"""
Make sure the working directory is the folder where this file is located
"""
import sys
import os
import logging
#import geopandas as gpd
#from codecs import ignore_errors
#from datetime import datetime
#import json
#import jsonschema
#from jsonschema import validate
# Relative path to root folder of script
sys.path.append(r".")
from tohydamogml.hydamo_table import HydamoObject

class GETDATA:

    def __init__(self,root_dir,data_dir,input_dir,shapefiles):
    # path to json files
        self.root_dir=root_dir
        self.data_dir=data_dir
        self.input_dir=input_dir
        self.shapefiles=shapefiles
        self.path_json = os.path.join(self.root_dir,r"json")

        # Optional: filepath to a python file with attributes functions. In the json files is referred to these functions.
        self.attr_function = os.path.join(self.path_json, "attribute_functions.py")
        

    # Optional: select a part of the sourcedata by a shape
    def run(self):
        for shapefile in self.shapefiles:
            mask = str(os.path.join(self.input_dir,shapefile+ '.shp'))
            # path to export gml files
            export_path = os.path.join(self.data_dir,"brondata",shapefile)
            if not os.path.exists(export_path):
                os.makedirs(export_path)
            
            # Make folder for logging
            report_folder = os.path.join(export_path,'report')
            if not os.path.exists(report_folder):
                os.makedirs(report_folder)
            
            # list with json objects to loop through
            json_objects = [
            os.path.join(self.path_json, "hydroobject.json"),
            os.path.join(self.path_json, "stuw.json"),
            os.path.join(self.path_json, "kunstwerkopening.json"),
            os.path.join(self.path_json, "regelmiddel.json"),
            os.path.join(self.path_json, "dwarsprofiel.json"),
            os.path.join(self.path_json, "duikersifonhevel.json"),
            os.path.join(self.path_json, "afsluitmiddel.json"),
            # os.path.join(self.path_json, "brug.json"),
            os.path.join(self.path_json, "gemaal.json"),
            os.path.join(self.path_json, "pomp.json"),
            # os.path.join(path_json, "sturing.json"),
            # os.path.join(self.path_json, "bodemval.json"),
            # os.path.join(self.path_json, "randvoorwaarden.json"),
            ]

            #profile_objects = [os.path.join(path_json, "brug_dwp.json"), os.path.join(path_json, "profiel_legger.json")]

            for json_object in json_objects:
                logging.info(f'Object path: {str(json_object)}')

                if mask:
                    obj = HydamoObject(json_object, mask=mask, file_attribute_functions=self.attr_function, outputfolder=report_folder,print_gml=False)
                else:
                    obj = HydamoObject(json_object, file_attribute_functions=self.attr_function, outputfolder=report_folder,print_gml=False)
                #obj.validate_gml(write_error_log=True)
                #obj.write_gml(export_path, ignore_errors=True, skip_validation=True)
 
                obj.write_gpkg(export_path)

