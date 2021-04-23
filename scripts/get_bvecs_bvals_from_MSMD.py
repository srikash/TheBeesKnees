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
MSMD_prot_file_data_frame_transposed = MSMD_prot_file_data_frame.transpose()

# Extract BVECS
bvecs = np.float32(np.array(MSMD_prot_file_data_frame_transposed)[0:3,:])
MSMD_bvec_name = MSMD_prot_filename_new.replace('txt','bvec')
print("bvecs : ")
print(np.array2string(bvecs).replace('[','').replace(']',''))
print(" ")
np.savetxt(MSMD_bvec_name,bvecs,fmt='%f',delimiter=' ')
print("bvecs file : %s" % MSMD_bvec_name)
print(" ")

# Extract BVALS (N.B.: units in s/m^2, for reasons.)
bvals_echo_0 = np.array(MSMD_prot_file_data_frame_transposed)[3,:]
## convert units to s/mm^2
bvals_echo_0 = np.float32(bvals_echo_0 / 1e6)
MSMD_bvec_name_0 = MSMD_prot_filename_new.replace('.txt','_Echo_0.bval')
print("bvals Echo_0 : ")
print(np.array2string(bvals_echo_0).replace('[','').replace(']',''))
print(" ")
np.savetxt(MSMD_bvec_name_0,bvals_echo_0.reshape((1,-1)),fmt='%f',delimiter=' ')
print("bvals Echo_0 file : %s" % MSMD_bvec_name_0)
print(" ")

bvals_echo_1 = np.array(MSMD_prot_file_data_frame_transposed)[4,:]
## convert units to s/mm^2
bvals_echo_1 = np.transpose(np.float32(bvals_echo_1 / 1e6))
MSMD_bvec_name_1 = MSMD_prot_filename_new.replace('.txt','_Echo_1.bval')
print("bvals Echo_1 : ")
print(np.array2string(bvals_echo_1).replace('[','').replace(']',''))
print(" ")
np.savetxt(MSMD_bvec_name_1,bvals_echo_1.reshape((1,-1)),fmt='%f',delimiter=' ')
print("bvals Echo_1 file : %s" % MSMD_bvec_name_1)
print(" ")