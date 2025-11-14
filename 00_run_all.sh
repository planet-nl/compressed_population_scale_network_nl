#!/bin/bash

# Author: Eszter Bokanyi, e.bokanyi@liacs.leidenuniv.nl, 2025.11.14.

python_path="/c/mambaforge/envs/9629"
node_data_folder="/h/shared_data/nodelists"
output_folder="/h/shared_data"
start_year=2009
end_year=2023
to_process=`seq $start_year $end_year`
echo -e "Years to process:\n $to_process"

# create merged nodelist between start_year and end_year: unioning all RINPERSOON ids occuring in GBAPERSOONTAB
echo -e "===========================================\n Creating merged nodelist... \n===========================================\n"
$python_path/python.exe 01_nodes_merged_nodelist.py $start_year $end_year $node_data_folder
echo -e "===========================================\n Done. \n===========================================\n"

# create base nodelists for each year
echo -e "===========================================\n Creating base nodelists... \n===========================================\n"
for year in $to_process
do
    echo -e "============= YEAR $year =================="
    $python_path/python.exe 02_nodes_base_files.py $start_year $end_year $year $node_data_folder
done
echo -e "===========================================\n Done. \n===========================================\n"

# layerwise adjacency matrices for each year
echo -e "===========================================\n Creating layerwise matrices... \n===========================================\n"
for year in $to_process
do 
    echo -e "============= YEAR $year =================="
    $python_path/python.exe 03_network_generator.py $start_year $end_year $year $node_data_folder $output_folder
done
echo -e "===========================================\n Done. \n===========================================\n"

# combining layerwise adjacency matrices
echo -e "===========================================\n Combining layerwise matrices... \n===========================================\n"
for year in `seq $start_year $end_year`
do
    echo -e "============= YEAR $year =================="
    echo "Combining in "$output_folder"\\"$year"..."
    $python_path/python.exe 04_combine_layers.py $output_folder"\\"$year
done
echo -e "===========================================\n Done. \n===========================================\n"