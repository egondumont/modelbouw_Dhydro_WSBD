from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from wbd_tools.resultaten.common import get_his_file


def stations_time_series(mdu_file: Path, variable) -> pd.DataFrame:
    his_file = get_his_file(mdu_file)
    with xr.open_dataset(his_file) as ds:
        station_ids = np.char.strip(np.char.decode(ds["station_id"].values, "utf-8"))
        data = ds[variable].to_numpy()
        time = pd.to_datetime(ds["time"].values)

    return pd.DataFrame(data, index=time, columns=station_ids)


def station_locations(mdu_file: Path, epsg: int | None = 28992) -> gpd.GeoDataFrame:
    """Return the stations of a FM model as a GeoDataFrame

    Args:
        mdu_file (Path): mdu_file of fm-model
        epsg (int | None, optional): crs epsg code. Defaults to 28992.

    Raises:
        ValueError: In case no projection epsg is provided nor read from fm NetCDF-file

    Returns:
        gpd.GeoDataFrame: GeoDataFrame with station ids and names and geometry (Point)
    """
    his_file = get_his_file(mdu_file)

    with xr.open_dataset(his_file) as ds:
        # get epsg
        if epsg is None:
            epsg = ds["projected_coordinate_system"].attrs["epsg"]
        if epsg is None:
            raise ValueError("Define epsg as projected_coordinate_system is not defined in netcdf_file: {his_file}")

        station_ids = np.char.strip(np.char.decode(ds["station_id"].values, "utf-8"))
        station_names = np.char.strip(np.char.decode(ds["station_name"].values, "utf-8"))
        gdf = gpd.GeoDataFrame(
            data={
                "station_id": station_ids,
                "station_name": station_names,
            },
            geometry=gpd.GeoSeries.from_xy(ds["station_x_coordinate"].values, ds["station_y_coordinate"].values),
            crs=epsg,
        )
    return gdf


def stations_to_folium_map(mdu_file: Path, epsg: int | None = 28992):
    """Create a stations_map.html in the fm output-folder and graphs in the graphs subfolder
    Args:
        mdu_file (Path):  mdu_file of fm-model
        epsg (int | None, optional): crs epsg code. Defaults to 28992. Defaults to 28992.
    """
    gdf = station_locations(mdu_file=mdu_file, epsg=epsg)

    # init map
    gdf_4326 = gdf.to_crs(epsg=4326)
    xmin, ymin, xmax, ymax = gdf_4326.total_bounds
    m = folium.Map(location=[np.average((ymin, ymax)), np.average((xmin, xmax))], zoom_start=11)

    his_file = get_his_file(mdu_file)
    output_dir = his_file.parent
    graphs_dir = output_dir.joinpath("graphs")
    graphs_dir.mkdir(exist_ok=True, parents=True)

    waterlevel_df = stations_time_series(mdu_file=mdu_file, variable="waterlevel")
    discharge_magnitude_df = stations_time_series(mdu_file=mdu_file, variable="discharge_magnitude")

    time = waterlevel_df.index.to_numpy()

    for row in gdf.to_crs(epsg=4326).itertuples():
        # image path
        filename = f"{row.station_id}.png"
        image_path = graphs_dir / filename

        # create popup
        html = f'<img src="{image_path.relative_to(output_dir).as_posix()}" width="600"/>'
        popup = folium.Popup(html, max_width=600)

        # add marker
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=4,
            color="blue",
            fill=True,
            fill_color="blue",
            popup=popup,
        ).add_to(m)

        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            icon=folium.features.DivIcon(
                icon_size=(0, 0),  # let the div size itself
                icon_anchor=(0, 0),  # anchor at marker point (top-left of the div)
                html=f"""
            <div style="
                white-space: nowrap;
                font-size: 12px;
                line-height: 1;
                color: #1f77b4;
                font-weight: 600;
                pointer-events: none;  /* clicks go through to the circle */
                transform: translate(6px, -6px);  /* nudge right and slightly up */
            ">{row.station_id}</div>
            """,
            ),
        ).add_to(m)

        # export time-series as fig
        y_discharge = waterlevel_df[row.station_id].to_numpy()
        y_waterlevel = discharge_magnitude_df[row.station_id].to_numpy()

        fig, ax1 = plt.subplots(figsize=(8, 4))

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
        ax2.grid(True)

        # Titel
        fig.suptitle(f"{row.station_id} - {row.station_name}", fontsize=10)

        plt.tight_layout()
        fig.savefig(image_path)
        plt.close(fig)
    m.save(output_dir / "stations_map.html")
