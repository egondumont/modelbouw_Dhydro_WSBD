import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiPoint, Point
from shapely.ops import split
from shapely.strtree import STRtree
from shapely.ops import substring
import numpy as np


def snap_point_to_line(
    point: Point, line: LineString, tolerance: float | None = 5
) -> Point:
    """Snap a Point to a LineString within tolerance

    Args:
        point (Point): Point to snap
        line (LineString): LineString to snap to
        tolerance (int, optional): _description_. Defaults to 5.

    Returns:
        Point: snapped point
    """
    projected = line.project(point)
    snapped_point = line.interpolate(projected)
    if tolerance:
        if snapped_point.distance(point) <= tolerance:
            snapped_point = None
    return snapped_point


def split_line_by_length(line: LineString, max_length: float = 500) -> list[LineString]:
    """Split a shapely LineString into smaller segments

    Args:
        line (LineString): Input LineSting
        max_length (float, optional): Maximum length of every segment. Defaults to 500.

    Returns:
        list[LineString]: List of segments
    """
    length = line.length
    if length <= max_length:
        return [line]

    # Calculate number of full segments
    num_segments = int(np.ceil(length / max_length))
    distances = np.linspace(0, length, num_segments + 1)

    segments = [
        substring(line, distances[i], distances[i + 1])
        for i in range(num_segments)
        if substring(line, distances[i], distances[i + 1]).length > 0
    ]

    return segments


def split_lines_to_points(
    lines_gdf: gpd.GeoDataFrame,
    points_gdf: gpd.GeoDataFrame,
    tolerance: float = 5,
    max_length: float = 500,
) -> gpd.GeoDataFrame:
    """Splits LineStrings in a GeoDataFrame to a set of points and a max_length

    Args:
        lines_gdf (gpd.GeoDataFrame): input LineStrings
        points_gdf (gpd.GeoDataFrame):input Points
        tolerance (float, optional): tolerance for Point being on a LineString. Defaults to 5.
        max_length (float, optional): Maximum length of a LineString before it gets split. Defaults to 500.

    Raises:
        ValueError: If split yields other geometries than LineString

    Returns:
        gpd.GeoDataFrame: GeoDataFrame with LineStrings
    """

    # function to populate row
    def row_dict(row, geometry, columns):
        row_dict = {i: getattr(row, i) for i in columns if i != "geometry"}
        row_dict["geometry"] = geometry
        return row_dict

    # make sure points are projected to lines
    points_gdf = points_gdf.copy()
    if not lines_gdf.crs.equals(other=points_gdf.crs):
        points_gdf.to_crs(lines_gdf.crs, inplace=True)

    # Convert to plain list for STRtree and create mapping
    point_geoms = points_gdf.geometry.to_numpy()
    tree = STRtree(point_geoms)

    data = []
    for line_row in lines_gdf.itertuples():
        line = line_row.geometry

        # Get candidate point geometries near the line
        candidate_points = tree.query(line)

        # Snap points to line (within tolerance)
        snapped_points = [
            snap_point_to_line(point_geoms[p], line, tolerance)
            for p in candidate_points
        ]
        snapped_points = [p for p in snapped_points if p is not None]

        # split line into parts if we have snapped points
        if not snapped_points:
            line_parts = [line]
        else:
            # Sort and deduplicate snapped points along the line
            snapped_points = sorted(set(snapped_points), key=lambda p: line.project(p))

            try:
                line_parts = list(split(line, MultiPoint(snapped_points)).geoms)
            except Exception:
                line_parts = [line]

        for line_part in line_parts:
            if line_part.geom_type != "LineString":
                raise ValueError(
                    f"At Index {line_row.Index} splitting results in a geometry {line_part.geom_type}"
                )
            line_segments = split_line_by_length(line_part, max_length)
            for line_segment in line_segments:
                data += [
                    row_dict(
                        row=line_row, geometry=line_segment, columns=lines_gdf.columns
                    )
                ]

    return gpd.GeoDataFrame(
        data, index=pd.Index(range(1, len(data) + 1), name="fid"), crs=lines_gdf.crs
    )


def get_line_connections(
    lines_gdf: gpd.GeoDataFrame, points_gdf: gpd.GeoDataFrame, tolerance: float = 5
) -> gpd.GeoDataFrame:
    """Get all connections (points) between two lines in lines_gdf

    Args:
        lines_gdf (GeoDataFrame): GeoDataFrame with input LineStrings
        points_gdf (GeoDataFrame): GeoDataFrame with points containing meta-info
        tolerance (float, optional): tolerance to find points from lines. Defaults to 5.

    Raises:
        ValueError: If multiple points in point_gdf are at ends of lines_gdf

    Returns:
        gpd.GeoDataFrame: connection points between two lines, containing:
         - from_line_fid (fid in line_gdf it is connecting from)
         - to_line_fid (fid in line_gdf it is connecting to)
         - all columns in point_gdf it there is any within tolerance
    """
    # reset_index and keep original fid
    lines_gdf = lines_gdf.copy()
    lines_gdf["line_fid"] = lines_gdf.index
    lines_gdf.reset_index(drop=True, inplace=True)

    points_gdf = points_gdf.reset_index(drop=True).copy()

    # Build lookup of start and end points
    lines_gdf["start_point"] = lines_gdf.boundary.explode(index_parts=True).xs(
        0, level=1
    )
    lines_gdf["end_point"] = lines_gdf.boundary.explode(index_parts=True).xs(1, level=1)

    start_tree = STRtree(lines_gdf["start_point"].to_numpy())
    points_tree = STRtree(points_gdf.geometry.to_numpy())

    # Prepare the connections list
    data = []

    for row in lines_gdf.itertuples():
        end_pt = row.end_point
        # Find segments whose start matches this segment's end
        candidates = start_tree.query(end_pt)
        candidates = [
            i
            for i in candidates
            if end_pt.distance(lines_gdf.at[i, "start_point"]) <= tolerance
        ]
        if candidates:
            for candidate in candidates:
                if end_pt.distance(lines_gdf.at[candidate, "start_point"]) <= tolerance:
                    row_dict = {
                        "from_line_fid": row.line_fid,
                        "to_line_fid": lines_gdf.at[candidate, "line_fid"],
                        "geometry": end_pt,
                    }

                # find point candidates
                point_idx = [
                    i
                    for i in points_tree.query(end_pt)
                    if points_gdf.at[i, "geometry"].distance(end_pt) <= tolerance
                ]
                if len(point_idx) > 1:
                    raise ValueError(
                        f"for line fid {row.line_fid} two we find two points with fids {point_idx}"
                    )
                elif len(point_idx) == 1:
                    row_dict = {
                        **row_dict,
                        **{
                            k: v
                            for k, v in points_gdf.loc[point_idx[0]].items()
                            if k != "geometry"
                        },
                    }
                data += [row_dict]
        else:
            row_dict = {
                "from_line_fid": row.line_fid,
                "to_line_fid": None,
                "geometry": end_pt,
            }
            data += [row_dict]

    return gpd.GeoDataFrame(
        data,
        index=pd.Index(range(1, len(data) + 1), name="fid"),
        crs=lines_gdf.crs,
    )


def _select_indices(line, remaining, tolerance):
    """Find indices in remaining that are within tolerance of given line"""
    candidates = remaining.sindex.query(line.buffer(tolerance), predicate="intersects")
    nearby = remaining.iloc[[i for i in candidates if i in remaining.index]]
    close = nearby[nearby.distance(line) < tolerance]
    return close.index.to_numpy()


def connecting_secondary_lines(
    lines_gdf: gpd.GeoDataFrame,
    secondary_lines_gdf: gpd.GeoDataFrame,
    tolerance: float = 1,
) -> gpd.GeoDataFrame:
    """Select all secondary lines that are connected via other lines to lines_gdf

    Args:
        lines_gdf (gpd.GeoDataFrame): GeoDataFrame with lines
        secondary_lines_gdf (gpd.GeoDataFrame):  GeoDataFrame with lines
        tolerance (float, optional): tolerance to find line-connections from secondary_lines. Defaults to 1.

    Returns:
        gpd.GeoDataFrame: Selection of secondary_lines_gdf
    """
    remaining = secondary_lines_gdf.copy()
    if not remaining.crs.equals(lines_gdf.crs):
        remaining = remaining.to_crs(lines_gdf.crs)

    lines_gdf = lines_gdf.copy()
    lines_gdf.loc[:, "line_fid"] = lines_gdf.index

    selections = []

    for line_row in lines_gdf.itertuples():
        if remaining.empty:
            break

        to_visit = [line_row.geometry]
        collected_indices = set()

        while to_visit:
            current_geom = to_visit.pop()
            indices = _select_indices(
                line=current_geom, remaining=remaining, tolerance=tolerance
            )

            # Only consider truly new indices
            new_indices = [i for i in indices if i not in collected_indices]
            if not new_indices:
                continue

            collected_indices.update(new_indices)
            new_geoms = remaining.loc[new_indices].geometry.tolist()
            to_visit.extend(new_geoms)

        if collected_indices:
            group = remaining.loc[list(collected_indices)].copy()
            group["line_fid"] = line_row.line_fid
            selections.append(group)
            remaining = remaining.drop(index=collected_indices)

    return gpd.GeoDataFrame(pd.concat(selections, ignore_index=True), crs=lines_gdf.crs)
