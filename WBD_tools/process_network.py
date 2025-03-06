#this scripts determines the dangling nodes of a shape (lines)
#real end and begin nodes can be turned of in GIS (count number is 1)
#helpfull in determining the locations were snapping might be needed
#Rineke Hulsman, RHDHV, 13 january 2021
#Egon Dumont, WSBD, 29 January 2025

import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import datetime
#import shapefile
from shapely import distance
from shapely.ops import snap, split
from shapely.geometry import LineString
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

            path_export = os.path.join(self.root_dir, "Network",dijkring)
            # get the shapefile
            

            waterloop = gpd.read_file(os.path.join(path_export,'networkraw_' + dijkring + '.gpkg'))

            waterloop['globalid']=waterloop['code']

            splitpoints=[] # list of locations where hydroobjects should be split due to intersection with a second hydroobject

            for index,row in waterloop.iterrows():
    
                start_point=gpd.points_from_xy([row.geometry.coords.xy[0][0]],[row.geometry.coords.xy[1][0]])
                end_point=gpd.points_from_xy([row.geometry.coords.xy[0][-1]],[row.geometry.coords.xy[1][-1]])
                I_1=waterloop.sindex.query(start_point, predicate="intersects") # gdb-index of geometries intersecting with start point of current hydroobject
                I_2=waterloop.sindex.query(end_point, predicate="intersects") # gdb-index of geometries intersecting with end point of current hydroobject
                I_self=[]
                I_conn_s=[]
                I_conn_e=[]
                str_start=''
                str_end=''

                for check_i in I_1[1]: # for each geometry intersecting with start point of current hydroobject....
                
                    if check_i in I_2[1]:

                        I_self.append(check_i)
                    else: # store start en end point geometry of hydroobject intersecting with start point of current hydroobject...
                        target_start=gpd.points_from_xy([waterloop.loc[check_i,'geometry'].coords.xy[0][0]],[waterloop.loc[check_i,'geometry'].coords.xy[1][0]])
                        target_end=gpd.points_from_xy([waterloop.loc[check_i,'geometry'].coords.xy[0][-1]],[waterloop.loc[check_i,'geometry'].coords.xy[1][-1]])
                        
                        if start_point==target_start or start_point==target_end: # If both hydroobjects only connect at their ends (i.e. no y-shape-connection)...
                            I_conn_s.append(check_i)
                
                for check_i in I_2[1]: # for each geometry intersecting with end point of current hydroobject....
                    if check_i not in I_1[1]:
                        target_start=gpd.points_from_xy([waterloop.loc[check_i,'geometry'].coords.xy[0][0]],[waterloop.loc[check_i,'geometry'].coords.xy[1][0]])
                        target_end=gpd.points_from_xy([waterloop.loc[check_i,'geometry'].coords.xy[0][-1]],[waterloop.loc[check_i,'geometry'].coords.xy[1][-1]])
                        
                        if end_point==target_start or end_point==target_end: # If both hydroobjects only connect at their ends (i.e. no y-shape-connection)...
                            I_conn_e.append(check_i) 
                
                if len(I_conn_s)==0: # If there is no upstream hydroobject which touches the current hydroobject... 

                    start_buffer=start_point.buffer(self.checkbuffer[0])
                    i_temp=waterloop.sindex.query(start_buffer, predicate="intersects")
                    i_potential=[]
                    for check_i in i_temp[1]:
                        if check_i not in I_self:
                            i_potential.append(check_i)
                    if len(i_potential)==0: # if no other hydroobjects were found within specified distance (checkbuffer[0]) from the start point of the current hydrooject...
                        start_buffer=start_point.buffer(self.checkbuffer[1])
                        i_temp=waterloop.sindex.query(start_buffer, predicate="intersects")
                        i_potential=[]
                        for check_i in i_temp[1]:
                            if check_i not in I_self:
                                i_potential.append(check_i)
                        if len(i_potential)==0:
                            str_start='start point, '
                        else: # if other hydroobjects were found within the larger specified distance (checkbuffer[1]) from the start point of the current hydrooject...
                            target_start=gpd.points_from_xy([waterloop.loc[i,'geometry'].coords.xy[0][0] for i in i_potential],[waterloop.loc[i,'geometry'].coords.xy[1][0] for i in i_potential])
                            target_end=gpd.points_from_xy([waterloop.loc[i,'geometry'].coords.xy[0][-1] for i in i_potential],[waterloop.loc[i,'geometry'].coords.xy[1][-1] for i in i_potential])
                            all_targets=gpd.GeoDataFrame(geometry=np.append(target_start,target_end))
                            all_targets['distance']=start_point.distance(all_targets)
                            i_min=all_targets['distance'].idxmin() # finding the (index of the) coordinates of the hydroobject start/end point that is closest to the start point of the current hydroobject

                            if all_targets.loc[i_min,'distance']<=self.checkbuffer[1]:
                                waterloop.loc[index,'geometry']=snap(waterloop.loc[index,'geometry'],all_targets.loc[i_min,'geometry'],self.checkbuffer[1])
                                str_start=f'start punt verplaatst naar punt binnen {self.checkbuffer[1]}, '
                            else:
                                str_start='geen punt in de buurt start, split doel waterloop, '
                                splitpoints.append(start_point[0]) # store point geometries where hydroobject should be split
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
                            splitpoints.append(start_point[0]) # store point geometries where hydroobject should be split    

                if len(I_conn_e)==0: # if no hydroobject has a start/end point that intersects with the end point of the current hydroobject...
                    
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
                        if len(i_potential)==0: # If no other hydroobject close to end point of current hydrrobject
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
                                splitpoints.append(end_point[0]) # store point geometries where hydroobject should be split

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
                            splitpoints.append(end_point[0]) # store point geometries where hydroobject should be split
                
                
                waterloop.loc[index,'commentconnect']=str_start + str_end

            def split_line_by_point(line, point, tolerance: float=self.checkbuffer[0]):
                    return split(snap(line, point, tolerance), point)

            # spit hydroobjects where other hydroobjects join or diverge from current hydroobject
            for p in splitpoints:
                for index,row in waterloop.iterrows():
                    # first use 2 if statements to check if hydroobject needs to be split 
                    if distance(row.geometry,p) < self.checkbuffer[0]: # if the current hydroobject is close enough to the current split point
                        if not row.geometry.boundary.contains(p): # if the splitpoint is not the endpoint of the current hydroobject
                            # give each half of the split a separate row in the hydroobjects geodataframe
                            waterloop.loc[index,'geometry'] = split_line_by_point(row.geometry,p).geoms[0]
                            row2 = waterloop.loc[index].copy()
                            row2["code"] = row2["code"] + "d" # making code unique
                            row2["globalid"] = row2["globalid"] + "d" # making globalid unique
                            row2["nen3610id"] = row2["nen3610id"][:-2] # making nen360id unique
                            row2['geometry'] = split_line_by_point(row.geometry,p).geoms[1]
                            waterloop = pd.concat([waterloop,row2.to_frame().T],ignore_index=True) # append second half of split hydroobject to hydroobjects 
            
            waterloop.set_crs(epsg=28992, inplace=True, allow_override=True)
            if len(self.dijkringen) > 1:
                waterloop.to_file(os.path.join(path_export,'hydroobject_' + dijkring + '.gpkg'), driver='GPKG')
            else:
                waterloop.to_file(os.path.join(path_export,'hydroobject.gpkg'), driver='GPKG') 


# if __name__ == '__main__':
#     pass

