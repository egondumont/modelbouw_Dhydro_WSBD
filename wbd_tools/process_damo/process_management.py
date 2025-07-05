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
                    # find location on closest branch that is 3 meters upstream of the pumpstation
                    distance = closest_branch.geometry.project(row_pumpstation.geometry) - 3.0
                    observation_location = Point(closest_branch.interpolate(distance).geometry.iloc[0])
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
