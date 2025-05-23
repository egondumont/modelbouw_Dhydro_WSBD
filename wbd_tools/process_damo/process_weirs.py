### Royal HaskoningDHV
### 2023-03-21: Albert Goedbloed

### Weir script

### Import
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
from pathlib import Path

class ProcessWeirs:
    
    def __init__(self,output_dir,checkbuffer):
        self.output_dir = Path(output_dir)
        self.source_data_dir = self.output_dir / "brondata"
        self.checkbuffer=checkbuffer

    
    def run(self):
        # Weir corrections specificially developed for Waterschap Brabantse Delta
        #export path
        # get the shapefile
        weir = gpd.read_file(self.source_data_dir / "stuw.gpkg")
        kwo = gpd.read_file(self.source_data_dir / "kunstwerkopening.gpkg")
        regelm = gpd.read_file(self.source_data_dir / "regelmiddel.gpkg")

        network=gpd.read_file(self.source_data_dir / 'hydroobject.gpkg') 
        network_buffer1 = network.buffer(self.checkbuffer[0],cap_style =2).unary_union
        network_buffer2 = network.buffer(self.checkbuffer[1],cap_style =2).unary_union
        network_intersection1 = weir.intersects(network_buffer1)
        network_intersection2 = weir.intersects(network_buffer2)
        print('start updating weirs')
        for index,row in weir.iterrows():
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
                    weir.drop(weir.loc[weir['globalid']==kwo.loc[index,'stuwid']].index,inplace=True)
                    kwo.drop(index,inplace=True)
                else:
                    kwo.loc[index,'laagstedoorstroomhoogte']=row['hoogstedoorstroomhoogte']
                    kwo.loc[index,'commenthoogte']= 'laagstedoorstroomhoogte aangevuld'

        print('finished updating weirs')
        weir.to_file(self.output_dir / 'stuw.gpkg', driver='GPKG')
        kwo.to_file(self.output_dir /'kunstwerkopening.gpkg', driver='GPKG')
        regelm.to_file(self.output_dir /'regelmiddel.gpkg', driver='GPKG')
