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
        "max_layer_num": 14,
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

The slope-ratio finalists are reproduced with:

```bash
python t1_start_compressors.py slope_ratio_finalists --skip-build --no-csv
python analyze_layer_eb_screen.py --result-prefix slope_ratio_finalists_ --curve-baseline-method asz_s054 --output results/slope_ratio_finalists_ranking.csv
```

The two-error-bound screen favored 0.58, but the complete five-error-bound curves show that it increases equal-PSNR bitrate by 0.93% relative to 0.54. The fixed default therefore remains `slope_ratio=0.54`.

The error-bound-specific block-pivot-ratio grid is reproduced with:

```bash
sbatch run_block_pivot_ratio_grid.sbatch
python analyze_block_ratio_grid.py
```

The grid covers ratios 2, 4, 8, 16, 32, and 64 at every error bound on all six tuning datasets. The unrestricted optimum `(4,32,4,64,64)` reduces equal-PSNR bitrate by 0.41% relative to the current `(4,4,4,64,64)` rule, but is non-monotonic and its gain is not robust under leave-one-dataset-out checks. The current rule remains the best monotonic policy. Constraining adjacent ratios to increase by at most 2x selects `(4,8,16,32,64)`, which increases bitrate by 0.32%. The default therefore remains unchanged.

The corrected layer-count/error-ratio recheck is reproduced with `run_layer_eb_recheck.sbatch` followed by `run_layer_count_expansion.sbatch`. Analyze both result groups together with:

```bash
python analyze_layer_eb_screen.py --result-prefix layer_eb_recheck_ --result-prefix layer_count_expansion_ --output csv/layer_eb_recheck_ranking.csv
```

With `eb_ratio=0.76`, 14 layers reduce equal-PSNR bitrate by 1.03% relative to 12 layers. The curve then reverses: 16, 18, and 20 layers change bitrate by -0.77%, +0.98%, and +1.46%, respectively. At 12 layers, changing `eb_ratio` to 0.74 or 0.78 increases bitrate by 1.33% and 2.81%. The defaults are therefore `max_layer_num=14` and `eb_ratio=0.76`.

Because increasing the layer limit also increases the physical block size at a fixed block-pivot ratio, the layer result is decoupled and locally checked with `run_layer_block_decoupling.sbatch`, `run_layer_block_local_grid.sbatch`, and `run_layer_block_fine_expansion.sbatch`. Reconstruct the 21 complete policies with:

```bash
python analyze_layer_block_policy.py
```

The coarse ratio 3 is an interior optimum between 2 and 4. At `rel_eb<=1e-4`, ratios 40 through 128 form a nearly flat region; 96 is the interior minimum and 128 slightly reverses. The `(3,96)` policy reduces equal-PSNR bitrate by 1.26% relative to the former 12-layer `(4,64)` policy and by 0.045% relative to `(3,40)`. The launcher defaults are therefore 3 for `rel_eb>1e-4` and 96 otherwise.

The plan-generation spatial sampling stride is screened with `run_generate_config_sample_stride.sbatch` and refined with `run_generate_config_sample_stride_refinement.sbatch`. Analyze both groups with:

```bash
python analyze_generate_config_sample_stride.py
```

Stride 5 reduces equal-PSNR bitrate by 2.38% relative to the former stride 8 default. It improves five of the six datasets, changes CLDICE by +0.15%, and remains selected in every leave-one-dataset-out check. A same-node, three-repetition timing check at `rel_eb=1e-3` is reproduced with `run_generate_config_sample_stride_timing.sbatch` and `analyze_generate_config_sample_stride_time.py`; stride 5 increases plan-generation time by 8.22% and total plan-plus-compression time by 6.57%. The fixed default is therefore `generate_config_sample_stride=5`.

The `AB_map` target sampling count is screened with `run_h1_block_sampling_num.sbatch` and analyzed with:

```bash
python analyze_h1_block_sampling_num.py
```

The tested counts are 64, 128, 256, 512, and 1024. Count 512 reduces the six-dataset equal-PSNR bitrate by only 0.17% relative to 256, with regressions of 0.17%, 0.33%, and 1.88% on APS, Aramco, and CLDICE. Its apparent aggregate gain is driven by Isabel and LETKF and is not stable under leave-one-dataset-out selection. Counts 128 and 64 increase aggregate bitrate by 3.48% and 4.45%, respectively, including roughly 22% regressions on APS. The fixed default therefore remains `h1_block_sampling_num=256`.

The A/B statistics error-bound ratio is screened with the `stat_eb_ratio` configurations and finalized with the same-node `run_stat_eb_ratio_final.sbatch` comparison. Analyze the final comparison with:

```bash
python analyze_stat_eb_ratio_final.py
```

Across the six datasets, ratio 0.2 reduces equal-PSNR bitrate by 0.041% relative to 0.1, changes plan-generation time by +0.12%, and changes total plan-plus-compression time by -0.75%. Ratio 0.075 increases bitrate by 0.023% and total time by 2.33%. The fixed default is therefore `stat_eb_ratio=0.2`. When the estimated H1 difference is numerically zero or non-positive, or the resulting default slope is above the finite proxy 1e4, ASZ treats the local RD slope as effectively infinite and uses 1e4.

The adaptive cubic-coefficient range and precision are screened with `t_range_p32`, `t_range_extension`, `t_range_lower_extension`, and `t_precision_final`. The corresponding analysis scripts use equal-PSNR bitrate ratios and take their geometric mean across datasets. Empty sampling regions now fall back to linear interpolation (`t=4/16`) and are excluded from the selected-`t` distribution; an earlier range screen that used the first candidate as its implicit fallback was discarded. At precision 32, extending `[3/16,6/16]` to `[2/16,6/16]` reduces geometric-mean bitrate by 0.124%, and extending it to `[1/16,6/16]` reduces it by another 0.167%. Extending the lower bound to zero or the upper bound to `7/16` is worse. On the final range, precision 16 increases bitrate by 0.398% relative to precision 32. Precision 64 reduces it by only 0.030%, with the aggregate result driven by Isabel while regressing on CLDICE and LETKF, so precision 32 is retained as the more stable setting. The fixed defaults are therefore `t_min=1/16`, `t_max=6/16`, and `t_precision=32`, producing candidates `{2,3,...,12}/32`.

A named method's `name` controls its CSV column name while `compressor` selects the executable. This allows several ASZ plan strategies in one task without overwriting results. `read_plan` applies a saved plan; omitting it generates a plan from that file. `write_plan` saves generated plans and must contain `{stem}` or `{name}` when a task has multiple data paths.

Named ASZ methods may override `pivot_eb_ratio`, `eb_ratio`, `slope_ratio`, `block_pivot_ratio`, `max_layer_num`, `full_predictor_search_layer_num`, `generate_config_sample_stride`, `h1_block_sampling_num`, `stat_eb_ratio`, `t_precision`, `t_min`, `t_max`, and `t_policy`. Unspecified values use `0.05`, `0.76`, `0.54`, plan-generation sample stride 5, `AB_map` target sample count 256, statistics error-bound ratio 0.2, at most 14 generated layers, full prediction-axis/traversal-order search in the first four generated layers, and adaptive per-block `t` selection over `[1/16,6/16]` at precision 32. `max_layer_num` and `full_predictor_search_layer_num` must be in `[1,63]`; generation may stop earlier when no valid predictor remains. `generate_config_sample_stride` and `h1_block_sampling_num` must be positive integers and are used only by compression. `stat_eb_ratio` must be in `(0,1]` and is also used only by compression. `t_precision` must be a positive multiple of 16. `t_min` and `t_max` are compression-only, must be supplied together, must include 4/16 and 5/16, and must be exactly representable at the selected precision. `t_policy` may be `adaptive`, `fixed_4_16`, or `fixed_5_16`. Fixed policies encode one shared `t` value rather than per-block values. For `block_pivot_ratio`, the launcher passes `96` when `rel_eb<=1e-4` and `3` otherwise; an explicit value always overrides this rule. Controlled experiments may instead set `coarse_block_pivot_ratio` and `fine_block_pivot_ratio` together. Both compression and decompression receive the selected values. The C++ executables themselves retain the default block ratio `4` for compatibility with existing compressed streams. When `predictor_family` is omitted, ASZ first generates the normal plan and compares cubic and quintic MSE on up to 200,000 samples along its final-layer direction, then applies the better family to the entire dataset. `predictor_family` may explicitly force `cubic` or `quintic` for controlled experiments. Version 2 plan files save the selected family; version 1 plans remain readable and default to cubic.

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
