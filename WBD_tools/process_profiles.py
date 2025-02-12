### Royal HaskoningDHV
### 2023-03-21: Albert Goedbloed

### Profile script

### Import
import os
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import datetime
from dwarsprofiel_xyz import make_profile
from shapely import Point
### /import

class PROCESS_PROFILES:

    
    def __init__(self,root_dir,input_dir,dijkringen):
        self.root_dir=root_dir
        self.dijkringen=dijkringen
        self.input_dir=input_dir

    def run(self):

        for dijkring in self.dijkringen:
            path_shape=os.path.join(self.root_dir,'brondata/',dijkring)
            
            raw_data = gpd.read_file(os.path.join(path_shape,"profielpunt.gpkg"))
            raw_data['code']=raw_data['profiellijnid']
            network_data = gpd.read_file(os.path.join(path_shape,"hydroobject.gpkg"))
            
            for index,row in raw_data.iterrows():
                
                if 'OVK07859' not in row['profiellijnid']:
                    if row['Z']<-6:
                        if row['Z']<-900:

                            network_id=row['profiellijnid'][0:8]
                            
                            buffer_drain=network_data[network_data['code']==network_id]['geometry'].buffer(30,cap_style ='square').unary_union
                            nearby_points=raw_data.intersects(buffer_drain)

                            try:
                                idx=raw_data
                                update_value=min(raw_data.loc[nearby_points,'Z'][raw_data['Z']>-15])
                                
                                if raw_data.loc[index,'codevolgnummer']>1 and raw_data.loc[index,'codevolgnummer']<4:
                                    raw_data.loc[index,'geometry']=Point(raw_data.loc[index,'geometry'].x,raw_data.loc[index,'geometry'].y,update_value)
                                    raw_data.loc[index,'Z']=update_value
                                else:
                                    raw_data.loc[index,'geometry']=Point(raw_data.loc[index,'geometry'].x,raw_data.loc[index,'geometry'].y,update_value+5)
                                    raw_data.loc[index,'Z']=update_value+5
                                raw_data.loc[index,'commentz']= 'Bodemhoogte aangevuld met data in de buurt'
                            except:
                                
                                raw_data.loc[index,'commentz']='geen waarde gevonden'

                        elif row['Z']<-100:
                            raw_data.loc[index,'geometry']=Point(raw_data.loc[index,'geometry'].x,raw_data.loc[index,'geometry'].y,raw_data.loc[index,'Z']*0.01)
                            raw_data.loc[index,'Z']=raw_data.loc[index,'Z']*0.01
                            
                            raw_data.loc[index,'commentz']= 'Decimaal punt ontbreekt in data dit gecorrigeerd (factor 100 lager)'  
                        else:
                            raw_data.loc[index,'geometry']=Point(raw_data.loc[index,'geometry'].x,raw_data.loc[index,'geometry'].y,raw_data.loc[index,'Z']*0.1)
                            raw_data.loc[index,'Z']=raw_data.loc[index,'Z']*0.1
                            
                            raw_data.loc[index,'commentz']= 'Decimaal punt ontbreekt in data dit gecorrigeerd (factor 10 lager)' 
                else:
                    if raw_data.loc[index,'codevolgnummer']>1 and raw_data.loc[index,'codevolgnummer']<4:
                        raw_data.loc[index,'geometry']=Point(raw_data.loc[index,'geometry'].x,raw_data.loc[index,'geometry'].y,0)
                        raw_data.loc[index,'Z']=0  
                    else:
                        raw_data.loc[index,'geometry']=Point(raw_data.loc[index,'geometry'].x,raw_data.loc[index,'geometry'].y,5)
                        raw_data.loc[index,'Z']=5 
                    raw_data.loc[index,'commentz']='geen waarde gevonden aangevuld met stadaardwaarde'     


            path_export = os.path.join(self.root_dir, "Profiles",dijkring)
            if not os.path.exists(path_export):
                os.makedirs(path_export)

            raw_data.to_file(os.path.join(path_export,'profielpunt.gpkg'), driver='GPKG')

            # remove hydroobjects without leggerprofiles
            for code in network_data['code'].values:
                
                if sum(raw_data['profiellijnid']==code)<4:

                    idx=network_data[network_data['code']==code].index
                    network_data.drop(idx,inplace=True)
            path_export = os.path.join(self.root_dir, "Network",dijkring)
            if not os.path.exists(path_export):
                os.makedirs(path_export)
            network_data.to_file(os.path.join(path_export,'networkraw_' + dijkring + '.gpkg'), driver='GPKG')        
                 
