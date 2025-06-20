# %%
#  imports
import logging
import os
from datetime import datetime
from pathlib import Path

from wbd_tools import GetData, get_modelgebied, init_gdb
from wbd_tools.fnames import create_output_dir, get_fnames
from wbd_tools.process_damo import (
    ProcessClosings,
    ProcessCulverts,
    ProcessNetwork,
    ProcessProfiles,
    ProcessPumps,
    ProcessWeirs,
)

# %%


# ophalen van file-namen en modelgebied uit foldernaam
fnames = get_fnames()
modelnaam = Path(__file__).parent.name

# initialiseren van geodatabase
json_dir = init_gdb(damo_gdb=fnames["damo_gdb"])


# %%
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

# %%

# define clip-polygon

modelgebied = get_modelgebied(modelgebied_gpkg=fnames["modelgebieden_gpkg"], modelnaam=modelnaam)

output_dir = create_output_dir(model_name=modelnaam, date=datetime.today())
print(f"output_dir: {output_dir}")

logging.basicConfig(filename=os.path.join(output_dir, "logging.log"), level=logging.INFO)
logging.info("Started")

if activities["laden"]:
    logging.info(f"loading data for {modelnaam}")
    get_data = GetData(json_dir=json_dir, output_dir=output_dir, poly_mask=modelgebied)
    get_data.run(
        json_subset=[
            "hydroobject",
            "kunstwerkopening",
            "regelmiddel",
            "dwarsprofiel",
            "duikersifonhevel",
            "afsluitmiddel",
            "gemaal",
            "pomp",
            "stuw",
        ]
    )
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
    process_pumps = ProcessPumps(output_dir, checkbuffer)
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
