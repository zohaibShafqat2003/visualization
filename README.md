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
- Place the GeoPackage files at `data/segments_N5.gpkg`, `data/segments_N55_manual_final.gpkg`, and `data/counts_N5_N55.gpkg`.
- The Streamlit entrypoint is `app.py`.

## Road data preparation

The app reads prepared condition GeoPackages directly from `data/`:

```text
data/
  segments_N5.gpkg
  segments_N55_manual_final.gpkg
  counts_N5_N55.gpkg
  validation_report.json
  raw/
    N5/        # Original directional GeoPackages and Excel references
    N55/       # Directional CSVs and preserved geometry_N55.gpkg
    archives/  # Original RAR archive
  backup/      # Original road GeoPackages; never overwritten by regeneration
```

N55 uses `data/segments_N55_manual_final.gpkg` directly.
The preparation script below produces the legacy `segments_N55.gpkg`; it does
not regenerate or replace the active N55 file.

From the repository root, with requirements installed, run:

```bash
python scripts/prepare_data.py
```

On the first run, the script copies and verifies the sources from `New folder`
and backs up both existing road GeoPackages. `New folder` is left intact.
Subsequent runs read `data/raw/`; existing source copies must match any files
still present in `New folder`. To intentionally update an input, update both
copies, or archive the old `New folder` outside this location first.

Each road output contains `km`, `status_north`, `status_south`, and LineString
geometry in EPSG:4326, sorted by kilometer. N5 uses `data/raw/N5/n5_line.gpkg`
as its segment geometry, matching its `seg_id` directly to condition-source `km`.
Northbound and southbound labels still come from `sf_north1.gpkg` and
`sf_south1.gpkg`. All geometry segments are retained; segments 1770 and 1771
have no supplied conditions and display as No Data. N55 retains the original network
geometry and joins CSV conditions by kilometer. Missing statuses remain missing.
Excel calculations are retained for reference and are not imported. Old numerical
RSL and roughness fields remain available in the backups.

The script rejects missing columns, conflicting duplicate kilometer keys, and
unexpected invalid geometry. Exact duplicate rows are collapsed. Both exports
are checked against their input frames before replacing the live files.
`validation_report.json` lists missing statuses, directional coverage differences,
and CSV kilometer keys with no matching geometry. Ten known, pre-existing N55
zero-length lines are retained and explicitly reported; no geometry is invented.
Traffic counts are unchanged. Refresh the app after regeneration (restart it if
cached data was already loaded).
