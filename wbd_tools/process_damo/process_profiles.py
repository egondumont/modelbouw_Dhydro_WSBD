from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely import Point


class ProcessProfiles:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.source_data_dir = self.output_dir / "brondata"

    def run(self):
        raw_data = gpd.read_file(self.source_data_dir / "profielpunt.gpkg")
        raw_data["code"] = raw_data["profiellijnid"]
        network_data = gpd.read_file(self.source_data_dir / "hydroobject.gpkg")

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
