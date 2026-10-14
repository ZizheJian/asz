# Experiment configuration format

`t1_start_compressors.py` accepts a JSON file whose top level is a nonempty list of tasks. Each task requires:

- `data_path_list`: one or more input paths. All inputs in one task share a shape.
- `data_shape`: exactly three positive dimensions.
- `rel_eb_list`: positive relative error bounds.
- `method_list`: one or more compressor definitions.

Optional task fields are:

- `cleanup_after_each_test`: delete the compressed stream and reconstruction after recording metrics.
- `comparison_baseline`: method name used to calculate `CR_DROP_PERCENT`.
- `summary_csv`: project-relative or absolute summary path. It must appear together with `comparison_baseline`.

The short method names are `asz`, `sz3`, `qoz`, `zfp`, and `sperr`. A named method object can set ASZ parameters or read/write a plan:

```json
[
  {
    "data_path_list":["/path/to/data.f32"],
    "data_shape":[100,500,500],
    "rel_eb_list":[0.001,0.0001],
    "method_list":[
      {
        "name":"asz_self_plan",
        "compressor":"asz",
        "write_plan":"plans/{stem}.json"
      },
      {
        "name":"asz_shared_plan",
        "compressor":"asz",
        "read_plan":"plans/shared.json"
      },
      "sz3",
      "qoz"
    ],
    "comparison_baseline":"asz_self_plan",
    "summary_csv":"results/comparison.csv",
    "cleanup_after_each_test":true
  }
]
```

`read_plan` and `write_plan` are mutually exclusive. When a task contains multiple inputs, `write_plan` must contain `{stem}` or `{name}` so files do not overwrite one another.

Supported ASZ method fields include:

- Plan parameters: `pivot_eb_ratio`, `eb_ratio`, `slope_ratio`, `block_pivot_ratio`, `max_layer_num`, `full_predictor_search_layer_num`, and `t_precision`.
- Sampling and selection parameters: `generate_config_sample_stride`, `h1_block_sampling_num`, `stat_eb_ratio`, `predictor_family_sample_limit`, `predictor_family_mse_ratio_threshold`, `default_slope_invalid_ratio_threshold`, `default_slope_fallback`, and `default_slope_eb_span`.
- Coefficient settings: `t_min`, `t_max`, `t_policy`, `block_t_policy`, and `report_t_histogram`.
- Dataset-wide family override: `predictor_family`, either `cubic` or `quintic`.
- Error-bound-specific block policy: `coarse_block_pivot_ratio` and `fine_block_pivot_ratio`, which must be set together.

Validate a configuration without touching the data:

```bash
python3 t1_start_compressors.py configs/example.json --dry-run
```

## Maintained experiment groups

- `family_mse_validation.json`: paired adaptive-4R/fixed-6R selector validation on all six Figure 3 datasets at five relative error bounds (`1e-1` through `1e-5`),60 full-compression runs. This specialized manifest is consumed by `run_family_mse_validation.py`,not `t1_start_compressors.py`; see the root README for the protocol and Slurm launcher.
- `family_mse_validation_eighteen.json` and the dataset list in `plot_final_eighteen_rd.py`: current 18-field paper selection,with RTM big snapshot 0750 replacing APS Kaz.
- `final_eighteen_*.json`,`apsu006.json`,and `rtm_middle.json`: measurement batches supplying the current paper evaluation; APS-Kaz-specific batches are retained only as historical inputs.
- `isabel_plan_transfer.json`: Pf24 plan applied to the remaining Isabel pressure time steps and compared with self-generated plans, SZ3, and QoZ.
- `aramco_plan_transfer.json`: Aramco time-step transfer check.
- `final_eighteen_nyx_baryon.json`: the selected Nyx baryon-density evaluation.
- Dataset-named files such as `aps_kaz.json` and `scale_letkf_pres.json`: small focused runs.

Historical final-eight/final-twelve batches and parameter grids were removed after their selected settings were incorporated into the current defaults. Their compact numerical summaries remain under `csv/`, and their complete definitions remain recoverable from Git history.
