### Royal HaskoningDHV
### 2023-03-21: Albert Goedbloed

### Weir script

### TODO:
### Only filling of missing data. evaluate what is missing and prepare assumtptions. get approval for assumptions and implement

### Import
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import datetime
import json
### /import
#verwijder alle objecten die niet op het netwerk liggen of te veel missing data hebben
class PROCESS_WEIR:
    #only copy data to new location
    
    def __init__(self,root_dir,dijkringen,checkbuffer):
        self.root_dir=root_dir
        self.dijkringen=dijkringen
        self.checkbuffer=checkbuffer

    def run(self):

        for dijkring in self.dijkringen:
            #path to shape channels
            path_shape=os.path.join(self.root_dir,'brondata/',dijkring)

            #export path
            path_export = os.path.join(self.root_dir,"Weir",dijkring)
            if not os.path.exists(path_export):
                os.makedirs(path_export)

            # get the shapefile
            

            raw_data = gpd.read_file(os.path.join(path_shape,"stuw.gpkg"))
            raw_data['globalid']=raw_data['code']

            network=gpd.read_file(os.path.join(self.root_dir, "Network",dijkring,'hydroobject.gpkg'))
            network_buffer1 = network.buffer(self.checkbuffer[0],cap_style =2).unary_union
            network_buffer2 = network.buffer(self.checkbuffer[1],cap_style =2).unary_union
            network_intersection1 = raw_data.intersects(network_buffer1)
            network_intersection2 = raw_data.intersects(network_buffer2)
            print('start updating weirs')
            for index,row in raw_data.iterrows():
                drop=False
                if not network_intersection2.iloc[index]:
                    drop=True
                elif not network_intersection1.iloc[index]:
                    raw_data.loc[index,'commentlocatie']= f'Stuw ligt waarschijnlijk niet op netwerk (verder dan {self.checkbuffer[0]} m)'   
                
                if row['laagstedoorstroombreedte']<=0:
                    if row['hoogstedoorstroombreedte']>0:
                        
                        raw_data.loc[index,'laagstedoorstroombreedte']=row['hoogstedoorstroombreedte']
                        raw_data.loc[index,'commentbreedte']= 'laagstedoorstroombreedte aangevuld'
                        if row['kruinbreedte']<=0:
                            raw_data.loc[index,'kruinbreedte']=row['hoogstedoorstroombreedte']
                    elif row['kruinbreedte']>0:
                        raw_data.loc[index,'laagstedoorstroombreedte']=row['kruinbreedte']
                        raw_data.loc[index,'hoogstedoorstroombreedte']=row['kruinbreedte'] 
                        raw_data.loc[index,'commentbreedte']= 'hoogste- en laagstedoorstroombreedte aangevuld'   
                    else:
                        raw_data.loc[index,'laagstedoorstroombreedte']=1.5
                        raw_data.loc[index,'hoogstedoorstroombreedte']=1.5
                        raw_data.loc[index,'kruinbreedte']=1.5
                        raw_data.loc[index,'commentbreedte']= 'kruinbreedte volledig aangevuld'
                elif row['hoogstedoorstroombreedte']<=0:
                    
                    raw_data.loc[index,'hoogstedoorstroombreedte']=row['laagstedoorstroombreedte']
                    raw_data.loc[index,'commentbreedte']= 'hoogstedoorstroombreedte aangevuld'
                    if row['kruinbreedte']<=0:
                        raw_data.loc[index,'kruinbreedte']=row['laagstedoorstroombreedte']
                elif row['kruinbreedte']<=0:
                    raw_data.loc[index,'kruinbreedte']=row['hoogstedoorstroombreedte']
                    raw_data.loc[index,'commentbreedte']= 'kruinbreedte aangevuld'
  

                if row['laagstedoorstroomhoogte']<-10:
                    if row['hoogstedoorstroomhoogte']<-10:
                        drop=True
                    else:
                        raw_data.loc[index,'laagstedoorstroomhoogte']=row['hoogstedoorstroomhoogte']
                        raw_data.loc[index,'commenthoogte']= 'laagstedoorstroomhoogte aangevuld'
                elif  row['hoogstedoorstroomhoogte']<-10:
                    raw_data.loc[index,'hoogstedoorstroomhoogte']=row['laagstedoorstroomhoogte']
                    raw_data.loc[index,'commenthoogte']= 'hoogstedoorstroomhoogte aangevuld'
   
                # if row['soortstuwcode']==str(99):
                    
                #     raw_data.loc[index,'commentsoortstuw']= 'geen soortstuwcode' 

                if row['soortregelbaarheidcode']==str(99):
                    
                    raw_data.loc[index,'commentregelbaarheid']= 'geen soortregelbaarheidcode'
                
                if drop:
                    raw_data.drop(index,inplace=True)              
            #     print(index)
            #     print(row['code'])
            print('finished updating weirs')
            raw_data.to_file(os.path.join(path_export,'stuw.gpkg'), driver='GPKG')  