# Road Condition Map (Visualization)

This repository contains a Streamlit app that visualizes road remaining-service-life and traffic counts using GeoPackage data.

Quick start (local):

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Notes:
- Place the GeoPackage files in the `data/` folder (already present in this repo): `segments_N5.gpkg`, `segments_N55.gpkg`, `counts_N5_N55.gpkg`.
- The Streamlit entrypoint is `app.py` which runs the original script.
