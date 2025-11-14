"""
Author: Eszter Bokanyi, e.bokanyi@liacs.leidenuniv.nl, 2025.11.14.

This code reads CBS raw files and creates an MLN data object per layer for a given year.

Usage (example for 2023):
    /c/mambaforge/envs/9629/python.exe 03_network_generator.py 2009 2023 2023 <node_data_folder> <output_folder>

Parameters:
    start_year
    end_year
    actual_year
    node_data_folder
    output_folder

Bash loop:
    for year in `seq 2009 2023`; do
        echo "======   YEAR $year   ============================";
        /c/mambaforge/envs/9629/python.exe 03_network_generator.py 2009 2023 $year <node_data_folder> <output_folder>;
    done
"""

import pandas as pd
import sys
from mlnlib.preparation import RawCSVtoMLN
import json
import os
from time import time
from copy import deepcopy

# year is first argument 
start_year = int(sys.argv[1])
end_year = int(sys.argv[2])
year = int(sys.argv[3])
node_data_folder = sys.argv[4]
output_folder = sys.argv[5]

print(f"Processing network for year {year}.")

# getting file names and col separators for different years
files_per_year = json.load(open("files_per_year.json"))

# ===============================================================

# node file names to include if they exist
node_files = [
    f"{node_data_folder}\\base_start_{start_year}_end_{end_year}_year_{year}.csv.gz",
    # f"{node_data_folder}\\location_{year}.csv.gz",
    # f"{node_data_folder}\\nodelists\\income_{year}.csv.gz"
]

# checking whether default node file (first from the above list) exists
# if not, read file names from JSON pointing to the GBAPERSOONTAB
node_files_checked = []
if not os.path.exists(node_files[0]):
    node_files_checked.append(files_per_year["node_files"][str(year)])
else:
    node_files_checked.append(node_files[0])

# checking the existence of all other input node files
for nf in node_files[1:]:
    if os.path.exists(nf):
        node_files_checked.append(nf)
# new node file list
node_files = node_files_checked

print("Concatenating the following node files into nodes.csv.gz:")
print("\n".join(node_files))

# which columns to use from the above files and how to rename them
# only columns listed here will be kept
# therefore, even if there has to be no renaming, they have to be included into this dict
node_colmap = {
    "RINPERSOON" : "label",
    "label" : "label",
    "id" : "id",
    "gender" : "gender",
    "migrant_generation" : "migrant_generation",
    "birth_year" : "birth_year",
    "active" : "active",
    "missing_mother" : "missing_mother",
    "missing_father" : "missing_father",
    "number_of_parents_from_abroad" : "number_of_parents_from_abroad",
    "household_income": "household_income",
    "household_income_percentile":"household_income_percentile",
    "individual_income_gross":"individual_income_gross",
    "individual_income_percentile":"individual_income_percentile",
    "socioeconomic_situation" : "socioeconomic_situation",
    "household_change_year" : "household_change_year",
    "gemeente_code" : "gemeente_code",
    "wijk_code" : "wijk_code",
    "buurt_code" : "buurt_code"
}

# node configuration script for MLN preparation script
node_conf = dict(
    input_folder_prefix = "",
    files = node_files,
    main_file = 0,
    colmap = node_colmap,
    sep = ",",
    geo_shp_folder = "",
    output = f"{output_folder}\\{year}\\nodes.csv.gz",
    add_geo = False
)

# ==========================================================================

# default edge file names
edge_files = [
    f"G:\\Bevolking\\BURENNETWERKTAB\\BURENNETWERK{year}TABV1.csv",
    f"G:\\Bevolking\\COLLEGANETWERKTAB\\COLLEGANETWERK{year}TABV2.csv",
    f"G:\\Bevolking\\FAMILIENETWERKTAB\\FAMILIENETWERK{year}TABV1.csv",
    f"G:\\Bevolking\\HUISGENOTENNETWERKTAB\\HUISGENOTENNETWERK{year}TABV1.csv",
    f"G:\\Bevolking\\KLASGENOTENNETWERKTAB\\KLASGENOTENNETWERK{year}TABV1.csv"
]

# checking whether default exists
# if any of them do not exist, read file names specified in JSON
edge_files_exist = True
for ef in edge_files:
    if not os.path.exists(ef):
        edge_files_exist = False
        print(f"{ef} was not found!")
if not edge_files_exist:
    edge_files = files_per_year["edge_files"][str(year)]

print("Adding layers from the following edge files:")
print("\n".join(edge_files))

# how to rename columns from the given edge files
edge_colmap = dict(
    RINPERSOON = "source",
    RINPERSOONRELATIE = "target",
    RELATIE = "layer"
)

# edge reading configuration dict for MLN preparation script
# this is a base dict which will be modified per year / layer / separator etc.
edge_conf_base = dict(
    input_folder_prefix = "",
    files = [],
    colmap = edge_colmap,
    sep = ";", #default separator
    output = f"{output_folder}\\{year}\\",
    nrows=None #how many rows to read from files, can be used for testing
)

#========================================================

# layer configuration dict
layer_conf = dict(
    input_folder_prefix = "",
    raw_file = "layers.csv",
    file = "",
    output = f"{output_folder}\\{year}\\layers.csv",
    symmetrize = [],
    symmetrize_all = False,
    raw_sep=",",
    sep = ",",
    colors = "",
    colmap = ""
)

# =======================================================

# how to rename above edge files
# TODO generalize
adjacency_names = [
    "neighbor_detailed_adjacency.npz",
    "work_detailed_adjacency.npz",
    "family_detailed_adjacency.npz",
    "household_detailed_adjacency.npz",
    "school_detailed_adjacency.npz"
]


# if there's no folder for the year's network, create it
p = os.path.join(f"{output_folder}",str(year))
if not os.path.exists(p):
    os.mkdir(p)
    print(f"Directory {p} created.")

# helper variable to only write node dataframe once
first = True

# create binary encoded adjacency matrices per edge file (in the CBS case, per layer)
for ef,adj_name in zip(edge_files,adjacency_names):
    print(f"Creating layer from {ef} into {adj_name}...")
    edge_conf = deepcopy(edge_conf_base)
    edge_conf["output"] += adj_name
    # only include one edge file into the configuration
    edge_conf["files"] = [ef]
    # the following 4 files have different separators (1 from 2021 and 3 from 2023)
    if ef in [
        "G:\\Bevolking\\HUISGENOTENNETWERKTAB\\HUISGENOTENNETWERK2021TABV1.csv",
        "G:\\Bevolking\\BURENNETWERKTAB\\BURENNETWERK2023TABV1.csv",
        "G:\\Bevolking\\FAMILIENETWERKTAB\\FAMILIENETWERK2023TABV1.csv",
        "G:\\Bevolking\\HUISGENOTENNETWERKTAB\\HUISGENOTENNETWERK2023TABV1.csv"
    ]:
        edge_conf["sep"] = ","

    # creating full configuration dict for MLN preparation script
    config = dict(
        node_conf = node_conf,
        edge_conf = edge_conf,
        layer_conf = layer_conf,
        grouped = False,
        use_polars = True,
        chunksize=1e8
    )
    print(f"Current config:")
    print(json.dumps(config,indent=4))

    r = RawCSVtoMLN(**config)

    r.init_layers()
    r.init_nodes()
    r.init_edges()
    r.read_all_edges()
    if first:
        r.save_layer_df(r.layer_conf["output"])
        r.save_node_df(r.node_conf["output"])
    first = False
    r.save_edge_npz(r.edge_conf["output"])
