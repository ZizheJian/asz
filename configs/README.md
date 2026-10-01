# ASZ experiment configurations

Run one configuration:

```bash
python t1_start_compressors.py isabel_pf01
```

Reuse existing builds:

```bash
python t1_start_compressors.py isabel_pf01 --skip-build
```

Regenerate the SZ3/QoZ baselines for the six tuning datasets:

```bash
python t1_start_compressors.py tuning_baselines --skip-build
```

Both tuning configurations use the same five relative error bounds: `1e-1`, `1e-2`, `1e-3`, `1e-4`, and `1e-5`.

Regenerate ASZ results for the same datasets:

```bash
python t1_start_compressors.py tuning_asz --skip-build
```

Compare dataset-wide fixed Lagrange quintic prediction against the current cubic predictor while keeping ASZ's generated axes and traversal orders:

```bash
python t1_start_compressors.py tuning_asz_quintic --skip-build
```

Reproduce the final layer-count/error-ratio comparison and the fixed-`t` ablation:

```bash
python t1_start_compressors.py layer_eb_finalists --skip-build --no-csv
python analyze_layer_eb_screen.py --result-prefix layer_eb_finalists_ --curve-baseline-method asz_l10_e72 --output results/layer_eb_finalists_ranking.csv
python t1_start_compressors.py t_policy_tuning --skip-build --no-csv
python analyze_layer_eb_screen.py --result-prefix t_policy_ --curve-baseline-method asz_t_adaptive --output results/t_policy_ranking.csv
```

The archived summaries are `csv/layer_eb_finalists_ranking.csv` and `csv/t_policy_ranking.csv`. The analyzer first removes dominated RD points, integrates the log-bitrate difference over the common PSNR interval, and then takes the equal-dataset geometric mean. The archived numerical summaries predate the prediction-axis sampling-boundary fix and must be regenerated before they are used in the paper.

The JSON top level is a task list. Each task requires `data_path_list`, `data_shape`, `rel_eb_list`, and `method_list`. Every path in `data_path_list` uses the same shape. Methods may be the strings `asz`, `sz3`, `qoz`, `zfp`, and `sperr`, or named method objects as shown below. Relative plan and summary paths are resolved from the project root. Set `cleanup_after_each_test` to `true` to remove that method's compressed and reconstructed files after its result has been recorded.

`sz3` uses the official `szcompressor/SZ3` master branch. `qoz` uses the independent `szcompressor/QoZ` 2.0 branch with the full QoZ 2.0 optimization level (`-q 4`). They are built and installed separately, but both link the project's `third_party/zstd` build so all three methods use the same Zstd version.

For SZ3, QoZ, ZFP, and SPERR, the launcher keeps the compressed stream until it has computed CR and BR from the actual file size. It independently recomputes PSNR and maximum absolute error from the reconstructed float32 data, checks the REL error bound, and then removes both files when `cleanup_after_each_test` is enabled. ZFP and SPERR tool-reported rounded statistics are not used.

ASZ is audited from its actual compressed stream and reconstructed float32 file in the same way. Its maximum-error acceptance threshold is `1.01*rel_eb*data_range` to allow up to 1% floating-point overshoot.

ASZ bitstreams intentionally do not embed experiment parameters such as `rel_eb`, the pivot/error/slope ratios, or `t_precision`. Compression and decompression must therefore use the same configuration; preserving that configuration is the user's responsibility.

```json
[
  {
    "data_path_list": ["/path/to/data.f32"],
    "data_shape": [100,500,500],
    "rel_eb_list": [0.001,0.0001],
    "method_list": [
      {
        "name": "asz_self_plan",
        "compressor": "asz",
        "pivot_eb_ratio": 0.05,
        "eb_ratio": 0.72,
        "slope_ratio": 0.54,
        "block_pivot_ratio": 4,
        "max_layer_num": 12,
        "full_predictor_search_layer_num": 4,
        "t_policy": "adaptive",
        "predictor_family": "cubic",
        "write_plan": "plans/{stem}.json"
      },
      {
        "name": "asz_shared_plan",
        "compressor": "asz",
        "read_plan": "plans/shared.json"
      },
      "sz3",
      "qoz"
    ],
    "cleanup_after_each_test": true
  }
]
```

The predictor-search-depth ablation is reproduced with `predictor_search_depth_tuning`; its archived equal-PSNR summary is `csv/predictor_search_depth_ranking.csv`. It must also be regenerated after changes to prediction-axis sampling or the shared RD analyzer.

The pivot-error-ratio finalists are reproduced with:

```bash
python t1_start_compressors.py pivot_eb_ratio_finalists --skip-build --no-csv
python analyze_layer_eb_screen.py --result-prefix pivot_eb_finalists_ --curve-baseline-method asz_p10 --output results/pivot_eb_finalists_ranking.csv
```

Across the six tuning datasets, `pivot_eb_ratio=0.05` reduces equal-PSNR bitrate by 1.26% relative to the former 0.10 default and is therefore the current fixed default.

A named method's `name` controls its CSV column name while `compressor` selects the executable. This allows several ASZ plan strategies in one task without overwriting results. `read_plan` applies a saved plan; omitting it generates a plan from that file. `write_plan` saves generated plans and must contain `{stem}` or `{name}` when a task has multiple data paths.

Named ASZ methods may override `pivot_eb_ratio`, `eb_ratio`, `slope_ratio`, `block_pivot_ratio`, `max_layer_num`, `full_predictor_search_layer_num`, and `t_policy`. Unspecified values use `0.05`, `0.76`, `0.54`, at most 12 generated layers, full prediction-axis/traversal-order search in the first four generated layers, and adaptive per-block `t` selection. `max_layer_num` and `full_predictor_search_layer_num` must be in `[1,63]`; generation may stop earlier when no valid predictor remains. `t_policy` may be `adaptive`, `fixed_4_16`, or `fixed_5_16`. Fixed policies encode one shared `t` value rather than per-block values. For `block_pivot_ratio`, the launcher passes `64` when `rel_eb<=1e-4` and `4` otherwise; an explicit value always overrides this rule. Both compression and decompression receive the selected values. The C++ executables themselves retain the default block ratio `4` for compatibility with existing compressed streams. When `predictor_family` is omitted, ASZ first generates the normal plan and compares cubic and quintic MSE on up to 200,000 samples along its final-layer direction, then applies the better family to the entire dataset. `predictor_family` may explicitly force `cubic` or `quintic` for controlled experiments. Version 2 plan files save the selected family; version 1 plans remain readable and default to cubic.

`ASZ_EXECUTABLE_DIRECTORY` may point the launcher at an isolated build directory containing `s1_compress` and `s1_decompress`. If it is unset, the launcher uses `install/bin` as before.


Optional task fields `comparison_baseline` and `summary_csv` generate a summary containing `CR_DROP_PERCENT=100*(baseline_CR-method_CR)/baseline_CR`.

A plan contains one entry per relative error bound. `layers` follows ASZ's prediction execution order. Prediction directions use dimension IDs 0, 1, and 2. Traversal orders are written explicitly from the outermost loop to the innermost loop.

```json
{
  "version": 1,
  "plans": [
    {
      "rel_eb": 0.0001,
      "layers": [
        {
          "prediction_direction": 0,
          "traversal_order": [1,2,0]
        }
      ]
    }
  ]
}
```
