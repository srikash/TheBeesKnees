#!/bin/bash

# Script to apply robust FOV adjustment and resample an MP2RAGE UNI image based on INV2

# Function to display script usage
display_usage() {
  echo "Usage: $0 -i <INV2_INPUT> -u <UNI_INPUT>"
  echo "Options:"
  echo "  -i   Path to the MP2RAGE INV2 image (e.g., MP2RAGE_INV2.nii.gz)"
  echo "  -u   Path to the MP2RAGE UNI image (e.g., MP2RAGE_UNI.nii.gz)"
  exit 1
}

# Parse options
while getopts ":i:u:" opt; do
  case $opt in
    i) inv2_input="$OPTARG" ;;
    u) uni_input="$OPTARG" ;;
    \?) echo "Invalid option: -$OPTARG" >&2; display_usage ;;
  esac
done

# Check for required arguments
if [ -z "$inv2_input" ] || [ -z "$uni_input" ]; then
  echo "Both -i and -u flags are required."
  display_usage
fi

# Remove file extension and path from input filenames
inv2_input_prefix=$(basename "${inv2_input%.*}")
uni_input_prefix=$(basename "${uni_input%.*}")

# Output directory
output_dir="output"
mkdir -p "$output_dir"

# Apply robust FOV adjustment
robustfov \
    -i "$inv2_input" \
    -r "$output_dir/${inv2_input_prefix}_full2fov.nii.gz" \
    -m "$output_dir/${inv2_input_prefix}_fov2full.mat"

# Invert transformation matrix
convert_xfm \
    -omat "$output_dir/${inv2_input_prefix}_full2fov.mat" \
    -inverse "$output_dir/${inv2_input_prefix}_fov2full.mat"

# Resample UNI image
flirt \
    -applyxfm \
    -init "$output_dir/${inv2_input_prefix}_full2fov.mat" \
    -interp sinc \
    -ref "$output_dir/${inv2_input_prefix}_full2fov.nii.gz" \
    -in "$uni_input" \
    -out "$output_dir/${uni_input_prefix}_full2fov.nii.gz"

echo "Processing complete. Output files are in the '$output_dir' directory."
