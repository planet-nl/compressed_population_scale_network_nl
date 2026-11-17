# Compressed Population-scale Network Netherlands 2009-2023 in MLN format

Scripts that convert the CBS person network tables in the CBS Microdata Remote Access (RA) environment into yearly multilayer networks in the compressed MLN format of [`mlnlib`](https://github.com/planet-nl/mlnlib).

| | |
|---|---|
| **Dataset** | Compressed Population-scale Network Netherlands 2009-2023 in MLN format |
| **DOI** | [10.34894/8575OP](https://doi.org/10.34894/8575OP) |
| **Content** | One network per year: 33 layers (CBS relation types) in 5 groups, directed edges |
| **Years** | 2009–2023 |
| **Access** | CBS Microdata environment, CBS project 9629 |

This repository was formerly called `cbs_netwerk_to_mln`. It is one of three related datasets, see [Related datasets](#related-datasets).


## Overview

The pipeline:

- builds a longitudinal person universe (union of RINPERSOON across years),
- derives minimal yearly node attributes and an `active` flag,
- generates per-layer sparse adjacency matrices and a `nodes.csv.gz` per year, and
- combines the layer matrices into a single `edges.npz` per year.

The scripts are designed for the CBS RA environment. The default locations of the CBS source files (`G:\\...`) can be overridden in `files_per_year.json`, and the working folders are passed as script arguments. Paths are joined with `os.path.join`, so the scripts run both in the CBS RA (Windows) and on Linux/macOS.

> **Node files in the published dataset.** In November 2026, the `nodes.csv.gz` files of the dataset were replaced by the base node files of the [node attribute pipeline](https://github.com/planet-nl/compressed_population_scale_network_nl_detailed_node_files) (its scripts 01–02, same 9 columns, same `id`s). These define the population on **1 January** of each year from the latest GBAADRESOBJECTBUS file, so all three related datasets have identical node tables. Steps 1–2 below are kept as used for the first version, which looked up addresses on 31 December of the previous year in the year-specific GBAADRESOBJECTBUS file.

Pipeline steps and main artifacts:

1) Merge node universe (once for a range of years)
   - Script: `01_nodes_merged_nodelist.py`
   - Input: GBAPERSOONTAB files for the selected years (CSV or SAV)
   - Output: `{output_folder}/merged_node_mapping_{start}_{end}.csv.gz` with columns: `id` (int, internal ID), `label` (RINPERSOON)

2) Build yearly base node files (attributes + active flag)
   - Script: `02_nodes_base_files.py`
   - Inputs: merged mapping (from step 1), GBAPERSOONTAB (year), GBAADRESOBJECTBUS (year−1, addresses on 31 December of the previous year), GBAOVERLIJDENTAB (latest), KINDOUDERTAB
   - Output: `{output_folder}/base_start_{start}_end_{end}_year_{YYYY}.csv.gz`
     - Columns: `label, id, active, gender, birth_year, migrant_generation, number_of_parents_from_abroad, missing_mother, missing_father`

3) Generate per-layer adjacency matrices + nodes file
   - Script: `03_network_generator.py`
   - Inputs: base node file for the year (from step 2), raw layer edge files (BURENNETWERK, COLLEGANETWERK, FAMILIENETWERK, HUISGENOTENNETWERK, KLASGENOTENNETWERK)
   - Output (per year):
     - `{output_folder}/{YYYY}/nodes.csv.gz`
     - `{output_folder}/{YYYY}/*_detailed_adjacency.npz` (one per CBS network table)
     - A copy of `layers.csv`

4) Combine layer matrices
   - Script: `04_combine_layers.py`
   - Input: all `*.npz` layer matrices in `{output_folder}/{YYYY}`
   - Output: `{output_folder}/{YYYY}/edges.npz` (sum of all layer matrices; the input files are deleted)


## Data format

The output uses the **MLN (MultiLayerNetwork) format** of `mlnlib`: one directory per year containing

| File            | Content                                                                                                     |
|-----------------|-------------------------------------------------------------------------------------------------------------|
| `nodes.csv.gz`  | Node table, 9 columns: `label, id, active, gender, birth_year, migrant_generation, number_of_parents_from_abroad, missing_mother, missing_father` |
| `layers.csv`    | 33 layers: `layer_id, layer, label, group, label_long, binary`                                              |
| `edges.npz`     | Sparse N × N adjacency matrix (`uint64`), directed; each entry is the sum of the `binary` codes of its layers |

`id` is the row/column index in `edges.npz`. It is the same in every year, and N is the size of the person universe 2009–2023. `active` marks the persons who belong to the population of that year (registered at an address and alive on 1 January).

### Layer metadata

Two CSVs are provided:

- `layers.csv`: the 33 relationship layers (CBS `RELATIE` codes in `layer`), their `group` (household, school, neighbor, work, family), and integer bitmasks in `binary`
- `layers_close_extended.csv`: the same layers with family split into `close` and `extended` groups

`03_network_generator.py` writes a copy of `layers.csv` into every year folder.


## Requirements

- Python 3.10+
- `pandas` (with `pyreadstat` for SPSS files), `polars`, `scipy`, `mlnlib` (provides `RawCSVtoMLN`, and `MultiLayerNetwork` for reading the results)

The published data were produced with `mlnlib` 0.2.39; 0.3.0 should work as well.

```bash
pip install -r requirements.txt
```


## Configuration

### `files_per_year.json`

Use `files_per_year.json` to override per-year filenames, separators, and encodings if the ones given in the scripts do not work. Keys used by the scripts:

- `node_files[year]`: list with the GBAPERSOONTAB file path for that year (CSV or SAV)
- `node_sep[year]`: CSV separator for that year (when using CSV)
- `node_encoding[year]`: optional file encoding override (e.g., `latin` for 2021)
- `edge_files[year]`: list of 5 layer edge files (BURENNETWERK, COLLEGANETWERK, FAMILIENETWERK, HUISGENOTENNETWERK, KLASGENOTENNETWERK)

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


## Usage

You can either run the full pipeline with the helper shell script or invoke each step manually.

### All years with `00_run_all.sh`

Edit the variables at the top of the script to fit your environment:

- `python_path`: path to your Python interpreter (RA example uses MSYS path and `python.exe`)
- `node_data_folder`: where node mapping and base node files are read/written
- `output_folder`: where per-year results are written
- `start_year`, `end_year`: inclusive range to process

Then run:

```bash
bash 00_run_all.sh
```

What it does:

1. Creates merged node mapping for the whole range
2. Builds base node files for each year
3. Generates per-layer matrices + nodes for each year
4. Combines the layers per year into `edges.npz`

### Steps one by one

1) Merge node universe

```bash
python 01_nodes_merged_nodelist.py <start_year> <end_year> <node_data_folder>
```

2) Build base node file for a year

```bash
python 02_nodes_base_files.py <start_year> <end_year> <year> <input_folder> [output_folder]
```

3) Generate layer matrices and nodes

```bash
python 03_network_generator.py <start_year> <end_year> <year> <node_data_folder> <output_folder>
```

4) Combine layer matrices into one

```bash
python 04_combine_layers.py <output_folder>/<year>
```

Per run you should see:

- `{node_data_folder}/merged_node_mapping_{start}_{end}.csv.gz` (once per range)
- `{node_data_folder}/base_start_{start}_end_{end}_year_{YYYY}.csv.gz`
- `{output_folder}/{YYYY}/nodes.csv.gz`, `layers.csv` and `edges.npz`


## Repository structure

```
.
├── 00_run_all.sh                 # Runs all steps for a range of years
├── 01_nodes_merged_nodelist.py   # Merges RINPERSOON across years into a single id mapping
├── 02_nodes_base_files.py        # Yearly base node file with attributes and the active flag
├── 03_network_generator.py       # Per-layer npz matrices and nodes.csv.gz using mlnlib
├── 04_combine_layers.py          # Sums the layer matrices into edges.npz
├── files_per_year.json           # Per-year raw file paths, separators, encodings
├── layers.csv                    # 33-layer definition and binary encoding
├── layers_close_extended.csv     # Same, family split into close/extended
├── requirements.txt
└── README.md
```


## Related datasets

The three datasets cover 2009–2023 and share the same nodes: every person has the same `id` and `label` (RINPERSOON) in all of them, and the yearly population (`active`) is defined on 1 January. The `nodes.csv.gz` of the two network datasets holds the first 9 columns of the node attribute tables. All three are available in the CBS Microdata environment (CBS project 9629) and can be read with [`mlnlib`](https://github.com/planet-nl/mlnlib) ([PyPI](https://pypi.org/project/mlnlib/)).

| Dataset | Content | DOI | Code |
|---|---|---|---|
| Compressed Population-scale Network Netherlands 2009-2023 in MLN format | 33 layers, directed | [10.34894/8575OP](https://doi.org/10.34894/8575OP) | [compressed_population_scale_network_nl](https://github.com/planet-nl/compressed_population_scale_network_nl) |
| Simplified Compressed Population-scale Network Netherlands 2009-2023 in MLN format | 5 layers, undirected | forthcoming | [compressed_population_scale_network_nl_simplified](https://github.com/planet-nl/compressed_population_scale_network_nl_simplified) |
| Detailed Node Attributes for Compressed Population-scale Network Netherlands 2009-2023 | Yearly node attribute tables | forthcoming | [compressed_population_scale_network_nl_detailed_node_files](https://github.com/planet-nl/compressed_population_scale_network_nl_detailed_node_files) |


## How to cite

Please cite the dataset(s) you use:

> Bokányi, E., Kazmina, Y., Heemskerk, E. M., & Takes, F. W. (2025). *Compressed Population-scale Network Netherlands 2009-2023 in MLN format* [Data set]. ODISSEI Portal. https://doi.org/10.34894/8575OP

> Bokányi, E., Kazmina, Y., Heemskerk, E. M., & Takes, F. W. (2026). *Simplified Compressed Population-scale Network Netherlands 2009-2023 in MLN format* [Data set]. ODISSEI Portal. DOI forthcoming.

> Bokányi, E., Kazmina, Y., Heemskerk, E. M., & Takes, F. W. (2026). *Detailed Node Attributes for Compressed Population-scale Network Netherlands 2009-2023* [Data set]. ODISSEI Portal. DOI forthcoming.

and the paper describing the network:

> Bokányi, E., Heemskerk, E. M., & Takes, F. W. (2023). The anatomy of a population-scale social network. *Scientific Reports*, 13, 9209. https://doi.org/10.1038/s41598-023-36324-9


## Authors and contact

Eszter Bokányi (Leiden University), Yuliia Kazmina (University of Amsterdam), Eelke M. Heemskerk (University of Amsterdam), Frank W. Takes (Leiden University), and the PLANET-NL team (https://planetnl.org).

For questions, contact the PLANET-NL team: info@planetnl.org
