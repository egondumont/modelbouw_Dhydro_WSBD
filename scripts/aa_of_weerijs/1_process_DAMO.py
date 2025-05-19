# %%
#  imports
import os
import logging
import shutil
import sys
from pathlib import Path
from datetime import datetime
from wbd_tools import GetData, init_gdb, get_modelgebied
from wbd_tools.process_damo import ProcessNetwork, ProcessProfiles, ProcessCulverts, ProcessWeirs, ProcessPumps, ProcessClosings
from wbd_tools.tohydamogml.hydamo_table import HydamoObject
from wbd_tools.fnames import get_fnames


#%%

# ophalen van file-namen en modelgebied uit foldernaam
fnames = get_fnames()
modelnaam = Path(__file__).parent.name

# initialiseren van geodatabase
json_dir = init_gdb(damo_gdb= fnames["damo_gdb"])


#%%
# relative path tot parent folder of script order to access model attribute_functions in folder 'json'

activities = {
    "laden": True,
    "network": True,
    "profiles": True,
    "culverts": True,
    "weirs": True,
    "pumping": True,
    "closing": True,
}

checkbuffer = [0.5, 5]

#%%

# define clip-polygon

modelgebied = get_modelgebied(modelgebied_gpkg=fnames["modelgebieden_gpkg"], modelnaam=modelnaam)

output_dir = fnames["modellen_output"].joinpath(f"{modelnaam}", datetime.today().strftime("%Y%m%d"))
output_dir.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    filename=os.path.join(output_dir, "logging.log"), level=logging.INFO
)
logging.info("Started")

if activities["laden"]:
    logging.info(f"loading data for {modelnaam}")
    get_data = GetData(json_dir=json_dir, output_dir=output_dir, poly_mask=modelgebied)
    get_data.run(json_subset=["hydroobject", "kunstwerkopening", "regelmiddel", "dwarsprofiel", "duikersifonhevel", "afsluitmiddel", "gemaal","pomp", "stuw"])
    logging.info("finished data loading")


if activities["profiles"]:
    logging.info("Start processing profiles")
    process_profiles = ProcessProfiles(output_dir)
    process_profiles.run()
    logging.info("finished processing profiles")

if activities["network"]:
    logging.info("Start processing network")
    process_network = ProcessNetwork(output_dir, checkbuffer)
    process_network.run()
    logging.info("finished processing network")

if activities["culverts"]:
    logging.info("Start processing culverts")
    # correct the culverts
    process_culverts = ProcessCulverts(output_dir, checkbuffer)
    process_culverts.run()
    logging.info("finished processing culverts")

if activities["weirs"]:
    process_weirs = ProcessWeirs(output_dir, checkbuffer)
    process_weirs.run()
    logging.info("finished processing weirs")

if activities["pumping"]:
    logging.info("Start processing pumping stations")
    process_pumps= ProcessPumps(output_dir, checkbuffer)
    process_pumps.run()
    logging.info("finished processing pumping stations")

if activities["closing"]:
    logging.info("Start processing closing mechanisms")
    process_closings = ProcessClosings(output_dir, checkbuffer)
    process_closings.run()
    logging.info("finished processing closing mechanisms")

logging.info("Finished")
logging.shutdown()

# %%