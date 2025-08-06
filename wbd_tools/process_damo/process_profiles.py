from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely import Point, force_2d


class ProcessProfiles:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.source_data_dir = self.output_dir / "brondata"
        self.profiles = gpd.read_file(self.source_data_dir / "profielpunt.gpkg")

    def run(self):
        raw_data = self.profiles
        raw_data["code"] = raw_data["profiellijnid"]
        network_data = gpd.read_file(self.source_data_dir / "hydroobject.gpkg")

        # Correct Z-values and fill missing Z-values
        for index, row in raw_data.iterrows():
            no_z = np.isnan(row["Z"])
            if row["Z"] < -6 or no_z:
                if row["Z"] < -900 or no_z:
                    network_id = row["profiellijnid"][0:8]

                    buffer_drain = (
                        network_data[network_data["code"] == network_id]["geometry"]
                        .buffer(30, cap_style="square")
                        .unary_union
                    )
                    nearby_points = raw_data.intersects(
                        buffer_drain
                    )  # profielpunten binnen 30 meter van het het huidige profielpunt dat een hoogte < 900m heeft

                    try:
                        update_value = min(raw_data.loc[nearby_points, "Z"][raw_data["Z"] > -15])

                        if (
                            raw_data.loc[index, "codevolgnummer"] > 1 and raw_data.loc[index, "codevolgnummer"] < 4
                        ):  # als het de waterbodem betreft...
                            raw_data.loc[index, "geometry"] = Point(
                                raw_data.loc[index, "geometry"].x, raw_data.loc[index, "geometry"].y, update_value
                            )
                            raw_data.loc[index, "Z"] = update_value
                        else:  # als het het talud/insteek betreft...
                            raw_data.loc[index, "geometry"] = Point(
                                raw_data.loc[index, "geometry"].x, raw_data.loc[index, "geometry"].y, update_value + 5
                            )
                            raw_data.loc[index, "Z"] = update_value + 5
                        raw_data.loc[index, "commentz"] = "Bodemhoogte aangevuld met data in de buurt"
                    except:
                        raw_data.loc[index, "commentz"] = "geen waarde gevonden"

                elif row["Z"] < -100:
                    raw_data.loc[index, "geometry"] = Point(
                        raw_data.loc[index, "geometry"].x,
                        raw_data.loc[index, "geometry"].y,
                        raw_data.loc[index, "Z"] * 0.01,
                    )
                    raw_data.loc[index, "Z"] = raw_data.loc[index, "Z"] * 0.01

                    raw_data.loc[index, "commentz"] = (
                        "Decimaal punt ontbreekt in data dit gecorrigeerd (factor 100 lager)"
                    )
                else:
                    raw_data.loc[index, "geometry"] = Point(
                        raw_data.loc[index, "geometry"].x,
                        raw_data.loc[index, "geometry"].y,
                        raw_data.loc[index, "Z"] * 0.1,
                    )
                    raw_data.loc[index, "Z"] = raw_data.loc[index, "Z"] * 0.1

                    raw_data.loc[index, "commentz"] = (
                        "Decimaal punt ontbreekt in data dit gecorrigeerd (factor 10 lager)"
                    )

        # remove hydroobjects for which process_profiles.run() could not assign a leggerprofile from a nearby hydroobject (happens if nearby hydroobject is not split at junction with current hydroobject)
        raw_data.dropna(
            subset=[
                "Z",
            ],
            inplace=True,
        )

        for code in network_data["code"].values:
            # remove hydroobjects without leggerprofiles
            if sum(raw_data["profiellijnid"] == code) < 4:
                idx = network_data[network_data["code"] == code].index
                network_data.drop(idx, inplace=True)
            # indicatie in hydroobjects output which hydroobjects have corrected leggerprofiles
            elif raw_data.loc[raw_data["profiellijnid"] == code, "commentz"].any():
                network_data.loc[network_data["code"] == code, "commentprofiel"] = (
                    "leggerprofiel aangevuld of gecorrigeerd"
                )

        raw_data.set_crs(epsg=28992, inplace=True, allow_override=True)
        raw_data.to_file(self.output_dir / "profielpunt.gpkg", driver="GPKG")

        network_data.to_file(self.output_dir / "networkraw.gpkg", driver="GPKG")

    def add_profiles_near_split(self, line, hydroobject_code, split_point):
        """
        .....

        Args:
            line (Shapely Linestring): Hydroobject geometry to be split
            split_point (Shapely Point): location where hydroobject will be split

        Returns:
            ...: ...

        """
        import copy

        # find profiles near upstream and downstream end of line (they have the same 8 characters in their 'profiellijnid')
        new_profiles = copy.deepcopy(
            self.profiles[hydroobject_code == self.profiles["profiellijnid"].apply(lambda x: x[0:8])]
        )
        distance = line.project(split_point, normalized=True)
        for i in range(4):
            # linear interpolation of elevations at either end of the original unsplitted hydroobject
            z = new_profiles.iloc[i].geometry.z * (1 - distance) + new_profiles.iloc[i + 4].geometry.z * distance
            # make one new profile on each side of the split
            for j in [0, 4]:
                # new profile 1 m upstream and 1 m downstream of split
                [x, y] = self.move_point_parallel_to_curve(
                    distance * line.length + (j - 2.0) / 2.0,
                    force_2d(new_profiles.iloc[i + j].geometry),
                    line,
                )
                new_profiles.iloc[i + j].geometry = Point(x, y, z)
                new_profiles.iloc[
                    i + j
                ].profiellijnid = f"{hydroobject_code}_{'boven' if j == 0 else 'beneden'}_aantakking"

        self.profiles = gpd.concat([self.profiles, new_profiles.to_frame().T], ignore_index=True)

    def move_point_parallel_to_curve(self, distance, point, linestring):
        # Step 1: Project the point onto the line to find position on the curve
        projected_dist = linestring.project(point)
        closest_point = linestring.interpolate(projected_dist)

        # Step 2: Compute the perpendicular offset vector from the curve to the point
        offset_vector = np.array([point.x - closest_point.x, point.y - closest_point.y])
        offset_distance = np.linalg.norm(offset_vector)

        # Normalize the offset direction
        offset_unit = offset_vector / offset_distance

        # Step 3: Move along the curve
        new_dist = max(0, min(distance, linestring.length))  # Clamp to curve bounds
        new_point_on_curve = linestring.interpolate(new_dist)

        # Step 4: Compute tangent to curve at new point
        # We'll approximate the tangent using a small delta
        delta = 0.01
        p_before = linestring.interpolate(max(0, new_dist - delta))
        p_after = linestring.interpolate(min(linestring.length, new_dist + delta))
        tangent_vector = np.array([p_after.x - p_before.x, p_after.y - p_before.y])
        tangent_vector /= np.linalg.norm(tangent_vector)

        # Compute normal vector (perpendicular to tangent)
        normal_vector = np.array([-tangent_vector[1], tangent_vector[0]])

        # Determine the sign of the offset (based on dot product with original offset vector)
        sign = np.sign(np.dot(normal_vector, offset_unit))

        # Step 5: Apply the perpendicular offset to the new point
        return np.array([new_point_on_curve.x, new_point_on_curve.y]) + sign * normal_vector * offset_distance
