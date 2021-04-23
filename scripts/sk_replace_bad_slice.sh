#! /bin/bash

input_file=$1
input_filename=$(remove_ext $input_file)

slice_to_replace=$2
slice_minus_1=$(($slice_to_replace - 1))
slice_plus_1=$(($slice_to_replace + 1))
slice_plus_2=$(($slice_to_replace + 2))

# get slices 
fslroi $input_file ${input_filename}_fov_till_slc${slice_minus_1}.nii.gz 0 -1 0 -1 0 $slice_minus_1
fslroi $input_file ${input_filename}_slc${slice_minus_1}.nii.gz 0 -1 0 -1 $slice_minus_1 1
fslroi $input_file ${input_filename}_slc${slice_to_replace}.nii.gz 0 -1 0 -1 $slice_to_replace 1
fslroi $input_file ${input_filename}_slc${slice_plus_1}.nii.gz 0 -1 0 -1 $slice_plus_1 1
fslroi $input_file ${input_filename}_fov_from_slc${slice_plus_2}.nii.gz 0 -1 0 -1 ${slice_plus_2} -1

# interpolate middle ground
antsMultivariateTemplateConstruction2.sh \
-a 0 -A 2 -n 0 -d 2 -i 10 -k 1 \
-f 4x2x1 -s 2x1x0vox -q 30x20x4 -t SyN -m CC[2] -c 2 -j 12 \
-o ${input_filename}_slc_middleground_ \
${input_filename}_slc${slice_minus_1}.nii.gz \
${input_filename}_slc${slice_plus_1}.nii.gz > /dev/null 2>&1

mv ${input_filename}_slc_middleground_template0.nii.gz ${input_filename}_slc_new_slc${slice_to_replace}.nii.gz

# merge slices
fslmerge -z \
${input_filename}_Repaired.nii.gz \
${input_filename}_fov_till_slc${slice_minus_1}.nii.gz \
${input_filename}_slc${slice_minus_1}.nii.gz \
${input_filename}_slc_new_slc${slice_to_replace}.nii.gz \
${input_filename}_slc${slice_plus_1}.nii.gz \
${input_filename}_fov_from_slc${slice_plus_2}.nii.gz

# clean up
rm ${input_filename}_slc_middleground_*.*
rm ${input_filename}_fov_till_slc${slice_minus_1}.nii.gz
rm ${input_filename}_slc${slice_minus_1}.nii.gz
rm ${input_filename}_slc${slice_to_replace}.nii.gz
rm ${input_filename}_slc_new_slc${slice_to_replace}.nii.gz
rm ${input_filename}_slc${slice_plus_1}.nii.gz
rm ${input_filename}_fov_from_slc${slice_plus_2}.nii.gz

