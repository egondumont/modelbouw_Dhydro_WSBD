import logging
import math

import geopandas as gpd
import shapely
import tqdm
from shapely.geometry import LineString, Point


def _make_profile(damo_gdf, obj=None):
    data = []
    # new_points = gpd.GeoDataFrame(geometry='geometry',crs = 'EPSG:28992')
    for i, row in tqdm.tqdm(damo_gdf.iterrows(), total=len(damo_gdf)):
        length = row.geometry.length
        if length > 20:
            up_dist_main, up_dist_help = 5, 10
            down_dist_main, down_dist_help = length - 5, length - 10
        else:
            up_dist_main, up_dist_help = length * 0.25, length * 0.5
            down_dist_main, down_dist_help = length * 0.75, length * 0.5
        up_line = _make_xyz(
            row=row,
            distance_main=up_dist_main,
            distance_help=up_dist_help,
            bottom_level=row["WS_BH_BOVENSTROOMS_L"],
            bottom_width=row["WS_BODEMBREEDTE_L"],
            talud_l=row["WS_TALUD_LINKS_L"],
            talud_r=row["WS_TALUD_RECHTS_L"],
            total_depth=5,
        )
        up_points = list(up_line.coords)

        for j in range(len(up_points)):
            if len(up_points[j]) == 3:
                new = {
                    "geometry": Point(up_points[j]),
                    "profiellijnid": row["CODE"],
                    "codevolgnummer": j + 1,
                    "globalid": f"{row['CODE']}_{j + 1}",
                    "profielpuntid": f"{row['CODE']}_{j + 1}",
                    "typeruwheid": "StricklerKs",
                    "TypeProfielCode": 4,
                    "RuwheidsTypeCode": 4,
                    "RuwheidsWaardeLaag": 30,
                    "RuwheidsWaardeHoog": 20,
                    "Z": up_points[j][2],
                }
            else:
                new = {
                    "geometry": Point(up_points[j]),
                    "profiellijnid": row["CODE"],
                    "codevolgnummer": j + 1,
                    "globalid": f"{row['CODE']}_{j + 1}",
                    "profielpuntid": f"{row['CODE']}_{j + 1}",
                    "typeruwheid": "StricklerKs",
                    "TypeProfielCode": 4,
                    "RuwheidsTypeCode": 4,
                    "RuwheidsWaardeLaag": 30,
                    "RuwheidsWaardeHoog": 20,
                    "Z": -999,
                }
            data.append(new)
        down_line = _make_xyz(
            row=row,
            distance_main=down_dist_main,
            distance_help=down_dist_help,
            bottom_level=row["WS_BH_BENEDENSTROOMS_L"],
            bottom_width=row["WS_BODEMBREEDTE_L"],
            talud_l=row["WS_TALUD_LINKS_L"],
            talud_r=row["WS_TALUD_RECHTS_L"],
            total_depth=5,
        )
        down_points = list(down_line.coords)

        for j in range(len(up_points)):
            if len(down_points[j]) == 3:
                new = {
                    "geometry": Point(down_points[j]),
                    "profiellijnid": f"{row['CODE']}_down",
                    "codevolgnummer": j + 1,
                    "globalid": f"{row['CODE']}_down_{j + 1}",
                    "profielpuntid": f"{row['CODE']}_down_{j + 1}",
                    "TypeProfielCode": 4,
                    "typeruwheid": "StricklerKs",
                    "RuwheidsTypeCode": 4,
                    "RuwheidsWaardeLaag": 30,
                    "RuwheidsWaardeHoog": 20,
                    "Z": down_points[j][2],
                }
            else:
                new = {
                    "geometry": Point(down_points[j]),
                    "profiellijnid": f"{row['CODE']}_down",
                    "codevolgnummer": j + 1,
                    "globalid": f"{row['CODE']}_down_{j + 1}",
                    "profielpuntid": f"{row['CODE']}_down_{j + 1}",
                    "typeruwheid": "StricklerKs",
                    "TypeProfielCode": 4,
                    "RuwheidsTypeCode": 4,
                    "RuwheidsWaardeLaag": 30,
                    "RuwheidsWaardeHoog": 20,
                    "Z": -999,
                }
            data.append(new)
    new_points = gpd.GeoDataFrame(data, geometry="geometry", crs="EPSG:28992")
    return new_points


def _make_xyz(
    row,
    distance_main,
    distance_help,
    bottom_level,
    bottom_width,
    talud_l,
    talud_r,
    total_depth=5,
):
    # Set up basic profile parameters: bottom width & total width based on talud
    if math.isnan(bottom_width):
        bottom_width = 2
        logging.info(f"Profielen maken: {row['CODE']} geen bodembreedte gevonden, bodembreedte op 2 gezet.")
    total_width = bottom_width + total_depth * talud_l + total_depth * talud_r
    if math.isnan(total_width):
        total_width = bottom_width + 2 * total_depth * 2
        logging.info(f"Profielen maken: {row['CODE']} geen taluds gevonden, talud op 2 gezet.")

    upper_level = bottom_level + total_depth

    # Profile will be created using a short sub-segment of the source-line-geometry.
    l = row["geometry"].length
    logging.info(
        f"Profielen maken: {row['CODE']}, op afstand: {distance_main} van lengte: {l}, "
        f"bodembreedte: {bottom_width}, "
        f"bodemhoogte: {bottom_level}, totale diepte: {total_depth}"
    )

    point1 = row["geometry"].interpolate(distance_main)
    point2 = row["geometry"].interpolate(distance_help)
    baseline = LineString([point1, point2])

    left_inner = baseline.parallel_offset(bottom_width / 2, "left")
    right_inner = baseline.parallel_offset(bottom_width / 2, "right")
    left_inner_point = shapely.ops.transform(lambda x, y: (x, y, bottom_level), Point(left_inner.coords[0]))
    right_inner_point = shapely.ops.transform(lambda x, y: (x, y, bottom_level), Point(right_inner.coords[0]))

    left_outer = baseline.parallel_offset(total_width / 2, "left")
    right_outer = baseline.parallel_offset(total_width / 2, "right")
    left_outer_point = shapely.ops.transform(lambda x, y: (x, y, upper_level), Point(left_outer.coords[0]))
    right_outer_point = shapely.ops.transform(lambda x, y: (x, y, upper_level), Point(right_outer.coords[0]))

    profile_line = LineString([left_outer_point, left_inner_point, right_inner_point, right_outer_point])
    return profile_line
