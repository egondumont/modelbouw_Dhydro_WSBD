# %%
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

file_dir = Path(__file__).parent

with xr.open_dataset(
    r"d:\projecten\D2508.WBD_modelinstrumentarium\06.modellen\output\aa_of_weerijs\20250723\dhydro\fm\DFM_OUTPUT_aa_of_weerijs\aa_of_weerijs_his.nc"
) as ds:
    gdf = gpd.GeoDataFrame(
        data={
            "station_id": np.char.strip(np.char.decode(ds["station_id"].values, "utf-8")),
            "station_name": np.char.strip(np.char.decode(ds["station_name"].values, "utf-8")),
        },
        geometry=gpd.GeoSeries.from_xy(ds["station_x_coordinate"].values, ds["station_y_coordinate"].values),
        crs=ds["projected_coordinate_system"].attrs["epsg"],
    )
    discharge = ds["discharge_magnitude"].to_numpy()
    waterlevel = ds["waterlevel"].to_numpy()
    selected_vars = [var for var in ds.data_vars if var.startswith("water_balance")]
    subset = ds[selected_vars]
    waterbalance_df = subset.to_dataframe().reset_index()
    waterbalance_df.set_index("time", inplace=True)
    time = pd.to_datetime(ds["time"].values)

# plot waterbalance

gdf_4326 = gdf.to_crs(epsg=4326)
xmin, ymin, xmax, ymax = gdf_4326.total_bounds
m = folium.Map(location=[np.average((ymin, ymax)), np.average((xmin, xmax))], zoom_start=11)


graphs_dir = file_dir.joinpath("graphs")
graphs_dir.mkdir(exist_ok=True, parents=True)

for i, row in enumerate(gdf.to_crs(epsg=4326).itertuples()):
    # image path
    filename = f"{row.station_id}.png"
    image_path = graphs_dir / filename

    # create popup
    html = f'<img src="{image_path.relative_to(file_dir).as_posix()}" width="400"/>'
    popup = folium.Popup(html, max_width=400)

    # add marker
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=4,
        color="blue",
        fill=True,
        fill_color="blue",
        popup=popup,
    ).add_to(m)

    # export time-series as fig
    y_discharge = discharge[:, i]
    y_waterlevel = ds["waterlevel"].values[:, i]

    fig, ax1 = plt.subplots(figsize=(4, 2))

    # Eerste as: discharge
    ax1.plot(time, y_discharge, color="tab:blue", label="Discharge")
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Discharge", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.tick_params(axis="x", rotation=45)
    ax1.grid(True)

    # Tweede y-as (waterlevel)
    ax2 = ax1.twinx()
    ax2.plot(time, y_waterlevel, color="tab:orange", label="Water level")
    ax2.set_ylabel("Water level", color="tab:orange")
    ax2.tick_params(axis="y", labelcolor="tab:orange")

    # Titel
    fig.suptitle(f"{row.station_id} - {row.station_name}", fontsize=10)

    plt.tight_layout()
    fig.savefig(image_path)
    plt.close(fig)
m.save(file_dir / "stations_map.html")
