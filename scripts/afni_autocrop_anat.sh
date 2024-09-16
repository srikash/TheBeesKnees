#!/bin/bash

# Help function
function usage {
    echo "Usage: $0 [-i input_file] [-h]"
    echo "  -i, --input     Input NIfTI file (.nii.gz required)"
    echo "  -h, --help      Display this help message and exit"
    exit 1
}

# Check for input arguments
if [ $# -eq 0 ]; then
    usage
fi

# Parse input arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -i|--input) input_file="$2"; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown parameter passed: $1"; usage ;;
    esac
    shift
done

# Check if input file is provided
if [ -z "$input_file" ]; then
    echo "Error: Input file is required"
    usage
fi

# Check if input file has the .nii.gz extension
if [[ "$input_file" != *.nii.gz ]]; then
    echo "Error: Input file must have a .nii.gz extension"
    usage
fi

# Extract the base name (without extension) for the output files
base_name=$(basename "$input_file" .nii.gz)

# Step 1: Skull stripping with 3dSkullStrip
3dSkullStrip \
    -overwrite \
    -push_to_edge \
    -shrink_fac 0.4 \
    -orig_vol \
    -input "$input_file" \
    -prefix "${base_name}_SS.nii.gz"

# Step 2: Autoboxing with 3dAutobox to find extent
3dAutobox \
    -overwrite \
    -extent_ijkord_to_file "${base_name}_abox.ijkord" \
    -npad 14 \
    -input "${base_name}_SS.nii.gz"

rm "${base_name}_SS.nii.gz"

# Extract x, y, z coordinates from the autobox ijkord file
xords=($(sed -n 1p "${base_name}_abox.ijkord"))
yords=($(sed -n 2p "${base_name}_abox.ijkord"))
zords=($(sed -n 3p "${base_name}_abox.ijkord"))

# Step 3: Cropping the image using the extent from 3dcalc
3dcalc \
    -overwrite \
    -prefix "${base_name}_abox.nii.gz" \
    -expr "a*within(${xords[0]},${xords[1]},${xords[2]})*within(${yords[0]},${yords[1]},${yords[2]})*within(${zords[0]},${zords[1]},${zords[2]})" \
    -a "$input_file"

# Step 4: Final autoboxing to clean up the image
3dAutobox \
    -overwrite \
    -prefix "${base_name}_abox.nii.gz" \
    -input "${base_name}_abox.nii.gz"

# Print completion message
echo "Processing complete. Output saved to ${base_name}_SS.nii.gz and ${base_name}_abox.nii.gz"