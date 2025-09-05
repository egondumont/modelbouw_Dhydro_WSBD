### Royal HaskoningDHV
### 2023-03-21: Albert Goedbloed

### pumping script

### TODO:
### check missing data. fill provided data and make /discuss assumptions


### Import
from pathlib import Path

import geopandas as gpd


class ProcessPumps:
    def __init__(self, output_dir, checkbuffer):
        self.output_dir = Path(output_dir)
        self.source_data_dir = self.output_dir / "brondata"
        self.checkbuffer = checkbuffer
        self.capacity_dict = {"KGM00033": 1.8, "KGM00043": 3.3, "KGM00389": 30.54}

    def run(self):
        raw_data = gpd.read_file(self.source_data_dir / "pomp.gpkg")
        raw_data_station = gpd.read_file(self.source_data_dir / "gemaal.gpkg")
        network = gpd.read_file(self.output_dir / "hydroobject.gpkg")

        network_buffer1 = network.buffer(self.checkbuffer[0], cap_style=2).unary_union
        network_buffer2 = network.buffer(self.checkbuffer[1], cap_style=2).unary_union
        network_intersection1 = raw_data.intersects(network_buffer1)
        network_intersection2 = raw_data.intersects(network_buffer2)

        drop = []
        for index, row in raw_data.iterrows():
            if not network_intersection2.iloc[index]:
                raw_data_station.loc[index, "commentlocatie"] = (
                    f"gemaal ligt niet op netwerk (verder dan {self.checkbuffer[1]} m)"
                )
                drop.append(index)

            elif not network_intersection1.iloc[index]:
                raw_data_station.loc[index, "commentlocatie"] = (
                    f"gemaal ligt waarschijnlijk niet op netwerk (verder dan {self.checkbuffer[0]} m)"
                )

            if row["globalid"] in self.capacity_dict.keys():
                raw_data.loc[index, "maximalecapaciteit"] = self.capacity_dict[row["globalid"]]

        raw_data_station.drop(drop, inplace=True)
        raw_data.drop(drop, inplace=True)

        raw_data.to_file(self.output_dir / "pomp.gpkg", driver="GPKG")
        raw_data_station.to_file(self.output_dir / "gemaal.gpkg", driver="GPKG")
