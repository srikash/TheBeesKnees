#!/usr/bin/env python3
"""
BTO DWI Pipeline

Author: Kashyap, S
Date: 2025

Description:
-------------
This script orchestrates a modular BIDS-compliant DWI preprocessing pipeline. It wraps three main processing steps (combining/copying diffusion data, TOPUP preparation, and EDDY preparation/execution).
into one flexible command-line tool. Each step can be run independently or all together.

Steps:
  step-1: Find, combine, and copy DWI files, generate b=0 images for AP/PA.
  step-2: Create TOPUP input, parameter, config, and command.
  step-3: (Optionally) run TOPUP and EDDY, generate indices and slspec.
  all   : Run all three steps in sequence (with optional --execute for step-3).

USAGE EXAMPLES:
  python bto_dwi_prep.py -m step-1 /path/to/BIDS
  python bto_dwi_prep.py -m step-2 /path/to/BIDS
  python bto_dwi_prep.py -m step-3 /path/to/BIDS --execute
  python bto_dwi_prep.py -m all /path/to/BIDS --execute

For each step, see the --help message for more details.

Requirements:
-------------
- Python >= 3.7
- nibabel, numpy
- External tools:
    - FSL: fslmaths, topup, eddy_cuda10.2 (or eddy_cuda)
    - FreeSurfer: mri_synthstrip
"""

import argparse
import json
from pathlib import Path
import nibabel as nib
import numpy as np
import os
import shutil
import subprocess
import sys


def check_external_commands():
    required = {
        "fslmaths": "FSL",
        "topup": "FSL",
        "eddy_cuda10.2": "FSL (or eddy_cuda)",
        "mri_synthstrip": "FreeSurfer",
    }
    missing = []
    for cmd, pkg in required.items():
        if shutil.which(cmd) is None:
            missing.append(f"{cmd} [{pkg}]")
    # Accept eddy_cuda or eddy_cuda10.2 for CUDA versions
    if shutil.which("eddy_cuda10.2") is None and shutil.which("eddy_cuda") is None:
        missing.append("eddy_cuda10.2 or eddy_cuda [FSL]")
    if missing:
        print("\nERROR: The following required MRI tools are missing or not in your PATH:")
        for cmd in missing:
            print(f"  - {cmd}")
        print("\nPlease ensure FSL and FreeSurfer are installed and sourced before running this script.")
        sys.exit(1)

###############################
# Helper functions shared by all steps
###############################


def get_nvols(nifti_path):
    img = nib.load(str(nifti_path))
    data = img.get_fdata()
    if data.ndim == 3:
        return 1
    else:
        return data.shape[3]


def run_cmd(cmd, cwd=None):
    print(f"Running:\n{cmd}\n")
    try:
        subprocess.run(cmd, shell=True, check=True, cwd=cwd)
        print("Success.\n")
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}\n")

###############################
# Step 1: Combine, copy, and extract b0
###############################


def concat_bvals(files, out_bval):
    bvals = []
    for f in files:
        with open(f, 'r') as fb:
            bvals.extend(fb.read().split())
    with open(out_bval, 'w') as fo:
        fo.write(' '.join(bvals) + '\n')


def concat_bvecs(files, out_bvec):
    bvec_arrays = []
    for f in files:
        arr = np.loadtxt(f)
        if arr.ndim == 1:
            raise ValueError(
                f"bvec file {f} appears 1D or malformed (shape {arr.shape})")
        if arr.shape[0] == 3:
            bvec_arrays.append(arr)
        elif arr.shape[1] == 3:
            bvec_arrays.append(arr.T)
        else:
            raise ValueError(
                f"bvec file {f} has unexpected shape {arr.shape} (expected 3xN or Nx3)")
    bvecs = np.hstack(bvec_arrays)
    np.savetxt(out_bvec, bvecs, fmt='%.8f')


def copy_and_rename(src, dest):
    if src.exists():
        shutil.copy(src, dest)
        print(f"Copied {src} -> {dest}")
    else:
        print(f"Warning: {src} missing (not copied)")


def extract_b0_volumes(combined_nii, combined_bval, combined_json, out_b0_nii, out_b0_json):
    with open(combined_bval, 'r') as fb:
        bvals = [float(x) for x in fb.read().split()]
    b0_indices = [i for i, b in enumerate(bvals) if b == 0.0]
    if not b0_indices:
        print(f"Warning: No b0 volumes found in {combined_bval}")
        return
    img = nib.load(combined_nii)
    data = img.get_fdata()
    if data.ndim != 4:
        raise ValueError(
            f"Expected 4D image in {combined_nii}, got shape {data.shape}")
    data_b0 = data[..., b0_indices]
    nib.Nifti1Image(data_b0, img.affine, img.header).to_filename(out_b0_nii)
    print(f"Extracted b0 volumes: {out_b0_nii}")
    shutil.copy(combined_json, out_b0_json)
    print(f"Copied JSON for b0: {out_b0_json}")


def step1_combine_and_extract_b0(bids_dir):
    bids_dir = bids_dir.resolve()
    derivatives_dir = bids_dir / "derivatives"
    derivatives_dir.mkdir(exist_ok=True)
    for subj in sorted(bids_dir.glob("sub-*")):
        for ses in sorted(subj.glob("ses-*")):
            dwi_dir = ses / "dwi"
            if not dwi_dir.is_dir():
                continue
            # === Combine AP runs ===
            run1 = next(dwi_dir.glob(
                "*_dir-AP_run-1_part-mag_dwi.nii.gz"), None)
            run2 = next(dwi_dir.glob(
                "*_dir-AP_run-2_part-mag_dwi.nii.gz"), None)
            if run1 and run2:
                base = run1.name.replace(
                    "_run-1", "").replace(".nii.gz", "") + "_combined"
                out_subj = derivatives_dir / subj.name / ses.name / "dwi"
                out_subj.mkdir(exist_ok=True, parents=True)
                # Combine NIFTIs
                img1 = nib.load(run1)
                img2 = nib.load(run2)
                data_combined = np.concatenate(
                    [img1.get_fdata(), img2.get_fdata()], axis=3)
                affine = img1.affine
                hdr = img1.header
                out_nii = out_subj / f"{base}.nii.gz"
                nib.Nifti1Image(data_combined, affine,
                                hdr).to_filename(out_nii)
                print(f"Saved combined NIfTI: {out_nii}")
                # Copy JSON from run-1, rename
                run1_json = run1.with_suffix('.json').with_name(
                    run1.name.replace('.nii.gz', '.json'))
                out_json = out_subj / f"{base}.json"
                copy_and_rename(run1_json, out_json)
                # Concatenate bval and bvec files
                run1_bval = run1.with_suffix('.bval').with_name(
                    run1.name.replace('.nii.gz', '.bval'))
                run2_bval = run2.with_suffix('.bval').with_name(
                    run2.name.replace('.nii.gz', '.bval'))
                out_bval = out_subj / f"{base}.bval"
                run1_bvec = run1.with_suffix('.bvec').with_name(
                    run1.name.replace('.nii.gz', '.bvec'))
                run2_bvec = run2.with_suffix('.bvec').with_name(
                    run2.name.replace('.nii.gz', '.bvec'))
                out_bvec = out_subj / f"{base}.bvec"
                if run1_bval.exists() and run2_bval.exists():
                    concat_bvals([run1_bval, run2_bval], out_bval)
                    print(f"Saved concatenated bval: {out_bval}")
                else:
                    print(f"Warning: Missing bval file for {run1} or {run2}.")
                if run1_bvec.exists() and run2_bvec.exists():
                    concat_bvecs([run1_bvec, run2_bvec], out_bvec)
                    print(f"Saved concatenated bvec: {out_bvec}")
                else:
                    print(f"Warning: Missing bvec file for {run1} or {run2}.")
                # --- Extract b0 from combined AP and save as _b0.nii.gz/json ---
                ap_b0_stem = base.split('dir-AP')[0] + 'dir-AP_b0'
                ap_b0_nii = out_subj / f"{ap_b0_stem}.nii.gz"
                ap_b0_json = out_subj / f"{ap_b0_stem}.json"
                extract_b0_volumes(
                    str(out_nii),
                    str(out_bval),
                    str(out_json),
                    str(ap_b0_nii),
                    str(ap_b0_json),
                )
            # === Copy and Rename PA files as _b0 (.nii.gz and .json only) ===
            pa_nii = next(dwi_dir.glob(
                "*_dir-PA_run-1_part-mag_dwi.nii.gz"), None)
            if pa_nii:
                out_subj = derivatives_dir / subj.name / ses.name / "dwi"
                out_subj.mkdir(exist_ok=True, parents=True)
                b0_base = pa_nii.name.replace(
                    "_run-1_part-mag_dwi.nii.gz", "_b0.nii.gz")
                out_pa_nii = out_subj / b0_base
                copy_and_rename(pa_nii, out_pa_nii)
                # JSON
                pa_json = pa_nii.with_suffix('.json').with_name(
                    pa_nii.name.replace('.nii.gz', '.json'))
                out_pa_json = out_subj / b0_base.replace('.nii.gz', '.json')
                copy_and_rename(pa_json, out_pa_json)

###############################
# Step 2: TOPUP input, params, config, and command
###############################


def concat_topup_inputs(ap_b0, pa_b0, out_path):
    img_ap = nib.load(str(ap_b0))
    img_pa = nib.load(str(pa_b0))
    data_ap = img_ap.get_fdata()
    data_pa = img_pa.get_fdata()
    if data_ap.ndim == 3:
        data_ap = data_ap[..., np.newaxis]
    if data_pa.ndim == 3:
        data_pa = data_pa[..., np.newaxis]
    data_concat = np.concatenate([data_ap, data_pa], axis=3)
    nib.Nifti1Image(data_concat, img_ap.affine,
                    img_ap.header).to_filename(str(out_path))
    print(f"Saved TOPUP input: {out_path}")


def write_topup_config(config_path):
    config_text = """# Resolution (knot-spacing) of warps in mm
--warpres=12,12,8,8,8,4,4,2,2
# Subsampling level (a value of 2 indicates that a 2x2x2 neighbourhood is collapsed to 1 voxel)
--subsamp=2,2,2,2,2,1,1,1,1
# FWHM of gaussian smoothing
--fwhm=8,4,4,4,2,2,2,0,0
# Maximum number of iterations
--miter=5,5,5,5,5,10,20,20,10
# Relative weight of regularisation
--lambda=0.005,0.001,0.0001,0.000015,0.000005,0.0000005,0.00000005,0.0000000005,0.00000000001
# If set to 1 lambda is multiplied by the current average squared difference
--ssqlambda=1
# Regularisation model
--regmod=bending_energy
# If set to 1 movements are estimated along with the field
--estmov=1,1,1,1,1,0,0,0,0
# 0=Levenberg-Marquardt, 1=Scaled Conjugate Gradient
--minmet=0,0,0,0,0,1,1,1,1
# Quadratic or cubic splines
--splineorder=3
# Precision for calculation and storage of Hessian
--numprec=double
# Linear or spline interpolation
--interp=spline
# If set to 1 the images are individually scaled to a common mean intensity 
--scale=1
"""
    with open(config_path, "w") as f:
        f.write(config_text)
    print(f"Wrote TOPUP config: {config_path}")


def step2_make_topup(bids_dir):
    derivatives = bids_dir.resolve() / "derivatives"
    if not derivatives.is_dir():
        print(f"Derivatives folder not found: {derivatives}")
        return
    nthr = os.cpu_count() or 8
    for subj_dir in sorted(derivatives.glob("sub-*")):
        for ses_dir in sorted(subj_dir.glob("ses-*")):
            dwi_dir = ses_dir / "dwi"
            if not dwi_dir.is_dir():
                continue
            config_path = dwi_dir / "bto_dwi_sk25.cnf"
            write_topup_config(config_path)
            prefix = f"{subj_dir.name}_{ses_dir.name}_acq-EP2D"
            ap_json = dwi_dir / f"{prefix}_dir-AP_part-mag_dwi_combined.json"
            ap_b0_nii = dwi_dir / f"{prefix}_dir-AP_b0.nii.gz"
            pa_b0_nii = dwi_dir / f"{prefix}_dir-PA_b0.nii.gz"
            topup_input = dwi_dir / f"{prefix}_b0_TOPUP_input.nii.gz"
            params_out = dwi_dir / f"{prefix}_b0_TOPUP_input.params"
            if ap_b0_nii.exists() and pa_b0_nii.exists():
                if not topup_input.exists():
                    concat_topup_inputs(ap_b0_nii, pa_b0_nii, topup_input)
            else:
                print(f"Missing AP or PA b0 in {dwi_dir}, skipping.")
                continue
            if not ap_json.exists():
                print(
                    f"Missing AP combined JSON in {dwi_dir}, skipping .params creation.")
                continue
            with open(ap_json, "r") as f:
                meta = json.load(f)
            trt = meta.get("TotalReadoutTime")
            if trt is None:
                print(f"TotalReadoutTime missing in {ap_json}, skipping.")
                continue
            n_ap = get_nvols(ap_b0_nii)
            n_total = get_nvols(topup_input)
            n_pa = n_total - n_ap
            with open(params_out, "w") as f:
                for _ in range(n_ap):
                    f.write(f"0 -1 0 {trt}\n")
                for _ in range(n_pa):
                    f.write(f"0 1 0 {trt}\n")
            print(f"Wrote params: {params_out}")
            imain = topup_input.resolve()
            datain = params_out.resolve()
            config = config_path.resolve()
            out_prefix = dwi_dir / f"{prefix}_b0_TOPUP_output"
            fout = dwi_dir / f"{prefix}_b0_TOPUP_output_fmap_Hz.nii.gz"
            iout = dwi_dir / f"{prefix}_b0_TOPUP_output_fmap_mag.nii.gz"
            cmd = (
                f"${{FSLDIR}}/bin/topup --imain={imain} --datain={datain} --config={config} "
                f"--out={out_prefix} --fout={fout} --iout={iout} --nthr={nthr}"
            )
            cmd_file = dwi_dir / f"{prefix}_b0_TOPUP.cmd"
            with open(cmd_file, "w") as f:
                f.write(cmd + "\n")
            print(f"\nTOPUP command for {dwi_dir}:")
            print(cmd + "\n")

###############################
# Step 3: Run/synthesize TOPUP and EDDY, create slspec
###############################


def generate_slspec(json_file, slspec_file):
    with open(json_file, "r") as f:
        metadata = json.load(f)
    if "SliceTiming" not in metadata:
        print(
            f"SliceTiming not found in {json_file}, skipping slspec creation.")
        return
    slicetimes = np.array(metadata["SliceTiming"])
    sortedslicetimes = np.sort(slicetimes)
    sindx = np.argsort(slicetimes)
    diffs = np.diff(sortedslicetimes)
    n_groups = np.sum(diffs != 0) + 1
    mb = len(sortedslicetimes) // n_groups
    slspec = sindx.reshape((mb, len(sindx)//mb)).T
    np.savetxt(slspec_file, slspec, fmt="%3d", delimiter=" ")
    print(f"Saved slspec to {slspec_file}")


def step3_run_eddy(bids_dir, execute=False):
    derivatives = bids_dir.resolve() / "derivatives"
    if not derivatives.is_dir():
        print(f"Derivatives folder not found: {derivatives}")
        return
    for subj_dir in sorted(derivatives.glob("sub-*")):
        for ses_dir in sorted(subj_dir.glob("ses-*")):
            dwi_dir = ses_dir / "dwi"
            if not dwi_dir.is_dir():
                continue
            prefix = f"{subj_dir.name}_{ses_dir.name}_acq-EP2D"
            cmd_file = dwi_dir / f"{prefix}_b0_TOPUP.cmd"
            combined_nii = dwi_dir / \
                f"{prefix}_dir-AP_part-mag_dwi_combined.nii.gz"
            fmap_mag = dwi_dir / f"{prefix}_b0_TOPUP_output_fmap_mag.nii.gz"
            fmap_mag_brainmask = dwi_dir / \
                f"{prefix}_b0_TOPUP_output_fmap_mag_brainmask.nii.gz"
            fmap_mag_brain = dwi_dir / \
                f"{prefix}_b0_TOPUP_output_fmap_mag_brain.nii.gz"
            params_out = dwi_dir / f"{prefix}_b0_TOPUP_input.params"
            bvec_file = dwi_dir / f"{prefix}_dir-AP_part-mag_dwi_combined.bvec"
            bval_file = dwi_dir / f"{prefix}_dir-AP_part-mag_dwi_combined.bval"
            json_file = dwi_dir / f"{prefix}_dir-AP_part-mag_dwi_combined.json"
            slspec_file = dwi_dir / f"{prefix}_dwi_combined_eddy.slspec"
            indices_file = dwi_dir / f"{prefix}_dwi_combined_eddy.indices"
            topup_base = dwi_dir / f"{prefix}_b0_TOPUP_output"
            eddy_out = dwi_dir / f"{prefix}_dwi_combined_eddy"
            # 1. Run (or synthesize) TOPUP command if the .cmd file exists
            if cmd_file.exists():
                print(f"\nTOPUP command for {dwi_dir}:")
                with open(cmd_file, "r") as f:
                    cmd = f.read().strip()
                print(cmd + "\n")
                if execute:
                    run_cmd(cmd, cwd=dwi_dir)
            else:
                print(f"TOPUP cmd file missing in {dwi_dir}, skipping.")
                continue
            # 2. Count volumes in combined NIfTI and write indices
            if combined_nii.exists():
                nvols = get_nvols(combined_nii)
                with open(indices_file, "w") as f:
                    f.write(' '.join(['1'] * nvols) + '\n')
                print(f"Wrote indices: {indices_file}")
            else:
                print(
                    f"Combined NIfTI missing in {dwi_dir}, skipping indices.")
            # 2b. Generate slspec from JSON
            if json_file.exists():
                generate_slspec(json_file, slspec_file)
            else:
                print(f"{json_file} not found, skipping slspec.")
            # 3. Run FSL fslmaths to mean-threshold fmap_mag
            if fmap_mag.exists():
                fslmaths_cmd = f"${{FSLDIR}}/bin/fslmaths {fmap_mag.resolve()} -Tmean -thr 0 {fmap_mag.resolve()}"
                run_cmd(fslmaths_cmd, cwd=dwi_dir)
            else:
                print(f"{fmap_mag} not found, skipping fslmaths.")
            # 4. Run FreeSurfer mri_synthstrip for brain extraction
            if fmap_mag.exists():
                synthstrip_cmd = (
                    f"${{FREESURFER_HOME}}/bin/mri_synthstrip "
                    f"-i {fmap_mag.resolve()} -m {fmap_mag_brainmask.resolve()} -o {fmap_mag_brain.resolve()}"
                )
                run_cmd(synthstrip_cmd, cwd=dwi_dir)
            else:
                print(f"{fmap_mag} not found for synthstrip, skipping.")
            # 5. Synthesize and (optionally) run eddy_cuda command
            eddy_cmd = (
                f"${{FSLDIR}}/bin/eddy_cuda "
                f'--imain="{combined_nii.resolve()}" '
                f'--mask="{fmap_mag_brainmask.resolve()}" '
                f'--index="{indices_file.resolve()}" '
                f'--acqp="{params_out.resolve()}" '
                f'--bvecs="{bvec_file.resolve()}" '
                f'--bvals="{bval_file.resolve()}" '
                f'--slspec="{slspec_file.resolve()}" '
                f'--topup="{topup_base.resolve()}" '
                f'--estimate_move_by_susceptibility '
                f'--repol '
                f'--ol_type=both '
                f'--mporder=10 '
                f'--s2v_niter=5 '
                f'--s2v_interp=spline '
                f'--niter=10 '
                f'--ol_nstd=5 '
                f'--out="{eddy_out}" '
                f'--cnr_maps '
                f'--residuals '
                f'--verbose'
            )
            eddy_cmd_file = dwi_dir / f"{eddy_out}.cmd"
            with open(eddy_cmd_file, "w") as f:
                f.write(eddy_cmd + "\n")
            print(f"\nEddy command for {dwi_dir}:")
            print(eddy_cmd + "\n")
            if execute:
                run_cmd(eddy_cmd, cwd=dwi_dir)

###############################
# Main dispatch
###############################


def main():

    check_external_commands()

    parser = argparse.ArgumentParser(
        description="""\
BTO DWI Preparation Pipeline (modular & all-in-one)
---------------------------------------------------
This script provides modular and unified DWI preprocessing for BIDS datasets.

Modes:
  step-1 : Combine/copy raw DWI, concat bvals/bvecs, and extract b0 for AP/PA.
  step-2 : Prepare TOPUP files: merge b0s, make param/config/cmd.
  step-3 : Make/execute EDDY & TOPUP commands, indices, and slspec.
  all    : Run all three steps above in sequence (see below).

Arguments:
  bids_dir  : Path to the root BIDS dataset directory.

Typical usage:
  python bto_dwi_prep.py -m all /path/to/BIDS --execute

Use --execute to actually run FSL/FS commands in step-3/all (otherwise only command lines are synthesized/written).
""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-m", "--mode",
        required=True,
        choices=["step-1", "step-2", "step-3", "all"],
        help="""\
Which step(s) to run:
  step-1 : Combine/copy DWI, concat bvals/bvecs, extract b0
  step-2 : Prepare TOPUP input, param, config, and command
  step-3 : Synthesize/run TOPUP/EDDY, make indices & slspec
  all    : Run all three steps in order (step-1, step-2, step-3)
""")
    parser.add_argument("bids_dir", type=Path,
                        help="Path to root BIDS directory (with sub-XX/ses-YY).")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run TOPUP and EDDY commands (step-3/all). If omitted, only command lines are written."
    )
    args = parser.parse_args()

    print("\n=== BTO DWI Preparation Pipeline ===\n")

    if args.mode == "step-1":
        print("[STEP 1] Combine/copy DWI and extract b0 images\n")
        step1_combine_and_extract_b0(args.bids_dir)
    elif args.mode == "step-2":
        print("[STEP 2] Prepare TOPUP input, parameter, config, and command\n")
        step2_make_topup(args.bids_dir)
    elif args.mode == "step-3":
        print("[STEP 3] Synthesize and/or execute TOPUP and EDDY\n")
        step3_run_eddy(args.bids_dir, execute=args.execute)
    elif args.mode == "all":
        print("[ALL STEPS] Running full pipeline: step-1 → step-2 → step-3\n")
        step1_combine_and_extract_b0(args.bids_dir)
        step2_make_topup(args.bids_dir)
        step3_run_eddy(args.bids_dir, execute=args.execute)
    else:
        print("Invalid mode. Use one of: step-1, step-2, step-3, all.")


if __name__ == "__main__":
    main()
