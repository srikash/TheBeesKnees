#! /bin/bash


for subject in {"sub-01_FB","sub-02_AB","sub-03_SH","sub-04_SD","sub-05_ZC"}
do
    for shot in {"anterior","posterior","superior","inferior","lefthemi","righthemi"}
    do
        echo "${subject}_hV4_${shot}"
        
        draw_text=$(echo "'text 25,75 \"${subject} ${shot}\"'")
        
        eval $(eval convert -pointsize 50 -fill yellow -draw $($eval echo $draw_text) ${subject}_hV4_${shot}.png ${subject}_hV4_${shot}_wCap.png)
        
    done
    
    convert \
    ${subject}_hV4_anterior_wCap.png \
    ${subject}_hV4_posterior_wCap.png \
    ${subject}_hV4_superior_wCap.png \
    ${subject}_hV4_inferior_wCap.png \
    ${subject}_hV4_lefthemi_wCap.png \
    ${subject}_hV4_righthemi_wCap.png \
    -quality 100 \
    ${subject}_hV4_FreesurferROI.pdf
    
done

