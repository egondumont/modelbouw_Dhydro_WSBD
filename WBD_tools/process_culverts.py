### Royal HaskoningDHV
### 2023-03-21: Albert Goedbloed

### Duiker script

### 
### fill  missing data:
### BOKBO and BOKBE assume 3cm below leggerbodemhoogte (get from clostest profiledata, might require network analysis)
### missing diameter set at 500 mm (mostly small culverts are missing). Good to have might be a check on the size of nearest profile or closest upstream or downstream culvert to verify if 500mm is a good assumption
### remove culverts that are not in an A-watergang (KDU7 in ID or are not on the network) option to do some easy checks
### all done and identified. TODO: remove all culverst outside network  and with no data (as identified)


### Import
import os
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import datetime
### /import

class PROCESS_CULVERTS:

    
    def __init__(self,root_dir,dijkringen,checkbuffer):
        self.root_dir=root_dir
        self.dijkringen=dijkringen
        self.checkbuffer=checkbuffer

    def run(self):

        for dijkring in self.dijkringen:
            #path to shape channels
            path_shape=os.path.join(self.root_dir,'brondata/',dijkring)

            #export path
            path_export = os.path.join(self.root_dir, "Culverts")
            if not os.path.exists(path_export):
                os.makedirs(path_export)

            profile_data = gpd.read_file(os.path.join(self.root_dir,"Profiles/profiles_" + dijkring + ".gpkg"))
            network_data = gpd.read_file(os.path.join(self.root_dir, "Network",'network_' + dijkring + '.gpkg'))
            raw_data = gpd.read_file(os.path.join(path_shape,"duikersifonhevel.gpkg"))
            raw_data['globalid']=raw_data['code']
            print('start intersction culverts')
            
            network_buffer1 = network_data.buffer(self.checkbuffer[0],cap_style =2).unary_union
            network_buffer2 = network_data.buffer(self.checkbuffer[1],cap_style =2).unary_union
            network_intersection1 = raw_data.within(network_buffer1)
            network_intersection2 = raw_data.within(network_buffer2)    
            print('start updating culverts')

            culvert_length=raw_data.length

            for index,row in raw_data.iterrows():
                drop=False
                if not network_intersection2.iloc[index]:
                    drop=True
                    raw_data.loc[index,'commentlocatie']= f'Duiker ligt niet op netwerk (verder dan {self.checkbuffer[1]} m)'
                elif not network_intersection1.iloc[index]:
                    raw_data.loc[index,'commentlocatie']= f'Duiker ligt waarschijnlijk niet op netwerk (verder dan {self.checkbuffer[0]} m)'  
                if row['lengte']<=0:
                    raw_data.loc[index,'lengte']=culvert_length[index]
                    raw_data.loc[index,'commentlengte']= 'lengte tabel aangevuld met lengte object'
                elif abs(1-row['lengte']/culvert_length[index])>0.2:
                    raw_data.loc[index,'commentlengte']= 'lengte in de tabel komt niet overeen met lengte van object'

                if row['hoogteopening']<=0 or row['hoogteopening']>10:
                    if row['breedteopening']<=0 or row['breedteopening']>10:
                        raw_data.loc[index,'hoogteopening']=0.5
                        
                    else:
                        raw_data.loc[index,'hoogteopening']=raw_data.loc[index,'breedteopening']    
                    raw_data.loc[index,'commenthoogteopening']= 'hoogteopening aangevuld'
                if row['breedteopening']<=0 or row['breedteopening']>10:
                    if row['hoogteopening']<=0 or row['hoogteopening']>10:
                        raw_data.loc[index,'breedteopening']=0.5
                    else:
                        raw_data.loc[index,'breedteopening']=raw_data.loc[index,'hoogteopening']
                            
                    raw_data.loc[index,'commentbreedteopening']= 'breedteopening aangevuld'   
                    

                if row['hoogtebinnenonderkantbene']<-10 or row['hoogtebinnenonderkantbene']>40:
                    if row['hoogtebinnenonderkantbov']<-10 or row['hoogtebinnenonderkantbov']>40:
                        obj_buffer=row['geometry'].buffer(self.checkbuffer[0])
                        obj_intersect=obj_buffer.intersects(network_data.geometry)
                        
                        if len(network_data['code'][obj_intersect])==0:
                            obj_buffer=row['geometry'].buffer(self.checkbuffer[1])
                            obj_intersect=obj_buffer.intersects(network_data.geometry)
                            if len(network_data['code'][obj_intersect])==0:
                                drop=True

                            else:
                                
                                points_up=profile_data[profile_data['code'].str.fullmatch(network_data['code'][obj_intersect].values[0])]
                                points_down=profile_data[profile_data['code'].str.contains(network_data['code'][obj_intersect].values[0]+'_down')]
                                if len(points_up)==0:
                                    
                                    drop=True
                                else:    
                                    distance_up=min(row['geometry'].distance(points_up.geometry))
                                    distance_down=min(row['geometry'].distance(points_down.geometry))
                                    new_z=min(points_down['Z'])+distance_down/(distance_up+distance_down)*(min(points_up['Z'])-min(points_down['Z']))
                                    raw_data.loc[index,'hoogtebinnenonderkantbene']=new_z
                                    raw_data.loc[index,'hoogtebinnenonderkantbov']=new_z+0.02
                                    raw_data.loc[index,'commentbodem']= f'bodem aangevuld (met obejct binnen {self.checkbuffer[1]} m)'  
                        else:
                            points_up=profile_data[profile_data['code'].str.fullmatch(network_data['code'][obj_intersect].values[0])]
                            points_down=profile_data[profile_data['code'].str.contains(network_data['code'][obj_intersect].values[0]+'_down')]
                            if len(points_up)==0:
                                drop=True
                                
                            else:    
                                distance_up=min(row['geometry'].distance(points_up.geometry))
                                distance_down=min(row['geometry'].distance(points_down.geometry))
                                new_z=min(points_down['Z'])+distance_down/(distance_up+distance_down)*(min(points_up['Z'])-min(points_down['Z']))
                                raw_data.loc[index,'hoogtebinnenonderkantbene']=new_z
                                raw_data.loc[index,'hoogtebinnenonderkantbov']=new_z+0.02
                                raw_data.loc[index,'commentbodem']= f'bodem aangevuld (met obejct binnen {self.checkbuffer[0]} m)'
                               
                        
                    else:
                        raw_data.loc[index,'hoogtebinnenonderkantbene']=  row['hoogtebinnenonderkantbov']-0.02
                        raw_data.loc[index,'commentbodem']= 'bodem hoogte beneden aangevuld'
                elif row['hoogtebinnenonderkantbov']<-10 or row['hoogtebinnenonderkantbov']>40: 
                    raw_data.loc[index,'hoogtebinnenonderkantbov']=  row['hoogtebinnenonderkantbene']+0.02
                    raw_data.loc[index,'commentbodem']= 'bodem hoogte boven aangevuld' 

                # if row['vormkoker']:
                #     raw_data.loc[index,'vormkoker']="rond"

                if row['ruwheid']<=0 or row['ruwheid']>100:
                    raw_data.loc[index,'ruwheid']=75

                if drop:
                    raw_data.drop(index,inplace=True)    
            # for index,row in raw_data.iterrows():
            #     print(index)
            #     print(row['code'])
            print('finished updating culverts')
            raw_data.to_file(os.path.join(path_export,'culverts_' + dijkring + '.gpkg'), driver='GPKG') 
