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
### /import
#all good
class PROCESS_PUMPING:

    def __init__(self,root_dir,dijkringen,checkbuffer):
        self.root_dir=root_dir
        self.dijkringen=dijkringen
        self.checkbuffer=checkbuffer
        self.capacity_dict={'KGM00033':1.8,'KGM00043':3.3,'KGM00389':30.54}

    def run(self):

        for dijkring in self.dijkringen:
            #path to shape channels
            path_shape=os.path.join(self.root_dir,'brondata/',dijkring)

            #export path
            path_export = os.path.join(self.root_dir, "Pumping")
            if not os.path.exists(path_export):
                os.makedirs(path_export)

            raw_data = gpd.read_file(os.path.join(path_shape,"pomp.gpkg"))
            raw_data['globalid']=raw_data['code']

            raw_data_station = gpd.read_file(os.path.join(path_shape,"gemaal.gpkg"))
            raw_data_station['globalid']=raw_data_station['code']

            network=gpd.read_file(os.path.join(self.root_dir, "Network",'network_' + dijkring + '.gpkg'))
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
                      
            raw_data.to_file(os.path.join(path_export,'Pump_' + dijkring + '.gpkg'), driver='GPKG') 
            raw_data_station.to_file(os.path.join(path_export,'Gemaal_' + dijkring + '.gpkg'), driver='GPKG')