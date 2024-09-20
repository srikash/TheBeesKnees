#!/bin/bash

# Help function
function usage() {
    echo "Usage: $0 [-i uniclean_file] [-a inv1_file] [-b inv2_file] [-c uni_file] [-d t1_file] [-o output_folder] [-h]"
    echo "  -i, --uniclean            Input NIfTI file (.nii.gz required)"
    echo "  -a, --inv1                (Optional) First additional NIfTI file"
    echo "  -b, --inv2                (Optional) Second additional NIfTI file"
    echo "  -c, --uni                 (Optional) Another NIfTI file"
    echo "  -d, --t1map               (Optional) Another NIfTI file"
    echo "  -o, --output              (Optional) Specify the output folder for processed files. Defaults to current directory."
    echo "  -h, --help                Display this help message and exit"
    exit 1
}

# Check for input arguments
if [ $# -eq 0 ]; then
    usage
fi

# Parse input arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
    -i | --uniclean)
        uniclean_file="$2"
        shift
        ;;
    -a | --inv1)
        inv1_file="$2"
        shift
        ;;
    -b | --inv2)
        inv2_file="$2"
        shift
        ;;
    -c | --uni)
        uni_file="$2"
        shift
        ;;
    -d | --t1map)
        t1_file="$2"
        shift
        ;;
    -o | --output)
        output_folder="$2"
        shift
        ;;
    -h | --help) usage ;;
    *)
        echo "Unknown parameter passed: $1"
        usage
        ;;
    esac
    shift
done

# Check if the required input file is provided
if [ -z "$uniclean_file" ] || [ ! -f "$uniclean_file" ]; then
    echo "Error: Uniclean file (-i) is required and must exist."
    usage
fi

if [[ -n "$inv1_file" && "$inv1_file" != *.nii.gz ]]; then
    echo "Error: inv1 file must have a .nii.gz extension"
    usage
fi

if [[ -n "$inv2_file" && "$inv2_file" != *.nii.gz ]]; then
    echo "Error: inv2 file must have a .nii.gz extension"
    usage
fi

if [[ -n "$uni_file" && "$uni_file" != *.nii.gz ]]; then
    echo "Error: Uni file must have a .nii.gz extension"
    usage
fi

if [[ -n "$t1_file" && "$t1_file" != *.nii.gz ]]; then
    echo "Error: T1 file must have a .nii.gz extension"
    usage
fi

# Set output folder to current directory if not specified
if [ -z "$output_folder" ]; then
    output_folder="."
fi

# Check if output folder is writable
if [ ! -w "$output_folder" ]; then
    echo "Error: Output folder is not writable: $output_folder"
    exit 1
fi

# Create the output folder if it doesn't exist
mkdir -p "$output_folder"

# Skull stripping for the uniclean file
base_name=$(basename "$uniclean_file" .nii.gz)
3dSkullStrip \
    -overwrite \
    -push_to_edge \
    -shrink_fac 0.4 \
    -orig_vol \
    -input "$uniclean_file" \
    -prefix "${output_folder}/tmp_${base_name}_SS.nii.gz"

# Autoboxing to find extent for the uniclean file
3dAutobox \
    -overwrite \
    -extent_ijkord_to_file "${output_folder}/${base_name}_abox.ijkord" \
    -npad 22 \
    -prefix "${output_folder}/tmp_ref_abox.nii.gz" \
    -input "${output_folder}/tmp_${base_name}_SS.nii.gz"

# Process optional files
for file in "$uniclean_file" "$inv1_file" "$inv2_file" "$uni_file" "$t1_file"; do
    if [ -n "$file" ]; then
        base_name=$(basename "$file" .nii.gz)
        3dZeropad \
            -overwrite \
            -master "${output_folder}/tmp_ref_abox.nii.gz" \
            -prefix "${output_folder}/${base_name}_abox.nii.gz" \
            "$file"
    fi
done

# Clean up tmp files
rm -f "$output_folder/tmp_*.nii.gz"

# Clean up tmp files
rm tmp_*.nii.gz

# Print final completion message
echo "Processing complete."
