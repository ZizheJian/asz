#!/bin/bash
set -euo pipefail
cd /home/x-zjian1/asz

output="results/t-fallback-validation-$(date +%Y%m%d-%H%M%S)"
export_arg="ALL,FALLBACK_OUTPUT=$output"

small_job=$(sbatch --parsable --array=0-12%2 --cpus-per-task=4 --time=00:05:00 --export="$export_arg" run_t_fallback_validation.sbatch)
aps_job=$(sbatch --parsable --dependency="afterok:$small_job" --array=14 --cpus-per-task=8 --time=00:05:00 --export="$export_arg" run_t_fallback_validation.sbatch)
nyx_job=$(sbatch --parsable --dependency="afterok:$aps_job" --array=13 --cpus-per-task=16 --time=00:10:00 --export="$export_arg" run_t_fallback_validation.sbatch)
e017_job=$(sbatch --parsable --dependency="afterok:$nyx_job" --array=15 --cpus-per-task=32 --time=00:20:00 --export="$export_arg" run_t_fallback_validation.sbatch)
validation_job=$(sbatch --parsable --dependency="afterok:$e017_job" --export="$export_arg" run_validate_fallback_rtm.sbatch)

printf 'output=%s\nsmall_job=%s\naps_job=%s\nnyx_job=%s\ne017_job=%s\nvalidation_job=%s\n' "$output" "$small_job" "$aps_job" "$nyx_job" "$e017_job" "$validation_job"
