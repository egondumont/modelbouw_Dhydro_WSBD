"""
Make sure the working directory is the folder where this file is located
"""

import sys
from pathlib import Path
import os
import logging
from wbd_tools.tohydamogml.hydamo_table import HydamoObject
import json
import geopandas as gpd
import shutil

JSON_DIR = Path(__file__).parent / "json"
JSON_OBJECTS = [
    {"json_file": "hydroobject.json"},
    {"json_file": "stuw.json"},
    {"json_file": "kunstwerkopening.json"},
    {"json_file": "regelmiddel.json"},
    {"json_file": "dwarsprofiel.json", "layer": "LEGGER_VASTGESTELD_WATERLOOP_CATEGORIE_A"},
    {"json_file": "duikersifonhevel.json"},
    {"json_file": "afsluitmiddel.json"},
    {"json_file": "brug.json"},
    {"json_file": "gemaal.json"},
    {"json_file": "pomp.json"},
    {"json_file": "sturing.json"},
    {"json_file": "bodemval.json"},
    {"json_file": "randvoorwaarden.json"},
]


def init_gdb(damo_gdb:Path, json_objects: dict = JSON_OBJECTS) -> Path:
    """Checks if DAMO GeoDataBase exists and populates JSON dir

    Returns:
       Path: Path to json dir
    """
    # init layers, will return FileNotFound when damo_gdb does not exist
    layers = gpd.list_layers(damo_gdb)
    layers["lower_casing"] = layers.name.str.lower()

    # init json-dir. Make if not existing
    json_dst_dir = damo_gdb.parent.joinpath("json")
    if not json_dst_dir.exists():
        json_dst_dir.mkdir()
    
    # update and write filename and layer of jsons
    for json_object in json_objects:

        # define file paths
        json_src_file = JSON_DIR.joinpath(json_object["json_file"])
        json_dst_file = json_dst_dir.joinpath(json_object["json_file"])

        # read json
        if not json_dst_file.exists():
            layer_specs = json.loads(json_src_file.read_text())
        else:
            layer_specs = json.loads(json_dst_file.read_text())

        # update path if layer is in layers
        if layer_specs["source"]["layer"].lower() in layers["lower_casing"].to_numpy():
            layer_specs["source"]["layer"] = layers.set_index("lower_casing").at[layer_specs["source"]["layer"].lower(), "name"]
            layer_specs["source"]["path"] = damo_gdb.as_posix()

        # write json
        json_dst_file.write_text(json.dumps(layer_specs, indent=1))

    return json_dst_dir    


class GetData:
    def __init__(self, json_dir, output_dir, poly_mask):
        # path to json files
        self.json_dir = json_dir
        self.source_data_dir = output_dir / "brondata"
        self.mask = poly_mask

    # Optional: select a part of the sourcedata by a shape
    def run(self, json_subset:list[str] | None = None):

        # if not a selection of json-objects is specified, we look trough json_dir
        if json_subset is not None:
            json_objects = [self.json_dir.joinpath(i["json_file"]) for i in JSON_OBJECTS if Path(i["json_file"]).stem in json_subset]
        else:
            json_objects = [self.json_dir.joinpath(i["json_file"]) for i in JSON_OBJECTS]

        
        if self.source_data_dir.exists():
            shutil.rmtree(self.source_data_dir)
        
        report_dir = self.source_data_dir / "report"
        report_dir.mkdir(parents=True)

        # write damo-object
        for json_object in json_objects:
            logging.info(f"Object path: {str(json_object)}")
            obj = HydamoObject(
                json_object,
                mask=self.mask,
                report_dir=report_dir,
                print_gml=False,
            )

            obj.write_gpkg(self.source_data_dir)
