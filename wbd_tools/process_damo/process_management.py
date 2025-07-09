from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import Point


class ProcessManagement:
    def __init__(self, output_dir, checkbuffer):
        self.output_dir = Path(output_dir)
        self.source_data_dir = self.output_dir / "brondata"
        self.checkbuffer = checkbuffer

    def run(self):
        # Weir corrections specificially developed for Waterschap Brabantse Delta
        management = gpd.read_file(self.source_data_dir / "sturing.gpkg")
        pumpstation = gpd.read_file(self.output_dir / "gemaal.gpkg")
        network = gpd.read_file(self.output_dir / "hydroobject.gpkg")
        observations = gpd.GeoDataFrame(
            {"id": [], "locationtype": []},
            geometry=[],
            crs="EPSG:28992",
        )
        # Assumed distance (meters) between pump station en the observation station used for steering the pump
        distance_pump_observation = 3.0
        network_buffer = network.buffer(self.checkbuffer[0], cap_style=2)
        pumpindex_hydrobjectindex = {}

        for index_pumpstation, row_pumpstation in pumpstation.iterrows():
            for index_network, row_network in network.iterrows():
                if network_buffer[index_network].intersects(row_pumpstation.geometry):
                    pumpindex_hydrobjectindex[index_pumpstation] = [index_network]

        for index_pumpstation, row_pumpstation in pumpstation.iterrows():
            for index_management, row_management in management.iterrows():
                # voor iedere gemaalid in object Sturing...
                if row_pumpstation["code"] == row_management["pompid"]:
                    # selecteren hydroobject waarop het gemaal ligt
                    closest_branch = network.iloc[pumpindex_hydrobjectindex[index_pumpstation]]
                    # find location of pumpstation on closest branch
                    distance = closest_branch.geometry.project(row_pumpstation.geometry)
                    # find location of specified distance upstream of pumpstation along hydroobject (this is where the observation will be placed)
                    distance = (distance - distance_pump_observation).iloc[0]
                    # if the beginning of the branch is within 3 meters:
                    # assign an observation location on the preceding branch, or
                    # if there is no preceding branch, place the obserbation onthe beginning of the current branch
                    if distance < 0.0:
                        # find preceding branch
                        closest_branch_ = self.point_near_linestring_end(
                            row_pumpstation.geometry, network.geometry, distance_pump_observation
                        )
                        # if preceding branch is found:
                        if closest_branch_:
                            closest_branch = closest_branch_
                        # If not, then put observation on start of current hydroobject
                        else:
                            distance = 0.0

                    # convert distance from beginning of branch to Shapely Point
                    observation_location = closest_branch.interpolate(distance)
                    if not isinstance(observation_location, Point):
                        observation_location = observation_location.iloc[0]
                    row_observations = gpd.GeoDataFrame(
                        {"id": [row_pumpstation.code], "locationtype": ["1d"]},
                        geometry=[observation_location],
                        crs="EPSG:28992",
                    )
                    observations = pd.concat([observations, row_observations], ignore_index=True)
                    management.loc[index_management, "geometry"] = observation_location

        # add observation ID to management object
        management["meetlocatieid"] = management["pompid"]

        observations.to_file(self.output_dir / "meetpunten.gpkg", driver="GPKG")
        management.to_file(self.output_dir / "sturing.gpkg", driver="GPKG")

    def point_near_linestring_end(self, point, linestrings, distance_tolerance):
        """
        Checks if a Shapely Point is within a specified distance of the endpoints of a list of linestrings.

        Args:
            point: A shapely.geometry.Point object.
            linestrings: A shapely.geoseries.LineString object.
        `   distance_tolerance: The maximum distance to consider the point near the endpoint.

        Returns:
            If the point is within the distance tolerance of either endpoint the linestring with this end point is returned, None otherwise.
        """
        index_distance = {}
        for index, linestring in linestrings.items():
            end_point = Point(linestring.coords[-1])
            if point.distance(end_point) <= distance_tolerance:
                index_distance[index] = point.distance(end_point)
        if not index_distance:
            return None
        else:
            return linestrings[min(index_distance, key=index_distance.get)]
