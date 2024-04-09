### Royal HaskoningDHV
### 2023-03-21: Albert Goedbloed

### closing mechanisms script

### zoekt gerelateerd object binnen 0.5 m anders binnen 5m. bij meerdere objecten wordt de dichtsbijzijnde genomen
### is er geen object binnen 5 m dan wordt item verwijderd.
### TODO: dichtsbijzijnde en verwijderen zonder gerelateerd object
### Import
import os
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import datetime
### /import

class PROCESS_CLOSING:

    
    def __init__(self,root_dir,dijkringen,checkbuffer):
        self.root_dir=root_dir
        self.dijkringen=dijkringen
        self.checkbuffer=checkbuffer

    def run(self):

        for dijkring in self.dijkringen:
            #path to shape channels
            path_shape=os.path.join(self.root_dir,'brondata/',dijkring)

            #export path
            path_export = os.path.join(self.root_dir, "Closing")
            if not os.path.exists(path_export):
                os.makedirs(path_export)

            # get the shapefile
            shape = os.path.join(path_shape,"afsluitmiddel.gpkg")

            raw_data = gpd.read_file(shape)
            raw_data['globalid']=raw_data['code']
            culvert_data = gpd.read_file(os.path.join(self.root_dir,"Culverts/culverts_" + dijkring + ".gpkg"))
            pump_data = gpd.read_file(os.path.join(self.root_dir,"Pumping/Pump_" + dijkring + ".gpkg"))
            for index,row in raw_data.iterrows():
                drop=False
                obj_buffer=row['geometry'].buffer(self.checkbuffer[0])
                obj_intersect=obj_buffer.intersects(culvert_data.geometry)
                obj_intersect_pump=obj_buffer.intersects(pump_data.geometry)
                if len(culvert_data['code'][obj_intersect])+len(pump_data['code'][obj_intersect_pump])==0:
                    obj_buffer=row['geometry'].buffer(self.checkbuffer[1])
                    obj_intersect=obj_buffer.intersects(culvert_data.geometry)
                    obj_intersect_pump=obj_buffer.intersects(pump_data.geometry)
                    if len(culvert_data['code'][obj_intersect])+len(pump_data['code'][obj_intersect_pump])==0:                    
                        drop=True
                    else:
                        if len(culvert_data['code'][obj_intersect])>0:
                            raw_data.loc[index,'duikersifonhevelid']= culvert_data['code'][obj_intersect].values[0]
                        else:    
                            raw_data.loc[index,'duikersifonhevelid']= pump_data['code'][obj_intersect_pump].values[0]
                        raw_data.loc[index,'comment']= f'object aangevuld (binnen {self.checkbuffer[1]} m)'
                else:
                    if len(culvert_data['code'][obj_intersect])>0:
                        raw_data.loc[index,'duikersifonhevelid']= culvert_data['code'][obj_intersect].values[0]
                    else:    
                        raw_data.loc[index,'duikersifonhevelid']= pump_data['code'][obj_intersect_pump].values[0]
                    raw_data.loc[index,'comment']= f'object aangevuld (binnen {self.checkbuffer[0]} m)'  
                if drop:
                    raw_data.drop(index,inplace=True) 
            raw_data.to_file(os.path.join(path_export,'closing_' + dijkring + '.gpkg'), driver='GPKG')    