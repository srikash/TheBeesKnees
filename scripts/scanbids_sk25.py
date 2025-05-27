#!/usr/bin/env python3
import argparse
from pathlib import Path

BIDS_DATA_TYPES = [
    "anat", "dwi", "func", "fmap", "perf",
    "meg", "eeg", "ieeg", "beh", "pet",
    "micr", "nirs", "motion", "mrs"
]

MULTIPART_EXTS = [
    '.nii.gz', '.tar.gz', '.nii', '.bval', '.bvec', '.json', '.tsv', '.mat', '.csv'
]

def get_full_ext(filename):
    """Get multi-part extension (e.g. .nii.gz) if present, else last suffix."""
    name = filename.name
    for ext in MULTIPART_EXTS:
        if name.endswith(ext):
            return ext
    return filename.suffix

def main():
    parser = argparse.ArgumentParser(
        description="Summarize BIDS directory for subjects, sessions, and data types."
    )
    parser.add_argument(
        "bids_dir", type=Path, help="Path to the BIDS directory (top-level)"
    )
    args = parser.parse_args()
    bids_dir = args.bids_dir.resolve()
    if not bids_dir.is_dir():
        print(f"ERROR: '{bids_dir}' is not a valid directory.")
        return

    subject_dirs = sorted([p for p in bids_dir.iterdir() if p.is_dir() and p.name.startswith("sub-")])
    n_subjects = len(subject_dirs)
    session_set = set()
    all_types_found = set()
    summary = []

    for subj_dir in subject_dirs:
        subj = subj_dir.name
        ses_dirs = sorted([p for p in subj_dir.iterdir() if p.is_dir() and p.name.startswith("ses-")])
        if ses_dirs:
            for ses_dir in ses_dirs:
                ses = ses_dir.name
                session_set.add(ses)
                type_counts = {}
                for dtype in BIDS_DATA_TYPES:
                    dtype_dir = ses_dir / dtype
                    if dtype_dir.is_dir():
                        all_types_found.add(dtype)
                        files = [f for f in dtype_dir.iterdir() if f.is_file()]
                        nfiles = len(files)
                        file_exts = set(get_full_ext(f) for f in files)
                        basenames = set(f.name[:-len(get_full_ext(f))] for f in files if len(get_full_ext(f)) > 0)
                        type_counts[dtype] = (nfiles, file_exts, basenames)
                summary.append((subj, ses, type_counts))
        else:
            # No session directories, check at subject level
            type_counts = {}
            for dtype in BIDS_DATA_TYPES:
                dtype_dir = subj_dir / dtype
                if dtype_dir.is_dir():
                    all_types_found.add(dtype)
                    files = [f for f in dtype_dir.iterdir() if f.is_file()]
                    nfiles = len(files)
                    file_exts = set(get_full_ext(f) for f in files)
                    basenames = set(f.name[:-len(get_full_ext(f))] for f in files if len(get_full_ext(f)) > 0)
                    type_counts[dtype] = (nfiles, file_exts, basenames)
            summary.append((subj, None, type_counts))

    n_total_sessions = len(session_set)
    session_list = sorted(list(session_set))
    found_types = sorted(list(all_types_found))

    log_path = bids_dir / "bids_summary.log"
    with open(log_path, "w") as f:
        f.write(f"BIDS Directory: {bids_dir}\n")
        f.write(f"Total subjects found: {n_subjects}\n")
        f.write(f"Unique sessions found: {n_total_sessions}\n")
        f.write(f"Session names: {', '.join(session_list) if session_list else 'None'}\n")
        f.write(f"BIDS data types found: {', '.join(found_types) if found_types else 'None'}\n")
        f.write("\nDetailed listing per subject/session:\n")

        for subj, ses, type_counts in summary:
            f.write(f"  {subj}")
            if ses:
                f.write(f" | {ses}")
            else:
                f.write(" | (no session)")
            if not type_counts:
                f.write(" : No BIDS data type folders present\n")
            else:
                f.write("\n")
                for dtype in BIDS_DATA_TYPES:
                    if dtype in type_counts:
                        nfiles, file_exts, basenames = type_counts[dtype]
                        ext_str = ', '.join(sorted(file_exts))
                        f.write(f"    - {dtype}: {nfiles} files [exts: {ext_str}]\n")
                        for bn in sorted(basenames):
                            f.write(f"        * {bn}\n")
            f.write("\n")

    print(f"Summary written to {log_path}\n\n--- BIDS Summary Log ---\n")
    with open(log_path, "r") as f:
        print(f.read())

if __name__ == "__main__":
    main()
