import os
from datetime import datetime
from delft3dfmpy import  HyDAMO
import geopandas as gpd


root_dir=os.path.dirname(os.getcwd())
output_dir = os.path.join(root_dir,"output",'20230413')
dijkringen = ["dijkring34","dijkring35"]
for dijkring in dijkringen:
    
    fn_model_domain= os.path.join(root_dir,"projectgebied",dijkring + '.shp')
    fn_branches = os.path.join(output_dir,'Network','network_' + dijkring + '.gpkg')
    fn_crosssections =os.path.join(output_dir,'Profiles','profiles_' + dijkring + '.gpkg')
    fn_culverts = os.path.join(output_dir,'Culverts','culverts_' + dijkring + '.gpkg')
    fn_weirs = os.path.join(output_dir,'Weir','weir_' + dijkring + '.gpkg')
    fn_pumpstation = os.path.join(output_dir,'Pumping','Gemaal_' + dijkring + '.gpkg')
    fn_pump = os.path.join(output_dir,'Pumping','Pump_' + dijkring + '.gpkg')
    fn_closing_devices = os.path.join(output_dir,'Closing','closing_' + dijkring + '.gpkg')

    network_data = gpd.read_file(fn_branches)
    
    hydamo = HyDAMO(fn_model_domain)

    hydamo.branches.read_gpkg_layer(str(fn_branches),layer_name='network_' + dijkring,
                                    clip=hydamo.clipgeo, index_col='code')


    
    hydamo.profile.read_gpkg_layer(str(fn_crosssections),
                                   layer_name='profiles_' + dijkring,
                                   groupby_column='profiellijnid',
                                   order_column='codevolgnummer')

    hydamo.profile_roughness.read_gpkg_layer(str(fn_crosssections), layer_name='profiles_' + dijkring)
    
    hydamo.profile.snap_to_branch(hydamo.branches, snap_method='intersecting')
    hydamo.profile.dropna(axis=0, inplace=True, subset=['branch_offset'])

    hydamo.culverts.read_gpkg_layer(str(fn_culverts), layer_name='culverts_' + dijkring, index_col='globalid',
                                    clip=hydamo.clipgeo)
    hydamo.culverts.snap_to_branch(hydamo.branches, snap_method='ends', maxdist=10)
    hydamo.culverts.dropna(axis=0, inplace=True, subset=['branch_offset'])
  
    hydamo.weirs.read_gpkg_layer(str(fn_weirs), layer_name='weir_' + dijkring)
    hydamo.weirs.snap_to_branch(hydamo.branches, snap_method='overal', maxdist=10)
    hydamo.weirs.dropna(axis=0, inplace=True, subset=['branch_offset'])

    hydamo.opening.read_gpkg_layer(str(fn_weirs), layer_name='weir_' + dijkring)

    hydamo.pumpstations.read_gpkg_layer(str(fn_pumpstation), layer_name='Gemaal_' + dijkring, index_col='globalid',
                                    clip=hydamo.clipgeo)
    hydamo.pumpstations.snap_to_branch(hydamo.branches, snap_method='ends', maxdist=10)
    hydamo.pumpstations.dropna(axis=0, inplace=True, subset=['branch_offset'])

    hydamo.pumps.read_gpkg_layer(str(fn_pump), layer_name='Pump_' + dijkring, index_col='globalid')

    hydamo.closing_device.read_gpkg_layer(str(fn_closing_devices), layer_name='closing_'+ dijkring)
    # Add afsluitmiddelen to management_devices
    
    # hydamo.management_device.add_data(hydamo.closing_device[['globalid', 'duikersifonhevelid', 'soortregelmiddel', 'hoogteopening']])


    
    