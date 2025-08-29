from pathlib import Path

import streamlit as st

from wbd_tools.config.config import load_cfg, save_cfg

cfg = load_cfg()

st.title("Config editor")
cfg.project_name = st.text_input("project_name", cfg.project_name)
cfg.debug = st.checkbox("debug", cfg.debug)
cfg.retries = st.number_input("retries", cfg.retries, step=1)
cfg.threshold = st.number_input("threshold", cfg.threshold)
cfg.mode = st.selectbox("mode", ["fast", "accurate"], index=["fast", "accurate"].index(cfg.mode))
tags_csv = st.text_input("tags (csv)", ",".join(cfg.tags))
cfg.tags = [t for t in tags_csv.split(",") if t.strip()]
cfg.output_dir = Path(st.text_input("output_dir", str(cfg.output_dir)))
cfg.api_key = st.text_input("api_key", cfg.api_key or "", type="password") or None

if st.button("Save"):
    save_cfg(cfg)
    st.success("Saved to config.toml")
