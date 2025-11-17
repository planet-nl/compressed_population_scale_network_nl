# CBS netwerk to `mlnlib` format

Convert CBS person-network raw tables (RA environment) into compressed MLN adjacency matrices and node files to be loaded by `mlnlib`.

This repo contains a small pipeline that:

- builds a longitudinal person universe (union of RINPERSOON across years),
- derives minimal yearly node attributes and “active on Jan 1” flags,
- generates per-layer sparse adjacency matrices and a consolidated `nodes.csv.gz` per year, and
- combines layerwise matrices into a single `edges.npz`.

The scripts are designed for the CBS RA environment and reference shared drives like `G:\\` and `H:\\`. When those defaults are not available, paths can be overridden via `files_per_year.json` and by passing folders as script arguments.


## Overview

Pipeline steps and main artifacts:

1) Merge node universe (once for a range of years)
   - Script: `01_nodes_merged_nodelist.py`
   - Input: GBAPERSOONTAB files for the selected years (CSV or SAV)
   - Output: `{output_folder}/merged_node_mapping_{start}_{end}.csv.gz` with columns: `id` (int, internal ID), `label` (RINPERSOON)

2) Build yearly base node files (attributes + active flag)
   - Script: `02_nodes_base_files.py`
   - Inputs: merged mapping (from step 1), GBAPERSOONTAB (year), GBAADRESOBJECTBUS (year-1), GBAOVERLIJDENTAB (latest), KINDOUDERTAB
   - Output: `{output_folder}/base_start_{start}_end_{end}_year_{YYYY}.csv.gz`
     - Columns: `label, id, active, gender, birth_year, migrant_generation, number_of_parents_from_abroad, missing_mother, missing_father`

3) Generate per-layer adjacency matrices + nodes file
   - Script: `03_network_generator.py`
   - Inputs: base node file for the year (from step 2), raw layer edge files (BURENNETWERK, COLLEGANETWERK, FAMILIENETWERK, HUISGENOTENNETWERK, KLASGENOTENNETWERK)
   - Output (per year):
     - `{output_folder}/{YYYY}/nodes.csv.gz`
     - `{output_folder}/{YYYY}/*_detailed_adjacency.npz` (one per layer)
     - A copy of `layers.csv` is written once

4) Combine layer matrices (optional)
   - Script: `04_combine_layers.py`
  - Input: all `*.npz` layer matrices in `{output_folder}/{YYYY}`
  - Output: `{output_folder}/{YYYY}/edges.npz` (sum of all layer matrices)


## Prerequisites

- Python 3.10+ recommended
- Packages:
  - `pandas` (incl. SPSS support via `pyreadstat`)
  - `polars`
  - `scipy`
  - `mlnlib` (provides `RawCSVtoMLN` and them `MultiLayerNetwork` for reading the results)

Install the typical open-source deps with pip (example):

```
pip install -r requirements.txt
```

## Data locations and configuration

Use`files_per_year.json` to override per-year filenames, separators, and encodings if the ones given in the scripts do not work.

### `files_per_year.json`

Keys used by the scripts:

- `node_files[year]`: list with the GBAPERSOONTAB file path for that year (CSV or SAV)
- `node_sep[year]`: CSV separator for that year (when using CSV)
- `node_encoding[year]`: optional file encoding override (e.g., `latin` for 2021)
- `edge_files[year]`: list of 5 layer edge files (Burennetwork, Collega, Familie, Huisgenoten, Klasgenoten)

Example (excerpt):

```
{
  "node_files": {
    "2023": ["G:\\\\Bevolking\\\\GBAPERSOONTAB\\\\2023\\\\geconverteerde data\\\\GBAPERSOON2023TABV1.csv"]
  },
  "node_sep": {"2023": ";"},
  "node_encoding": {"2021": "latin"},
  "edge_files": {
    "2023": [
      "G:\\\\Bevolking\\\\BURENNETWERKTAB\\\\BURENNETWERK2023TABV1.csv",
      "... (four more layer files) ..."
    ]
  }
}
```

### Layer metadata

Two CSVs are provided:

- `layers.csv`: full list of relationship layers, with integer bitmasks in `binary`
- `layers_close_extended.csv`: same layers grouped into `close` vs `extended` family categories

These are used for downstream labeling/aggregation. In `03_network_generator.py` a copy of `layers.csv` is written once per run.


## Usage

You can either run the full pipeline with the helper shell script or invoke each step manually.

### A) Run all years with `00_run_all.sh`

Edit the variables at the top of the script to fit your environment:

- `python_path`: path to your Python interpreter (RA example uses MSYS path and `python.exe`)
- `node_data_folder`: where node mapping and base node files are read/written
- `output_folder`: where per-year results are written
- `start_year`, `end_year`: inclusive range to process

Then run:

```
bash 00_run_all.sh
```

What it does:

1. Creates merged node mapping for the whole range
2. Builds base node files for each year
3. Generates per-layer matrices + nodes for each year
4. Combines the layers per year into `edges.npz`

### B) Run steps manually

1) Merge node universe

```
python 01_nodes_merged_nodelist.py <start_year> <end_year> <node_data_folder>
```

2) Build base node file for a year

```
python 02_nodes_base_files.py <start_year> <end_year> <year> <input_folder> [output_folder]
```

3) Generate layer matrices and nodes

```
python 03_network_generator.py <start_year> <end_year> <year> <node_data_folder> <output_folder>
```

4) Combine layer matrices into one

```
python 04_combine_layers.py <output_folder>/<year>
```


## Outputs

Per run/year you should see:

- `{node_data_folder}/merged_node_mapping_{start}_{end}.csv.gz` (once per range)
- `{node_data_folder}/base_start_{start}_end_{end}_year_{YYYY}.csv.gz`
- `{output_folder}/{YYYY}/nodes.csv.gz`
- `{output_folder}/{YYYY}/*_detailed_adjacency.npz` (one per input layer)
- `{output_folder}/{YYYY}/edges.npz` after combining


## Known caveats and notes

- Environment and paths:
  - The code base mixes Linux bash and Windows-style paths as used in the RA (e.g., `G:\\...`, `H:\\...`). If running outside RA, adjust arguments and/or `files_per_year.json`.
  - The helper script uses `python.exe`. Replace with `python` if your interpreter is POSIX-only.

- Custom files used as sources (`files_per_year.json`). Two files had to be generated manually by SPSS export as they were not available in the RA shared drives, and they were too large to load as SPSS files. Note that csv availability may change in the RA environment over time.
  - Line 56: H:\\shared_data\\misc\\BURENNETWERK2009TABV1.csv
  - Line 72: H:\\shared_data\\misc\\COLLEGANETWERK2023TABV1.csv


## Troubleshooting

- Missing files: Point per-year paths to existing files in `files_per_year.json`.
- Separator/encoding issues: Adjust `node_sep` and `node_encoding` per year in `files_per_year.json`.
- Memory/scale: Use the `chunksize` parameter in `03_network_generator.py` (already set to `1e8`, but unfortunately, only works in pandas mode) and ensure sufficient disk space for `npz` outputs.


## Repository structure (key files)

- `00_run_all.sh` – Orchestrates all steps for a year range
- `01_nodes_merged_nodelist.py` – Merges RINPERSOON across years into a single mapping
- `02_nodes_base_files.py` – Builds yearly base node file with attributes and “active” flag
- `03_network_generator.py` – Creates per-layer `npz` matrices and `nodes.csv.gz` using `mlnlib`
- `04_combine_layers.py` – Sums layer matrices into `edges.npz`
- `files_per_year.json` – Per-year raw file paths, separators, encodings
- `layers.csv`, `layers_close_extended.csv` – Layer metadata used for labeling/grouping


## Citation / Contact

Author and maintainer: Eszter Bokanyi, e.bokanyi@liacs.leidenuniv.nl, PLANET-NL project.
