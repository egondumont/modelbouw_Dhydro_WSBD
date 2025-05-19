### Royal HaskoningDHV
### 2023-03-21: Albert Goedbloed

### pumping script

### TODO:
### check missing data. fill provided data and make /discuss assumptions


### Import
import os
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
### /import
#all good
class ProcessPumps:

    def __init__(self,output_dir,checkbuffer):
        self.output_dir = Path(output_dir)
        self.source_data_dir = self.output_dir / "brondata"
        self.checkbuffer=checkbuffer
        self.capacity_dict={'KGM00033':1.8,'KGM00043':3.3,'KGM00389':30.54}

    def run(self):
        raw_data = gpd.read_file(self.source_data_dir / "pomp.gpkg")
        raw_data['globalid']=raw_data['code']

        raw_data_station = gpd.read_file(self.source_data_dir / "gemaal.gpkg")
        raw_data_station['globalid']=raw_data_station['code']

        network=gpd.read_file(self.output_dir / 'hydroobject.gpkg')
        network_buffer1 = network.buffer(self.checkbuffer[0],cap_style =2).unary_union
        network_buffer2 = network.buffer(self.checkbuffer[1],cap_style =2).unary_union
        network_intersection1 = raw_data.intersects(network_buffer1)
        network_intersection2 = raw_data.intersects(network_buffer2)


        for index,row in raw_data.iterrows():
            drop=False
            if not network_intersection2.iloc[index]:
                raw_data.loc[index,'commentlocatie']= f'gemaal ligt niet op netwerk (verder dan {self.checkbuffer[1]} m)'
                drop=True

            elif not network_intersection1.iloc[index]:
                raw_data.loc[index,'commentlocatie']= f'gemaal ligt waarschijnlijk niet op netwerk (verder dan {self.checkbuffer[0]} m)'  
            
            raw_data.loc[index,'gemaalid']='GEM_'+raw_data.loc[index,'gemaalid']
            if row['code'] in self.capacity_dict.keys():
                raw_data.loc[index,'maximalecapaciteit']=self.capacity_dict[row['code']]

            if drop:
                idx_gemaal=  raw_data_station[raw_data_station['code']==raw_data.loc[index,'gemaalid']].index
                raw_data_station.drop(idx_gemaal,inplace=True)
                raw_data.drop(index,inplace=True)
                    
        raw_data.to_file(self.output_dir / 'pomp.gpkg', driver='GPKG') 
        raw_data_station.to_file(self.output_dir / 'gemaal.gpkg', driver='GPKG')