# %%
from datetime import datetime, timedelta
from pathlib import Path

from wbd_tools.clean_raster import generate_constant_time_rasters, opschonen_raster

ahn_file = Path(
    r"d:\projecten\D2508.WBD_modelinstrumentarium\02.DTM2CAT\dtm2cat\data\hoogtekaart\AHN4\dtm_2m_filled.tif"
)
start_time = datetime(2016, 6, 1)
end_time = datetime(2016, 6, 3)


# ahn
opschonen_raster(ahn_file, raster_out_file=Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\07.rasters\ahn.tif"))

# landgebruik
opschonen_raster(
    raster_file=Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\07.rasters\Reclass_LGN22_Clip.tif"),
    raster_out_file=Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\07.rasters\landgebruik.tif"),
    min_val=1,
    max_val=15,
)

# bodem
opschonen_raster(
    raster_file=Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\07.rasters\Reclass_LGN22_Clip.tif"),
    raster_out_file=Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\07.rasters\bodemtypen.tif"),
    min_val=8,
    max_val=8,
)

# precipitation
generate_constant_time_rasters(
    raster_template_file=ahn_file,
    dst_folder=Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\07.rasters\precipitation"),
    raster_prefix="neerslag",
    start_time=start_time,
    end_time=end_time,
    delta_time=timedelta(hours=1),
    constant_value=4 / 24,
    cell_size=25,
)


# evaporation
generate_constant_time_rasters(
    raster_template_file=ahn_file,
    dst_folder=Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\07.rasters\evaporation"),
    raster_prefix="verdamping",
    start_time=datetime(2016, 6, 1),
    end_time=datetime(2016, 6, 3),
    delta_time=timedelta(days=1),
    constant_value=1,
    cell_size=25,
)

# seepage
generate_constant_time_rasters(
    raster_template_file=ahn_file,
    dst_folder=Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\07.rasters\seepage"),
    raster_prefix="kwel",
    start_time=datetime(2016, 6, 1),
    end_time=datetime(2016, 6, 3),
    delta_time=timedelta(days=1),
    constant_value=0,
    cell_size=25,
)
