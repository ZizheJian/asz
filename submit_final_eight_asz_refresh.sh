#!/bin/bash

set -euo pipefail

cd /home/x-zjian1/asz
small_job=$(sbatch --parsable run_final_eight_asz_refresh_small.sbatch)
e017_job=$(sbatch --parsable run_final_eight_asz_refresh_e017.sbatch)
apsu_job=$(sbatch --parsable run_final_eight_asz_refresh_apsu.sbatch)
merge_job=$(sbatch --parsable --dependency="afterok:${small_job}:${e017_job}:${apsu_job}" run_final_eight_asz_refresh_merge.sbatch)
printf 'small=%s\ne017=%s\napsu=%s\nmerge=%s\n' "$small_job" "$e017_job" "$apsu_job" "$merge_job"
