#!/bin/tcsh

# Check if input file argument is provided
if ($#argv < 1 || $#argv > 2) then
    echo "Usage: $0 <input_file> [<mfrac>]"
    exit 1
endif

set input_file = $1

# Set default value for mfrac if not provided
if ($#argv == 1) then
    set mfrac = 0.5
else
    set mfrac = $2
endif

set output_prefix = `basename $input_file .nii.gz`

# Determine the threshold level for clipping using 3dClipLevel
set thr = `3dClipLevel -mfrac $mfrac $input_file`

# Create a brain mask using 3dcalc
3dcalc \
    -overwrite \
    -prefix ${output_prefix}_brain_mask.nii.gz \
    -expr "step(a-$thr)" \
    -a $input_file

# Fill holes in the brain mask using 3dmask_tool
3dmask_tool \
    -overwrite \
    -prefix ${output_prefix}_brain_mask.nii.gz \
    -fill_holes \
    -fill_dirs XY \
    -input ${output_prefix}_brain_mask.nii.gz

# Dilate the brain mask using 3dmask_tool
3dmask_tool \
    -overwrite \
    -prefix ${output_prefix}_brain_mask.nii.gz \
    -dilate_result -3 3 \
    -input ${output_prefix}_brain_mask.nii.gz

# Create clusters in the brain mask using 3dclust
3dclust \
    -overwrite \
    -NN3 100 \
    -savemask ${output_prefix}_brain_mask_clusts.nii.gz \
    ${output_prefix}_brain_mask.nii.gz

# Keep largest connected cluster using 3dcalc
3dcalc \
    -overwrite \
    -a ${output_prefix}_brain_mask_clusts.nii.gz'<1>' \
    -expr a \
    -prefix ${output_prefix}_brain_mask.nii.gz
