import geopandas as gpd
from pathlib import Path
import json

# global constants
JSON_DIR = Path(__file__).parent / "json"
LAYER_TO_FILE_MAP = {"LEGGER_VASTGESTELD_WATERLOOP_CATEGORIE_A": "dwarsprofiel.json"}

def init_gdb(damo_gdb:Path, layer_to_file_map: dict = LAYER_TO_FILE_MAP) -> Path:
    """Checks if DAMO GeoDataBase exists and populates JSON dir

    Returns:
       Path: Path to json dir
    """
    # init layers, will return FileNotFound when damo_gdb does not exist
    layers = gpd.list_layers(damo_gdb)

    # init json-dir. Make if not existing
    json_dst_dir = damo_gdb.parent.joinpath("json")
    if not json_dst_dir.exists():
        json_dst_dir.mkdir()
    
    # update and write filename and layer of jsons
    for row in layers.itertuples():
        layer = row.name
        if layer in LAYER_TO_FILE_MAP.keys():
            json_src_file = JSON_DIR.joinpath(LAYER_TO_FILE_MAP[layer])
            json_dst_file = json_dst_dir.joinpath(LAYER_TO_FILE_MAP[layer])
        else:
            json_src_file = JSON_DIR.joinpath(f"{row.name}.json")
            json_dst_file = json_dst_dir.joinpath(f"{row.name}.json")

        file_updated = False
        try:
            if not json_dst_file.exists():
                layer_specs = json.loads(json_src_file.read_text())
            else:
                layer_specs = json.loads(json_dst_file.read_text())
        except FileNotFoundError:
            continue

        layer_specs["source"]["path"] = damo_gdb.as_posix()
        layer_specs["source"]["layer"] = layer

        json_dst_file.write_text(json.dumps(layer_specs, indent=1))
    
    return json_dst_dir
