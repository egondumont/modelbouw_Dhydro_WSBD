from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import Point


class ProcessManagement:
    def __init__(self, output_dir, checkbuffer):
        self.output_dir = Path(output_dir)
        self.source_data_dir = self.output_dir / "brondata"
        self.checkbuffer = checkbuffer

        # Assumed distance (meters) between gate en the observation station used for steering the gate
        self.distance_structure_observation = 3.0
        self.observations = gpd.GeoDataFrame(
            {"id": [], "locationtype": []},
            geometry=[],
            crs="EPSG:28992",
        )

    def run(self, mask):
        """
        Parameters
        ----------
        mask : shapely polygon
            Only the management items that intersect the mask will be included
        """

        # Weir corrections specificially developed for Waterschap Brabantse Delta
        self.management = gpd.read_file(self.source_data_dir / "sturing.gpkg")
        gate = gpd.read_file(self.output_dir / "regelmiddel.gpkg")
        pump = gpd.read_file(self.output_dir / "pomp.gpkg")
        network = gpd.read_file(self.output_dir / "hydroobject.gpkg")

        network_buffer = network.buffer(self.checkbuffer[0], cap_style=2)

        # linking weir gates to hydroobjects
        self.make_locations_of_measurements_and_management(
            gate,
            network,
            network_buffer,
            is_gate=True,  # Automatic gates require separate observation locations in D-hydro, in contrast to pumps in D-hydro
        )
        # linking pumps to hydroobjects
        self.make_locations_of_measurements_and_management(pump, network, network_buffer)

        # Remove management rules that apply weirs and pumps outside the mask
        # This step was not done in tohydamogml, because the 'management' table (DAMO) in the beheerregister has no geometry
        self.management = self.management[self.management.intersects(mask)]

        # add observation ID to management object
        self.management["meetlocatieid"] = self.management["regelmiddelid"]

        self.observations.to_file(self.output_dir / "meetpunten.gpkg", driver="GPKG")
        self.management.to_file(self.output_dir / "sturing.gpkg", driver="GPKG")

    def make_locations_of_measurements_and_management(self, structure, network, network_buffer, is_gate: bool = False):
        structureindex_hydrobjectindex = {}
        for index_structure, row_structure in structure.iterrows():
            for index_network, _ in network.iterrows():
                if network_buffer[index_network].intersects(row_structure.geometry):
                    structureindex_hydrobjectindex[index_structure] = [index_network]

        if is_gate:
            id_name = "regelmiddelid"
        else:
            id_name = "pompid"

        for index_structure, row_structure in structure.iterrows():
            for index_management, row_management in self.management.iterrows():
                # voor iedere regelmiddelid in object Sturing...
                if row_structure["code"] == row_management[id_name]:
                    # selecteren hydroobject waarop het stuw horend bij het regelmiddel ligt
                    closest_branch = network.iloc[structureindex_hydrobjectindex[index_structure]]
                    # find location of gate/pump on closest branch
                    distance = closest_branch.geometry.project(row_structure.geometry)
                    # find location of specified distance upstream of gate/pump along hydroobject (this is where the observation will be placed)
                    distance = (distance - self.distance_structure_observation).iloc[0]
                    # if the beginning of the branch is within 3 meters:
                    # assign an observation location on the preceding branch, or
                    # if there is no preceding branch, place the obserbation onthe beginning of the current branch
                    if distance < 0.0:
                        # find preceding branch
                        closest_branch_ = self.point_near_linestring_end(
                            row_structure.geometry, network.geometry, self.distance_structure_observation
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
                        {"id": [row_structure.code], "locationtype": ["1d"]},
                        geometry=[observation_location],
                        crs="EPSG:28992",
                    )
                    self.management.loc[index_management, "geometry"] = observation_location
                    if is_gate:
                        self.observations = pd.concat([self.observations, row_observations], ignore_index=True)

    def point_near_linestring_end(self, point, linestrings, distance_tolerance):
        """
        Check if a Shapely Point is within a specified distance of the endpoints of a list of linestrings.

        Args:
            point: A shapely.geometry.Point object.
            linestrings: A shapely.geoseries.LineString object.
        `   distance_tolerance: The maximum distance to consider the point near the endpoint.

        Return:
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
