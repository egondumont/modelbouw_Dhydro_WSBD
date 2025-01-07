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


    def initialValidate(self, validatietool):
        # Make objects "kunstwerkopening" and "regelmiddel" that are related to the existing object "stuw"  
        # export resulting weir data to disk and to the validation task  
        for dijkring in self.dijkringen:
            #path to shape channels
            path_shape=os.path.join(self.root_dir,'brondata',dijkring)

            #export path for 
            path_export = os.path.join(self.root_dir,"weir","step1",dijkring)
            if not os.path.exists(path_export):
                os.makedirs(path_export)

            # get the data for shapefile
            raw_data = gpd.read_file(os.path.join(path_shape,"stuw.gpkg"))
            dropColumns = ['laagstedoorstroombreedte', 'laagstedoorstroomhoogte', 'hoogstedoorstroombreedte', 'hoogstedoorstroomhoogte']
            raw_data.drop(columns=dropColumns).to_file(os.path.join(path_export,'stuw.gpkg'), driver='GPKG') # Export to geopackage

            # Start of temporary code for the time period that 'kunstwerkopening' and 'regelmiddel' are not yet separate data objects in the 'beheerregister'
            #     Relate object kunstwerkopening to object stuw
            kunstwerkopening = raw_data.drop(columns=['afvoercoefficient'])
                # make relation between 'stuw' and 'kunstwerkopening':
                #   (Unfortunately D-hydamo can only cope with one "kunstwerkopening" for each "stuw")
            kunstwerkopening.rename(columns={"globalid" : "stuwid"}, inplace=True) # GlobalID of object 'stuw' becomes 'stuwid' of object 'kunstwerkopening'
            kunstwerkopening["globalid"] = globalid(len(kunstwerkopening)) # Creating a globally unique globalid for every kunstwerkopening
            kunstwerkopening.to_file(os.path.join(path_export,'kunstwerkopening.gpkg'), driver='GPKG') # Export to geopackage
            regelmiddel = kunstwerkopening
            kunstwerkopening = pd.DataFrame(kunstwerkopening.drop(columns='geometry')) # kunstwerkopening is volgens DAMO een tabel zonder geometrie
                # make relation between 'kunstwerkopening' and 'regelmiddel':
            regelmiddel.rename(columns={"globalid" : "kunstwerkopeningid"}, inplace=True)
            regelmiddel["overlaatonderlaat"]="Overlaat"
            dropColumns.append('stuwid')
            regelmiddel.drop(columns=dropColumns).to_file(os.path.join(path_export,'regelmiddel.gpkg'), driver='GPKG') # Export to geopackage       
            # End of temporary code for the time period that 'kunstwerkopening' and 'regelmiddel' are not yet separate data objects in the 'beheerregister'

            # Add weir-related data to existing validation task"
            validatietool.addData(path_export,'stuw.gpkg')
            validatietool.addData(path_export,'kunstwerkopening.gpkg')
            validatietool.addData(path_export,'regelmiddel.gpkg')
            validatietool.run() # run validation with just added objects
    
    def correct(self):
        # Corrections specificially developed for Waterschap Brabantse Delta, with the use of Validatietool output
        for dijkring in self.dijkringen:

            # open validation results, except syntax validation nor validation summaries
            val_weir = gpd.read_file(
                os.path.join(self.root_dir,'brondata/',"weir","step1",dijkring,'uitvoerValidatietool.gpkg'), 
                columns = validatietool.getColumnNames(self,4), # 4 is the index of the object 'stuw' in the json of the Validatietool
                layer='stuw'
                )

            #path to shape channels
            path_shape=os.path.join(self.root_dir,"weir","step1",dijkring)

            #export path
            path_export = os.path.join(self.root_dir,"weir","step2",dijkring)
            if not os.path.exists(path_export):
                os.makedirs(path_export)

            # Open non-corrected weirs, kunstwerkopeningen en regelmiddelen  
            weir = gpd.read_file(os.path.join(path_shape,'stuw.gpkg'))
            kunstwerkopening = gpd.read_file(os.path.join(path_shape,'kunstwerkopening.gpkg'))
            regelmiddel = gpd.read_file(os.path.join(path_shape,'regelmiddel.gpkg'))

            network=gpd.read_file(os.path.join(self.root_dir, "Network",dijkring,'hydroobject.gpkg'))

            network_buffer1 = network.buffer(self.checkbuffer[0],cap_style =2).unary_union
            network_buffer2 = network.buffer(self.checkbuffer[1],cap_style =2).unary_union
            network_intersection1 = weir.intersects(network_buffer1)
            network_intersection2 = weir.intersects(network_buffer2)
            print('start updating weirs')
            for index,row in weir.iterrows():
                drop=False
                if not network_intersection2.iloc[index]:
                    drop=True
                elif not network_intersection1.iloc[index]:
                    weir.loc[index,'commentlocatie']= f'Stuw ligt waarschijnlijk niet op netwerk (verder dan {self.checkbuffer[0]} m)'   
                
                if row['laagstedoorstroombreedte']<=0:
                    if row['hoogstedoorstroombreedte']>0:
                        
                        weir.loc[index,'laagstedoorstroombreedte']=row['hoogstedoorstroombreedte']
                        weir.loc[index,'commentbreedte']= 'laagstedoorstroombreedte aangevuld'
                        if row['kruinbreedte']<=0:
                            weir.loc[index,'kruinbreedte']=row['hoogstedoorstroombreedte']
                    elif row['kruinbreedte']>0:
                        weir.loc[index,'laagstedoorstroombreedte']=row['kruinbreedte']
                        weir.loc[index,'hoogstedoorstroombreedte']=row['kruinbreedte'] 
                        weir.loc[index,'commentbreedte']= 'hoogste- en laagstedoorstroombreedte aangevuld'   
                    else:
                        weir.loc[index,'laagstedoorstroombreedte']=1.5
                        weir.loc[index,'hoogstedoorstroombreedte']=1.5
                        weir.loc[index,'kruinbreedte']=1.5
                        weir.loc[index,'commentbreedte']= 'kruinbreedte volledig aangevuld'
                elif row['hoogstedoorstroombreedte']<=0:
                    
                    weir.loc[index,'hoogstedoorstroombreedte']=row['laagstedoorstroombreedte']
                    weir.loc[index,'commentbreedte']= 'hoogstedoorstroombreedte aangevuld'
                    if row['kruinbreedte']<=0:
                        weir.loc[index,'kruinbreedte']=row['laagstedoorstroombreedte']
                elif row['kruinbreedte']<=0:
                    weir.loc[index,'kruinbreedte']=row['hoogstedoorstroombreedte']
                    weir.loc[index,'commentbreedte']= 'kruinbreedte aangevuld'
  

                if row['laagstedoorstroomhoogte']<-10:
                    if row['hoogstedoorstroomhoogte']<-10:
                        drop=True
                    else:
                        weir.loc[index,'laagstedoorstroomhoogte']=row['hoogstedoorstroomhoogte']
                        weir.loc[index,'commenthoogte']= 'laagstedoorstroomhoogte aangevuld'
                elif  row['hoogstedoorstroomhoogte']<-10:
                    weir.loc[index,'hoogstedoorstroomhoogte']=row['laagstedoorstroomhoogte']
                    weir.loc[index,'commenthoogte']= 'hoogstedoorstroomhoogte aangevuld'

                if row['soortregelbaarheidcode']==str(99):
                    
                    weir.loc[index,'commentregelbaarheid']= 'geen soortregelbaarheidcode'
                
                if drop:
                    weir.drop(index,inplace=True)              

            print('finished updating weirs')
            weir.to_file(os.path.join(path_export,'stuw.gpkg'), driver='GPKG')
