### Royal HaskoningDHV
### 2023-03-21: Albert Goedbloed

### Weir script

### Import
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import datetime
import json
import random
import sys
sys.path.append("./json")
from attribute_functions import globalid

class PROCESS_WEIR:
    
    def __init__(self,root_dir,dijkringen,checkbuffer):
        self.root_dir=root_dir
        self.dijkringen=dijkringen
        self.checkbuffer=checkbuffer
    
    def run(self):
        # Weirorrections specificially developed for Waterschap Brabantse Delta
        for dijkring in self.dijkringen:
            #path to shape channels
            path_shape=os.path.join(self.root_dir,'brondata/',dijkring)

            #export path
            path_export = os.path.join(self.root_dir,"Weir",dijkring)
            if not os.path.exists(path_export):
                os.makedirs(path_export)

            # get the shapefile
            weir = gpd.read_file(os.path.join(path_shape,"stuw.gpkg"))
            kwo = gpd.read_file(os.path.join(path_shape,"kunstwerkopening.gpkg"))
            regelm = gpd.read_file(os.path.join(path_shape,"regelmiddel.gpkg"))

            network=gpd.read_file(os.path.join(self.root_dir, "Network",dijkring,'hydroobject.gpkg'))
            network_buffer1 = network.buffer(self.checkbuffer[0],cap_style =2).unary_union
            network_buffer2 = network.buffer(self.checkbuffer[1],cap_style =2).unary_union
            network_intersection1 = weir.intersects(network_buffer1)
            network_intersection2 = weir.intersects(network_buffer2)
            print('start updating weirs')
            for index,row in weir.iterrows():
                drop=False
                if not network_intersection2.iloc[index]: # if weir is too far from any hydroobject...
                    # remove weir and its related kunstwerkopening and regelmiddel objects
                    x = kwo.loc[kwo['stuwid']==weir.loc[index,'globalid']]
                    regelm.drop(regelm[regelm['kunstwerkopeningid']==x['globalid'].values[0]].index,inplace=True)
                    kwo.drop(x.index,inplace=True)
                    weir.drop(index,inplace=True)   
                elif not network_intersection1.iloc[index]:
                    weir.loc[index,'commentlocatie']= f'Stuw ligt waarschijnlijk niet op netwerk (verder dan {self.checkbuffer[0]} m)'   

            for index,row in kwo.iterrows():                
                if row['laagstedoorstroombreedte']<=0:
                    if row['kruinbreedte']>0:
                        kwo.loc[index,'laagstedoorstroombreedte']=row['kruinbreedte']
                        kwo.loc[index,'commentbreedte']= 'laagstedoorstroombreedte aangevuld'   
                    else:
                        kwo.loc[index,'laagstedoorstroombreedte']=1.5
                        kwo.loc[index,'kruinbreedte']=1.5
                        kwo.loc[index,'commentbreedte']= 'kruinbreedte en hoogste- en laagstedoorstroombreedte volledig aangevuld'

                if row['laagstedoorstroomhoogte']<-10:
                    if row['hoogstedoorstroomhoogte']<-10:
                        regelm.drop(regelm.loc[regelm['kunstwerkopeningid']==kwo.loc[index,'globalid']].index,inplace=True)
                        kwo.drop(index,inplace=True)
                    else:
                        kwo.loc[index,'laagstedoorstroomhoogte']=row['hoogstedoorstroomhoogte']
                        kwo.loc[index,'commenthoogte']= 'laagstedoorstroomhoogte aangevuld'

            print('finished updating weirs')
            weir.to_file(os.path.join(path_export,'stuw.gpkg'), driver='GPKG')
            kwo.to_file(os.path.join(path_export,'kunstwerkopening.gpkg'), driver='GPKG')
            regelm.to_file(os.path.join(path_export,'regelmiddel.gpkg'), driver='GPKG')
