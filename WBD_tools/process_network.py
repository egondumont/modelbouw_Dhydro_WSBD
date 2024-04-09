#this scripts determines the dangling nodes of a shape (lines)
#real end and begin nodes can be turned of in GIS (count number is 1)
#helpfull in determining the locations were snapping might be needed
#Rineke Hulsman, RHDHV, 13 january 2021

import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import datetime
#import shapefile
from shapely.ops import snap
import os
# TODO: add check if there are profiles on the obejct
# dit is klaar alles wat gesnapt kan worden is gesnapt.
# mogelijk handmatige stap knip features op zodat niet verbonden stukjes er wel bij kunnen
class PROCESS_NETWORK:
    
    def __init__(self,root_dir,dijkringen,checkbuffer):
        self.root_dir=root_dir
        self.dijkringen=dijkringen
        self.checkbuffer=checkbuffer

    def run(self):
        for dijkring in self.dijkringen:
        #path to shape channels
            
            #export path

            path_export = os.path.join(self.root_dir, "Network")
            # get the shapefile
            

            waterloop = gpd.read_file(os.path.join(path_export,'networkraw_' + dijkring + '.gpkg'))

            waterloop['globalid']=waterloop['code']

            for index,row in waterloop.iterrows():
    
                start_point=gpd.points_from_xy([row.geometry.coords.xy[0][0]],[row.geometry.coords.xy[1][0]])
                end_point=gpd.points_from_xy([row.geometry.coords.xy[0][-1]],[row.geometry.coords.xy[1][-1]])
                I_1=waterloop.sindex.query(start_point, predicate="intersects")
                I_2=waterloop.sindex.query(end_point, predicate="intersects")
                I_self=[]
                I_conn_s=[]
                I_conn_e=[]
                str_paralel=''
                str_start=''
                str_end=''

                for check_i in I_1[1]:
                
                    if check_i in I_2[1]:

                        I_self.append(check_i)
                    else:
                        target_start=gpd.points_from_xy([waterloop.loc[check_i,'geometry'].coords.xy[0][0]],[waterloop.loc[check_i,'geometry'].coords.xy[1][0]])
                        target_end=gpd.points_from_xy([waterloop.loc[check_i,'geometry'].coords.xy[0][-1]],[waterloop.loc[check_i,'geometry'].coords.xy[1][-1]])
                        
                        if start_point==target_start or start_point==target_end:
                            I_conn_s.append(check_i)
                
                for check_i in I_2[1]:
                    if check_i not in I_1[1]:
                        target_start=gpd.points_from_xy([waterloop.loc[check_i,'geometry'].coords.xy[0][0]],[waterloop.loc[check_i,'geometry'].coords.xy[1][0]])
                        target_end=gpd.points_from_xy([waterloop.loc[check_i,'geometry'].coords.xy[0][-1]],[waterloop.loc[check_i,'geometry'].coords.xy[1][-1]])
                        
                        if end_point==target_start or end_point==target_end:
                            I_conn_e.append(check_i)
                
                if len(I_conn_s)==0:

                    start_buffer=start_point.buffer(self.checkbuffer[0])
                    i_temp=waterloop.sindex.query(start_buffer, predicate="intersects")
                    i_potential=[]
                    for check_i in i_temp[1]:
                        if check_i not in I_self:
                            i_potential.append(check_i)
                    if len(i_potential)==0:
                        start_buffer=start_point.buffer(self.checkbuffer[1])
                        i_temp=waterloop.sindex.query(start_buffer, predicate="intersects")
                        i_potential=[]
                        for check_i in i_temp[1]:
                            if check_i not in I_self:
                                i_potential.append(check_i)
                        if len(i_potential)==0:
                            str_start='start point, '
                        else:
                            target_start=gpd.points_from_xy([waterloop.loc[i,'geometry'].coords.xy[0][0] for i in i_potential],[waterloop.loc[i,'geometry'].coords.xy[1][0] for i in i_potential])
                            target_end=gpd.points_from_xy([waterloop.loc[i,'geometry'].coords.xy[0][-1] for i in i_potential],[waterloop.loc[i,'geometry'].coords.xy[1][-1] for i in i_potential])
                            all_targets=gpd.GeoDataFrame(geometry=np.append(target_start,target_end))
                            all_targets['distance']=start_point.distance(all_targets)
                            i_min=all_targets['distance'].idxmin()

                            if all_targets.loc[i_min,'distance']<=self.checkbuffer[1]:
                                waterloop.loc[index,'geometry']=snap(waterloop.loc[index,'geometry'],all_targets.loc[i_min,'geometry'],self.checkbuffer[1])
                                str_start=f'start punt verplaatst naar punt binnen {self.checkbuffer[1]}, '
                            else:
                                str_start='geen punt in de buurt start, split doel waterloop, '
                            # print(all_targets)
                            # print(start_point.distance(all_targets).sort)
                            


                    else:
                        target_start=gpd.points_from_xy([waterloop.loc[i,'geometry'].coords.xy[0][0] for i in i_potential],[waterloop.loc[i,'geometry'].coords.xy[1][0] for i in i_potential])
                        target_end=gpd.points_from_xy([waterloop.loc[i,'geometry'].coords.xy[0][-1] for i in i_potential],[waterloop.loc[i,'geometry'].coords.xy[1][-1] for i in i_potential])
                        all_targets=gpd.GeoDataFrame(geometry=np.append(target_start,target_end))
                        all_targets['distance']=start_point.distance(all_targets)
                        i_min=all_targets['distance'].idxmin()
            
                        if all_targets.loc[i_min,'distance']<=self.checkbuffer[1]:

                            waterloop.loc[index,'geometry']=snap(waterloop.loc[index,'geometry'],all_targets.loc[i_min,'geometry'],self.checkbuffer[1])
                            str_start=f'start punt verplaatst naar punt binnen {self.checkbuffer[0]}, '
                        else:
                            str_start='geen punt in de buurt start, split doel waterloop, '        

                if len(I_conn_e)==0:
                    
                    end_buffer=end_point.buffer(self.checkbuffer[0])
                    i_temp=waterloop.sindex.query(end_buffer, predicate="intersects")
                    i_potential=[]
                    for check_i in i_temp[1]:
                        if check_i not in I_self:
                            i_potential.append(check_i)
                    if len(i_potential)==0:
                        end_buffer=end_point.buffer(self.checkbuffer[1])
                        i_temp=waterloop.sindex.query(end_buffer, predicate="intersects")
                        i_potential=[]
                        for check_i in i_temp[1]:
                            if check_i not in I_self:
                                i_potential.append(check_i)
                        if len(i_potential)==0:
                            str_end='eind punt. '
                        else:
                            
                            target_start=gpd.points_from_xy([waterloop.loc[i,'geometry'].coords.xy[0][0] for i in i_potential],[waterloop.loc[i,'geometry'].coords.xy[1][0] for i in i_potential])
                            target_end=gpd.points_from_xy([waterloop.loc[i,'geometry'].coords.xy[0][-1] for i in i_potential],[waterloop.loc[i,'geometry'].coords.xy[1][-1] for i in i_potential])
                            all_targets=gpd.GeoDataFrame(geometry=np.append(target_start,target_end))
                            all_targets['distance']=end_point.distance(all_targets)
                            i_min=all_targets['distance'].idxmin()

                            if all_targets.loc[i_min,'distance']<=self.checkbuffer[1]:
                                waterloop.loc[index,'geometry']=snap(waterloop.loc[index,'geometry'],all_targets.loc[i_min,'geometry'],self.checkbuffer[1])
                            
                                str_end=f'eind punt verplaatst naar punt binnen {self.checkbuffer[1]}.'
                            else:
                                str_end='geen punt in de buurt einde, split doel waterloop.'
                        


                    else:
                        
                        target_start=gpd.points_from_xy([waterloop.loc[i,'geometry'].coords.xy[0][0] for i in i_potential],[waterloop.loc[i,'geometry'].coords.xy[1][0] for i in i_potential])
                        target_end=gpd.points_from_xy([waterloop.loc[i,'geometry'].coords.xy[0][-1] for i in i_potential],[waterloop.loc[i,'geometry'].coords.xy[1][-1] for i in i_potential])
                        all_targets=gpd.GeoDataFrame(geometry=np.append(target_start,target_end))
                        all_targets['distance']=end_point.distance(all_targets)
                        i_min=all_targets['distance'].idxmin()
                        if all_targets.loc[i_min,'distance']<=self.checkbuffer[1]:
                            waterloop.loc[index,'geometry']=snap(waterloop.loc[index,'geometry'],all_targets.loc[i_min,'geometry'],self.checkbuffer[1])
                            str_end=f'eind punt verplaatst naar punt binnen {self.checkbuffer[0]}.'
                        else:
                            str_end='geen punt in de buurt einde, split doel waterloop.' 
                
                
                waterloop.loc[index,'commentconnect']=str_paralel + str_start + str_end
            waterloop.set_crs(epsg=28992)
            waterloop.to_file(os.path.join(path_export,'network_' + dijkring + '.gpkg'), driver='GPKG') 


# if __name__ == '__main__':
#     pass

