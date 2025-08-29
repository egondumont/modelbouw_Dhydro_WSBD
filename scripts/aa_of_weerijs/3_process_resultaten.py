# %%
from pathlib import Path

import pandas as pd

from wbd_tools.fm.read_bc import read_flow_boundaries
from wbd_tools.fnames import get_fnames, get_output_dir
from wbd_tools.resultaten import stations_to_folium_map
from wbd_tools.resultaten.stations import stations_time_series
from wbd_tools.resultaten.waterbalance import water_balance

fm_dir = "dhydro_1d2d_cflmax_07_no_bc"
fnames = get_fnames()
modelnaam = Path(__file__).parent.name
output_dir = get_output_dir(model_name=modelnaam, date=None)

# %%

# op basis van mdu-file maken we een folium map met stations
mdu_file = output_dir.joinpath(fm_dir, "fm", f"{modelnaam}.mdu")
stations_to_folium_map(mdu_file)

# %%

# inlezen en sommeren flow-boundadries
rvw_df = read_flow_boundaries(mdu_file)
rvw_series = rvw_df.sum(axis=1).cumsum() * 60 * 60
rvw_series.name = "randvoorwaarden"

# uitlezen waterbalans
wb_df = water_balance(mdu_file, remove_no_flow=True)

# uitlezen stations
q_df = stations_time_series(mdu_file, "discharge_magnitude")

# alles combineren
summary_df = pd.concat(
    [wb_df["water_balance_boundaries_in"], (q_df[["BEB", "AAOW"]].sum(axis=1).cumsum() * 5 * 60)],
    axis=1,
)

summary_df.columns = ["fm waterbalans", "observatiepunten"]
ax = summary_df.plot()
rvw_series.plot(ax=ax, legend=True)
ax.set_title("controle Q-randen")
ax.set_ylabel("m3")
ax.grid(True, which="both", axis="both", linestyle="--", color="grey", alpha=0.7)


# %%

# afvoer over
