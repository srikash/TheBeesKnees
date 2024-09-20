#!/bin/bash

# Help function
function usage {
    echo "Usage: $0 [-i input_file] [-a additional_file] [-o output_folder] [-h]"
    echo "  -i, --input            Input NIfTI file (.nii.gz required)"
    echo "  -a, --additional       Additional NIfTI file to be cropped the same way"
    echo "  -o, --output-folder    Specify the output folder for processed files"
    echo "  -h, --help             Display this help message and exit"
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
        -a|--additional) additional_file="$2"; shift ;;
        -o|--output-folder) output_folder="$2"; shift ;;
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

# Check if the additional file is provided
if [ -z "$additional_file" ]; then
    echo "Error: Additional file is required"
    usage
fi

# Check if the input files have the .nii.gz extension
if [[ "$input_file" != *.nii.gz ]]; then
    echo "Error: Input file must have a .nii.gz extension"
    usage
fi

if [[ "$additional_file" != *.nii.gz ]]; then
    echo "Error: Additional file must have a .nii.gz extension"
    usage
fi

# Set output folder to current directory if not specified
if [ -z "$output_folder" ]; then
    output_folder="."
fi

# Extract the base name (without extension) for the output files
base_name=$(basename "$input_file" .nii.gz)
additional_base_name=$(basename "$additional_file" .nii.gz)

# Create the output folder if it doesn't exist
mkdir -p "$output_folder"

# Step 1: Skull stripping with 3dSkullStrip for the main input file
3dSkullStrip \
    -overwrite \
    -push_to_edge \
    -shrink_fac 0.4 \
    -orig_vol \
    -input "$input_file" \
    -prefix "${output_folder}/${base_name}_SS.nii.gz"

# Step 2: Autoboxing with 3dAutobox to find extent for the main input file
3dAutobox \
    -overwrite \
    -extent_ijkord_to_file "${output_folder}/${base_name}_abox.ijkord" \
    -npad 14 \
    -input "${output_folder}/${base_name}_SS.nii.gz"

# Clean up intermediate skull-stripped file
rm "${output_folder}/${base_name}_SS.nii.gz"

# Extract x, y, z coordinates from the autobox ijkord file
xords=($(sed -n 1p "${output_folder}/${base_name}_abox.ijkord"))
yords=($(sed -n 2p "${output_folder}/${base_name}_abox.ijkord"))
zords=($(sed -n 3p "${output_folder}/${base_name}_abox.ijkord"))

# Step 3: Cropping the image using the extent for the main input file
3dcalc \
    -overwrite \
    -prefix "${output_folder}/${base_name}_abox_init.nii.gz" \
    -expr "a*within(${xords[0]},${xords[1]},${xords[2]})*within(${yords[0]},${yords[1]},${yords[2]})*within(${zords[0]},${zords[1]},${zords[2]})" \
    -a "$input_file"

# Step 4: Final autoboxing to clean up the main input image
3dAutobox \
    -overwrite \
    -prefix "${output_folder}/${base_name}_abox_final.nii.gz" \
    -input "${output_folder}/${base_name}_abox_init.nii.gz"

# Step 5: Cropping the additional input file using the same coordinates
3dcalc \
    -overwrite \
    -prefix "${output_folder}/${additional_base_name}_abox_init.nii.gz" \
    -expr "a*within(${xords[0]},${xords[1]},${xords[2]})*within(${yords[0]},${yords[1]},${yords[2]})*within(${zords[0]},${zords[1]},${zords[2]})" \
    -a "$additional_file"

# Step 6: Final autoboxing for the additional input file
3dAutobox \
    -overwrite \
    -prefix "${output_folder}/${additional_base_name}_abox_final.nii.gz" \
    -input "${output_folder}/${additional_base_name}_abox_init.nii.gz"

# Clean up the autobox ijkord file
# rm "${output_folder}/${base_name}_abox.ijkord"

# Print completion message
echo "Processing complete."
echo "Main input output saved to ${output_folder}/${base_name}_abox_final.nii.gz."
echo "Additional input output saved to ${output_folder}/${additional_base_name}_abox_final.nii.gz."
