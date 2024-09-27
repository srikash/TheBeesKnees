#! /bin/bash

Usage() {
    echo ""
    echo "Usage: moco_flirt <4dinput> <4doutput> <refvol> <tr> <interp> <reffile> <wmseg>"
    echo "       Choose interp from {spline,sinc} def - spline "
    echo ""
    exit
}

[ "$3" = "" ] && Usage

tr="2.0"
if [ $# -eq 4 ]; then
    tr=${4}
fi

interpm="spline"
if [ $# -eq 5 ]; then
    interpm=${5}
fi

if [ $# -eq 6 ]; then
    reffile=${6}
fi

if [ $# -eq 7 ]; then
    wmseg=${7}
fi

input=$(${FSLDIR}/bin/remove_ext ${1})
echo ""
echo "processing $input"
echo ""

output=$(${FSLDIR}/bin/remove_ext ${2})
ref=${3}

if [ $(${FSLDIR}/bin/imtest $input) -eq 0 ]; then
    echo "Input does not exist or is not in a supported format"
    exit
fi

fslroi $input ${output}_ref $ref 1

fslsplit $input ${output}_tmp
full_list=$(${FSLDIR}/bin/imglob ${output}_tmp????.*)

mkdir ${output}_mats

for i in $full_list; do
    n=$(echo $i | tail -c 5)
    echo " > processing $n"

    if [ -z $reffile ]; then
        echo "using refvol"
        ${FSLDIR}/bin/flirt \
            -cost normmi \
            -schedule /opt/fsl/etc/flirtsch/bbr.sch \
            -wmseg ${wmseg} \
            -in $i \
            -ref ${output}_ref \
            -interp ${interpm} \
            -o $i \
            -omat ${output}_mats/MAT_${n} \
            -paddingsize 1

        ${FSLDIR}/bin/avscale \
            --allparams \
            ${output}_mats/MAT_${n} \
            $i | grep 'Translations' | tail -c 31 >>${output}.translations
        sed -i -e 's/=//g' ${output}.translations
        ${FSLDIR}/bin/avscale \
            --allparams \
            ${output}_mats/MAT_${n} \
            $i | grep 'Rotation Angles' | tail -c 31 >>${output}.rotations
        sed -i -e 's/=//g' ${output}.rotations

    else
        echo "using reffile"
        ${FSLDIR}/bin/flirt \
            -cost normmi \
            -schedule /opt/fsl/etc/flirtsch/bbr.sch \
            -wmseg ${wmseg} \
            -in $i \
            -ref $reffile \
            -interp ${interpm} \
            -o $i \
            -omat ${output}_mats/MAT_${n} \
            -paddingsize 1

        ${FSLDIR}/bin/avscale \
            --allparams \
            ${output}_mats/MAT_${n} \
            $i | grep 'Translations' | tail -c 31 >>${output}.translations
        sed -i -e 's/=//g' ${output}.translations
        ${FSLDIR}/bin/avscale \
            --allparams \
            ${output}_mats/MAT_${n} \
            $i | grep 'Rotation Angles' | tail -c 31 >>${output}.rotations
        sed -i -e 's/=//g' ${output}.rotations

    fi

done
paste ${output}.translations ${output}.rotations >>${output}.mocorr_params

fslmerge -tr $output $full_list $tr

fslmaths $output -Tmean ${output}_fslTmean

/bin/rm ${output}_tmp????.* ${output}_ref*
