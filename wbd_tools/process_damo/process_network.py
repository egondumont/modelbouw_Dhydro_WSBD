# this scripts determines the dangling nodes of a shape (lines)
# helpfull in determining the locations were snapping might be needed
# Rineke Hulsman, RHDHV, 13 january 2021
# Egon Dumont, WSBD, 29 January 2025


import copy
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import distance, intersects
from shapely.ops import snap, split


class ProcessNetwork:
    def __init__(self, output_dir, checkbuffer):
        self.output_dir = Path(output_dir)
        self.source_data_dir = self.output_dir / "brondata"
        self.checkbuffer = checkbuffer

    def run(self, process_profiles):
        waterloop = gpd.read_file(self.output_dir / "networkraw.gpkg")

        waterloop["globalid"] = waterloop["code"]

        splitpoints = []  # list of locations where hydroobjects should be split due to intersection with a second hydroobject

        # Snapping hydroobject ends to each other where needed
        for index, row in waterloop.iterrows():
            start_point = gpd.points_from_xy([row.geometry.coords.xy[0][0]], [row.geometry.coords.xy[1][0]])
            end_point = gpd.points_from_xy([row.geometry.coords.xy[0][-1]], [row.geometry.coords.xy[1][-1]])
            # gdb-index of geometries intersecting with start point of current hydroobject:
            I_1 = waterloop.sindex.query(start_point, predicate="intersects")
            # gdb-index of geometries intersecting with end point of current hydroobject:
            I_2 = waterloop.sindex.query(end_point, predicate="intersects")
            I_self = []  # indexes of hydroobjects that intersect with both the start and end vertex of the current hydroobject, and index of the current hydroobject
            I_conn_s = []  # indexes of hydroobjects which start or end vertex intersect with start vertex of current hydroobject
            I_conn_e = []  # indexes of hydroobjects which start or end vertex intersect with end vertex of current hydroobject
            str_start = ""
            str_end = ""

            for check_i in I_1[1]:  # for each geometry intersecting with start point of current hydroobject....
                if check_i in I_2[1]:
                    I_self.append(check_i)
                else:  # store start and end point geometry of hydroobject intersecting with start point of current hydroobject...
                    target_start = gpd.points_from_xy(
                        [waterloop.loc[check_i, "geometry"].coords.xy[0][0]],
                        [waterloop.loc[check_i, "geometry"].coords.xy[1][0]],
                    )
                    target_end = gpd.points_from_xy(
                        [waterloop.loc[check_i, "geometry"].coords.xy[0][-1]],
                        [waterloop.loc[check_i, "geometry"].coords.xy[1][-1]],
                    )
                    # If hydroobject start only connects to start or end vertice of other hydroobject (i.e. no connection to the edge of the side of another hydroobject)
                    if start_point == target_start or start_point == target_end:
                        I_conn_s.append(check_i)

            for check_i in I_2[1]:  # for each geometry intersecting with end point of current hydroobject....
                if check_i not in I_1[1]:
                    target_start = gpd.points_from_xy(
                        [waterloop.loc[check_i, "geometry"].coords.xy[0][0]],
                        [waterloop.loc[check_i, "geometry"].coords.xy[1][0]],
                    )
                    target_end = gpd.points_from_xy(
                        [waterloop.loc[check_i, "geometry"].coords.xy[0][-1]],
                        [waterloop.loc[check_i, "geometry"].coords.xy[1][-1]],
                    )
                    # If hydroobject end only connects to start or end vertice of other hydroobject (i.e. no connection to the edge of the side of another hydroobject)
                    if end_point == target_start or end_point == target_end:
                        I_conn_e.append(check_i)

            if (
                len(I_conn_s) == 0
            ):  # If there is no upstream hydroobject which start or end vertex intersects with the current hydroobject
                start_buffer = start_point.buffer(self.checkbuffer[0])
                i_temp = waterloop.sindex.query(start_buffer, predicate="intersects")
                i_potential = []
                for check_i in i_temp[1]:
                    if check_i not in I_self:
                        i_potential.append(check_i)
                # if no other hydroobjects were found within specified distance (checkbuffer[0]) from the start point of the current hydrooject
                if len(i_potential) == 0:
                    start_buffer = start_point.buffer(self.checkbuffer[1])
                    i_temp = waterloop.sindex.query(start_buffer, predicate="intersects")
                    i_potential = []
                    for check_i in i_temp[1]:
                        if check_i not in I_self:
                            i_potential.append(check_i)
                    if len(i_potential) == 0:
                        str_start = "start point, "
                    else:  # if other hydroobjects were found within the larger specified distance (checkbuffer[1]) from the start point of the current hydrooject...
                        target_start = gpd.points_from_xy(
                            [waterloop.loc[i, "geometry"].coords.xy[0][0] for i in i_potential],
                            [waterloop.loc[i, "geometry"].coords.xy[1][0] for i in i_potential],
                        )
                        target_end = gpd.points_from_xy(
                            [waterloop.loc[i, "geometry"].coords.xy[0][-1] for i in i_potential],
                            [waterloop.loc[i, "geometry"].coords.xy[1][-1] for i in i_potential],
                        )
                        all_targets = gpd.GeoDataFrame(geometry=np.append(target_start, target_end))
                        all_targets["distance"] = start_point.distance(all_targets)
                        i_min = all_targets[
                            "distance"
                        ].idxmin()  # finding the (index of the) coordinates of the hydroobject start/end point that is closest to the start point of the current hydroobject

                        if all_targets.loc[i_min, "distance"] <= self.checkbuffer[1]:
                            waterloop.loc[index, "geometry"] = snap(
                                waterloop.loc[index, "geometry"],
                                all_targets.loc[i_min, "geometry"],
                                self.checkbuffer[1],
                            )
                            str_start = f"start punt verplaatst naar punt binnen {self.checkbuffer[1]}, "
                        else:
                            str_start = "geen punt in de buurt start, split doel waterloop, "
                            # store point geometries where hydroobject should be split:
                            splitpoints.append(start_point[0])

                else:
                    target_start = gpd.points_from_xy(
                        [waterloop.loc[i, "geometry"].coords.xy[0][0] for i in i_potential],
                        [waterloop.loc[i, "geometry"].coords.xy[1][0] for i in i_potential],
                    )
                    target_end = gpd.points_from_xy(
                        [waterloop.loc[i, "geometry"].coords.xy[0][-1] for i in i_potential],
                        [waterloop.loc[i, "geometry"].coords.xy[1][-1] for i in i_potential],
                    )
                    all_targets = gpd.GeoDataFrame(geometry=np.append(target_start, target_end))
                    all_targets["distance"] = start_point.distance(all_targets)
                    i_min = all_targets["distance"].idxmin()

                    if all_targets.loc[i_min, "distance"] <= self.checkbuffer[1]:
                        waterloop.loc[index, "geometry"] = snap(
                            waterloop.loc[index, "geometry"], all_targets.loc[i_min, "geometry"], self.checkbuffer[1]
                        )
                        str_start = f"start punt verplaatst naar punt binnen {self.checkbuffer[0]}, "
                    else:
                        str_start = "geen punt in de buurt start, split doel waterloop, "
                        splitpoints.append(start_point[0])  # store point geometries where hydroobject should be split

            # if no hydroobject has a start/end point that intersects with the end point of the current hydroobject
            if len(I_conn_e) == 0:
                end_buffer = end_point.buffer(self.checkbuffer[0])
                i_temp = waterloop.sindex.query(end_buffer, predicate="intersects")
                i_potential = []
                for check_i in i_temp[1]:
                    if check_i not in I_self:
                        i_potential.append(check_i)
                if len(i_potential) == 0:
                    end_buffer = end_point.buffer(self.checkbuffer[1])
                    i_temp = waterloop.sindex.query(end_buffer, predicate="intersects")
                    i_potential = []
                    for check_i in i_temp[1]:
                        if check_i not in I_self:
                            i_potential.append(check_i)
                    # If no other hydroobject close to end point of current hydrobject:
                    if len(i_potential) == 0:
                        str_end = "eind punt. "
                    # snap hydroobject endpoint to closest other hydroobject:
                    else:
                        target_start = gpd.points_from_xy(
                            [waterloop.loc[i, "geometry"].coords.xy[0][0] for i in i_potential],
                            [waterloop.loc[i, "geometry"].coords.xy[1][0] for i in i_potential],
                        )
                        target_end = gpd.points_from_xy(
                            [waterloop.loc[i, "geometry"].coords.xy[0][-1] for i in i_potential],
                            [waterloop.loc[i, "geometry"].coords.xy[1][-1] for i in i_potential],
                        )
                        all_targets = gpd.GeoDataFrame(geometry=np.append(target_start, target_end))
                        all_targets["distance"] = end_point.distance(all_targets)
                        i_min = all_targets["distance"].idxmin()

                        if all_targets.loc[i_min, "distance"] <= self.checkbuffer[1]:
                            waterloop.loc[index, "geometry"] = snap(
                                waterloop.loc[index, "geometry"],
                                all_targets.loc[i_min, "geometry"],
                                self.checkbuffer[1],
                            )

                            str_end = f"eind punt verplaatst naar punt binnen {self.checkbuffer[1]}."
                        else:
                            str_end = "geen punt in de buurt einde, split doel waterloop."
                            splitpoints.append(
                                end_point[0]
                            )  # store point geometries where hydroobject should be split

                else:
                    target_start = gpd.points_from_xy(
                        [waterloop.loc[i, "geometry"].coords.xy[0][0] for i in i_potential],
                        [waterloop.loc[i, "geometry"].coords.xy[1][0] for i in i_potential],
                    )
                    target_end = gpd.points_from_xy(
                        [waterloop.loc[i, "geometry"].coords.xy[0][-1] for i in i_potential],
                        [waterloop.loc[i, "geometry"].coords.xy[1][-1] for i in i_potential],
                    )
                    all_targets = gpd.GeoDataFrame(geometry=np.append(target_start, target_end))
                    all_targets["distance"] = end_point.distance(all_targets)
                    i_min = all_targets["distance"].idxmin()
                    if all_targets.loc[i_min, "distance"] <= self.checkbuffer[1]:
                        waterloop.loc[index, "geometry"] = snap(
                            waterloop.loc[index, "geometry"], all_targets.loc[i_min, "geometry"], self.checkbuffer[1]
                        )
                        str_end = f"eind punt verplaatst naar punt binnen {self.checkbuffer[0]}."
                    else:
                        str_end = "geen punt in de buurt einde, split doel waterloop."
                        splitpoints.append(end_point[0])  # store point geometries where hydroobject should be split

            waterloop.loc[index, "commentconnect"] = str_start + str_end

        # remove hydrobjects that are fish passages bypassing weirs
        vispassages = gpd.read_file(self.source_data_dir / "vispassage.gpkg")
        for index, vispassage in vispassages.iterrows():
            buffer = vispassage.geometry.buffer(self.checkbuffer[0])
            for index2, row in waterloop.iterrows():
                if intersects(row.geometry, buffer):
                    if (
                        vispassage["soort_vispassage"] in [2, 98, 99, "2", "98", "99"]
                        and any(c in vispassage["opmerking"] for c in ["slot", "Wit"])
                        and "hoofdloop" not in vispassage["opmerking"]
                    ):
                        # found fish passage bypassing weir
                        waterloop.drop(index2, inplace=True)
                    elif (
                        not vispassage["bovenstroomse_drempelhoogte"]
                        or vispassage["bovenstroomse_drempelhoogte"] > 90
                        or vispassage["bovenstroomse_drempelhoogte"] < -10
                    ):
                        waterloop.loc[index, "comment_vispassage"] = "vispassage zonder bovenstroomse drempelhoogte"

        # split hydroobjects where other hydroobjects join or diverge from current hydroobject
        j = 0
        for index, line in waterloop.geometry.items():
            for i, p in enumerate(splitpoints):
                # first use 2 if statements to check if hydroobject needs to be split
                if distance(line, p) < self.checkbuffer[0]:
                    # if the current hydroobject is close enough to the current split point
                    if not line.boundary.contains(p):
                        # if the splitpoint is not the endpoint of the current hydroobject
                        # make new profiles where the hydroobject will be split
                        hydroobject_code = waterloop.loc[index, "code"][:8]  # code of original hydroobject pre split
                        if j == 0:
                            process_profiles.add_profiles_near_split(line, hydroobject_code, p, first_call=True)
                        elif j == len(splitpoints) - 1:
                            process_profiles.add_profiles_near_split(line, hydroobject_code, p, last_call=True)
                        else:
                            process_profiles.add_profiles_near_split(line, hydroobject_code, p)
                        j += 1  # increment j
                        # give each half of the split a separate row in the hydroobjects geodataframe
                        # start with first half:
                        waterloop.loc[index, "geometry"] = split(snap(line, p, self.checkbuffer[0]), p).geoms[0]
                        row = copy.deepcopy(waterloop.loc[index])
                        row["code"] = f"{row['code']}d{i}"  # making code unique
                        row["globalid"] = f"{row['globalid']}d{i}"  # making globalid unique
                        row["nen3610id"] = row["nen3610id"][:-2]  # making nen360id unique
                        row["geometry"] = split(snap(line, p, self.checkbuffer[0]), p).geoms[1]
                        # append second half of split hydroobject to hydroobjects
                        waterloop = pd.concat([waterloop, row.to_frame().T], ignore_index=True)

        waterloop.set_crs(epsg=28992, inplace=True, allow_override=True)
        waterloop.to_file(self.output_dir / "hydroobject.gpkg", driver="GPKG")
