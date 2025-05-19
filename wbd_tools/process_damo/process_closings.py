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
import logging
from datetime import datetime
from pathlib import Path
### /import

class ProcessClosings:

    
    def __init__(self,output_dir,checkbuffer):
        self.output_dir = Path(output_dir)
        self.source_data_dir = self.output_dir / "brondata"
        self.checkbuffer=checkbuffer

    def run(self):

        # get the shapefile
        shape = self.source_data_dir / "afsluitmiddel.gpkg"

        raw_data = gpd.read_file(shape)
        raw_data['globalid']=raw_data['code']
        culvert_data = gpd.read_file(self.output_dir / "duikersifonhevel.gpkg")
        pump_data = gpd.read_file(self.output_dir / "pomp.gpkg")
        logging.info(f"{len(raw_data)} afsluitmiddelen.")
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
                        raw_data.loc[index,'comment']= f'duikersifonhevelID aangevuld (binnen {self.checkbuffer[1]} m)'
                    else:    
                        raw_data.loc[index,'gemaalid']= pump_data['code'][obj_intersect_pump].values[0]
                        raw_data.loc[index,'comment']= f'gemaalID aangevuld (binnen {self.checkbuffer[1]} m)'
            else:
                if len(culvert_data['code'][obj_intersect])>0:
                    raw_data.loc[index,'duikersifonhevelid']= culvert_data['code'][obj_intersect].values[0]
                    raw_data.loc[index,'comment']= f'duikersifonhevelID aangevuld (binnen {self.checkbuffer[0]} m)'
                else:    
                    raw_data.loc[index,'gemaalid']= pump_data['code'][obj_intersect_pump].values[0]
                    raw_data.loc[index,'comment']= f'gemaalID aangevuld (binnen {self.checkbuffer[0]} m)'
            if drop:
                raw_data.drop(index,inplace=True)
        logging.info(f"{len(raw_data)} afsluitmiddelen zijn gekoppeld aan een duiker of gemaal.")
        raw_data.to_file(self.output_dir / 'afsluitmiddel.gpkg', driver='GPKG')    