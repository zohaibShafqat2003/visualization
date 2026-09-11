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
- The map displays only N5 from Multan to Peshawar. Endpoints use the N5
  segment nearest Multan (approximately km 929), ending at km 1706 before
  the terminal Peshawar PDA section. Km 1707–1718 is excluded in both directions.
  Conditions, distance markers, cities, and traffic stations follow this section.
- N5 condition data in both directions is overwritten with **iRAP** (gray)
  from Lahore toward Gujranwala (RD km 1281–1335), **LDA** (orange) at RD km 1260–1280
  and **AIB** (gray) at RD km 1566–1605 and 1675–1706,
  including both endpoints. These categories appear in the map's Road condition
  key. Rules are stored in `data/n5_condition_overrides.json` and reapplied by
  data preparation. The original N5 file is preserved in
  `data/backup/segments_N5_before_project_conditions.gpkg`.
  **Cantt/RDA** uses a dotted gray line (and matching map-key symbol) at RD km 1539–1565 in both directions,
  matching the whole N5 segments between the supplied T-Chowk and 26 Number
  screenshots. AIB continues from km 1566.
- N5 also loads `data/traffic_counts_rauf_10.09.26.csv` when **Traffic count
  stations** is enabled. These 13 records are labeled **ETTM Toll Plaza** and
  use dark diamond markers with a white toll-gate symbol; other ADT stations use orange circles.
  Qutbal (ETTM) is excluded from the map; its source record is retained.
  ADT uses the second `Total` column (the supplied daily counts), with the
  original vehicle categories retained. Approximate coordinates are noted in
  popups; collocated Chenab NB/SB records share a popup with separate counts.

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
