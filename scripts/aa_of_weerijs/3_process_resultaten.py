# %%
from pathlib import Path

from wbd_tools.fnames import get_fnames, get_output_dir
from wbd_tools.resultaten import stations_to_folium_map

fnames = get_fnames()
modelnaam = Path(__file__).parent.name
output_dir = get_output_dir(model_name=modelnaam, date=None)

# %%

# op basis van mdu-file maken we een folium map met stations
mdu_file = output_dir.joinpath("dhydro", "fm", f"{modelnaam}.mdu")
stations_to_folium_map(mdu_file)
