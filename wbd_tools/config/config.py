# %%
import json
from pathlib import Path
from typing import List, Literal, Optional

import tomli
import tomli_w
from pydantic import BaseModel


class ModuleCfg(BaseModel):
    enabled: bool = True
    resolution: Optional[int] = None
    scheme: Optional[Literal["fast", "accurate"]] = None


class Cfg(BaseModel):
    project_name: str = "Demo"
    debug: bool = False
    retries: int = 3
    threshold: float = 0.8
    mode: Literal["fast", "accurate"] = "fast"
    tags: List[str] = []
    output_dir: Path = Path("./output")
    api_key: Optional[str] = None


def load_cfg(p="config.toml"):
    try:
        with open(p, "rb") as f:
            return Config.model_validate(tomli.load(f))
    except FileNotFoundError:
        return Config()


def save_cfg(cfg: Config, p="config.toml"):
    with open(p, "wb") as f:
        tomli_w.dump(json.loads(cfg.model_dump_json(exclude_none=True)), f)
