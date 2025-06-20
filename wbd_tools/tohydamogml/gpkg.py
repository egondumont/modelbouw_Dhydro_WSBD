import geopandas as gpd
import json
import os
import logging
from datetime import datetime

class Gpkg:
    def validate(self):
        """Validate GPKG with JSON Schema HyDAMO2.2
        """
        df = gpd.read_file(self)
        # Load the JSON file
        with open("../json/HyDAMO_2.2.json") as f:
            validation_rules = json.load(f)
            print(validation_rules.keys())
            a = (validation_rules['definitions'])
            b = a['hydroobject']['properties']

        # check if all columns are present
        f = b.keys()
        for kolommen in f:
            x = 0
            #    print("kolommen ", kolommen)
            for column in df.columns:
                if column == kolommen:
                    x = x + 1
                    logging.info(f'{str(kolommen)}' " aanwezig")
                    break
                else:
                    x = 0
            if x == 0:
                logging.info(f'{str(kolommen)}' " ontbreekt")
