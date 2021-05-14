#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 22 18:55:35 2021

@author: sriranga
"""
import os
import io 
import argparse
import numpy as np
import pandas as pd
np.set_printoptions(precision=6)

help_text="This script creates a .bvec .bval file from MESMERISED protocol file for use with FSL Eddy"
parser=argparse.ArgumentParser(description=help_text)
parser.add_argument("-i", "--input", help="MESMERISED protocol text file")
parser.add_argument("-a", "--axis_sign", default="gy", help="Select axis to change sign (gx, gy or gz), defaults to 'gy'")
parser.add_argument("-s", "--save_orig", default=False, help="Save orig bvecs file, defaults to False")
args = parser.parse_args()

print(" ")
print("----------------------------------------------------------------------")
print(" ")

# Rename filename more sensibly
MSMD_prot_filename_old = args.input
print("Input file : %s" % MSMD_prot_filename_old)
print(" ")
MSMD_prot_filename_new = MSMD_prot_filename_old.replace('+AF8-','_')
os.rename(MSMD_prot_filename_old,MSMD_prot_filename_new)
print("Renamed file : %s" % MSMD_prot_filename_new)
print(" ")

# Convert to dataframe
MSMD_prot_file=open(MSMD_prot_filename_new, "r")
MSMD_prot_file_data = MSMD_prot_file.read()
MSMD_prot_file_data = MSMD_prot_file_data.replace('#','').replace(',',' ')
MSMD_prot_file_data_frame = pd.read_csv(io.StringIO(MSMD_prot_file_data),delim_whitespace=True)
MSMD_prot_file_data_frame2 = MSMD_prot_file_data_frame.copy()
MSMD_prot_file_data_frame_transposed = MSMD_prot_file_data_frame.transpose()

# Extract BVECS
orig_bvecs = np.float32(np.array(MSMD_prot_file_data_frame_transposed)[0:3,:])
MSMD_orig_bvec_name = MSMD_prot_filename_new.replace('.txt','_orig.bvec')
print("orig bvecs : ")
print(np.array2string(orig_bvecs).replace('[','').replace(']',''))
print(" ")
if args.save_orig is True:
    np.savetxt(MSMD_orig_bvec_name,orig_bvecs,fmt='%f',delimiter=' ')
    print("orig bvecs file : %s" % MSMD_orig_bvec_name)
    print(" ")

# Fix co-ordinate sign, for axial MESMERISED use X,-Y,Z
print("Multiplying -1.0 to axis : %s" % args.axis_sign)
print(" ")
if args.axis_sign == "gx":
    MSMD_prot_file_data_frame2["gx"] = MSMD_prot_file_data_frame2["gx"].mul(-1.0)
elif args.axis_sign == "gy":
    MSMD_prot_file_data_frame2["gy"] = MSMD_prot_file_data_frame2["gy"].mul(-1.0)
elif args.axis_sign == "gz":
    MSMD_prot_file_data_frame2["gz"] = MSMD_prot_file_data_frame2["gz"].mul(-1.0)

MSMD_prot_file_data_frame2_transposed = MSMD_prot_file_data_frame2.transpose()

# Extract BVECS
bvecs = np.float32(np.array(MSMD_prot_file_data_frame2_transposed)[0:3,:])
MSMD_bvec_name = MSMD_prot_filename_new.replace('txt','bvec')
print("bvecs : ")
print(np.array2string(bvecs).replace('[','').replace(']',''))
print(" ")
np.savetxt(MSMD_bvec_name,bvecs,fmt='%f',delimiter=' ')
print("bvecs file : %s" % MSMD_bvec_name)
print(" ")

# Extract BVALS (N.B.: units in s/m^2, for reasons.)
bvals_echo_0 = np.array(MSMD_prot_file_data_frame2_transposed)[3,:]
## convert units to s/mm^2
bvals_echo_0 = np.float32(bvals_echo_0 / 1e6)
MSMD_bvec_name_0 = MSMD_prot_filename_new.replace('.txt','_SE.bval')
print("bvals Echo_0 : ")
print(np.array2string(bvals_echo_0).replace('[','').replace(']',''))
print(" ")
np.savetxt(MSMD_bvec_name_0,bvals_echo_0.reshape((1,-1)),fmt='%f',delimiter=' ')
print("bvals SE file : %s" % MSMD_bvec_name_0)
print(" ")

bvals_echo_1 = np.array(MSMD_prot_file_data_frame2_transposed)[4,:]
## convert units to s/mm^2
bvals_echo_1 = np.transpose(np.float32(bvals_echo_1 / 1e6))
MSMD_bvec_name_1 = MSMD_prot_filename_new.replace('.txt','_STE.bval')
print("bvals STE : ")
print(np.array2string(bvals_echo_1).replace('[','').replace(']',''))
print(" ")
np.savetxt(MSMD_bvec_name_1,bvals_echo_1.reshape((1,-1)),fmt='%f',delimiter=' ')
print("bvals STE file : %s" % MSMD_bvec_name_1)
print(" ")