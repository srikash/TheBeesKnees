#! /bin/bash

# Steps to install
# Pre-requisites
# conda create -n bgrem python=3.9
# $CONDA_PREFIX/bin/pip3 install --upgrade pip
# $CONDA_PREFIX/bin/pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# Main program
# Uses repo from : https://github.com/nadermx/backgroundremover.git
# $CONDA_PREFIX/bin/pip3 install backgroundremover

echo "Activate Environment BGREM"
conda activate bgrem

input_file=$1
output_prefix=${$input_file%.*}

echo "Removing background"
backgroundremover \
    -i "$input_file" \
    -a \
    -ae 15 \
    -o "${output_prefix}_bgrem.jpg"

echo "Adding white background"
convert \
"${output_prefix}_bgrem.jpg" \
-background 'white' \
-flatten \
"${output_prefix}_bgwhite.jpg"