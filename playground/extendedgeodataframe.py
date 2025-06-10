# %%
import logging
from copy import deepcopy

import geopandas as gpd


class ExtendedGeoDataFrame(gpd.GeoDataFrame):
    _metadata = ["required_columns", "geotype", "related"]

    def __init__(self, *args, geotype=None, required_columns=None, related=None, logger=logging, **kwargs):
        # Store extended metadata
        self.required_columns = required_columns[:] if required_columns else []
        self.geotype = geotype
        self.related = deepcopy(related)

        # Optionally modify kwargs['columns'] (only if this is a user-level init)
        if "columns" in kwargs:
            for col in self.required_columns:
                if col not in kwargs["columns"]:
                    kwargs["columns"].append(col)

        super().__init__(*args, **kwargs)

    @property
    def _constructor(self):
        def _c(*args, **kwargs):
            obj = ExtendedGeoDataFrame(
                *args,
                geotype=getattr(self, "geotype", None),
                required_columns=getattr(self, "required_columns", []),
                related=deepcopy(getattr(self, "related", None)),
                **kwargs,
            )
            return obj

        return _c

    def extended_method(self):
        print("working!")
