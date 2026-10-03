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

The slope-ratio recheck under the current parameter stack is reproduced with:

```bash
sbatch run_slope_ratio_recheck.sbatch
python analyze_layer_eb_screen.py --result-prefix slope_ratio_recheck_ --curve-baseline-method asz_s054 --output csv/slope_ratio_recheck_ranking.csv
```

The complete grid covers 0.50, 0.52, 0.54, 0.56, and 0.58 at all five error bounds. Ratio 0.56 is only 0.062% ahead of 0.54 in the six-dataset geometric mean and regresses LETKF by 0.656%; ratio 0.58 regresses the aggregate by 1.671%. The more stable fixed default therefore remains `slope_ratio=0.54`.

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

Across the six datasets, ratio 0.2 reduces equal-PSNR bitrate by 0.041% relative to 0.1, changes plan-generation time by +0.12%, and changes total plan-plus-compression time by -0.75%. Ratio 0.075 increases bitrate by 0.023% and total time by 2.33%. The fixed default is therefore `stat_eb_ratio=0.2`.

For each of the two slope-estimation error-bound endpoints, ASZ measures the fraction of candidate direction/coefficient tests with zero estimated MSE. The failure policy uses the less valid endpoint, equivalently the maximum of the two invalid fractions. If that fraction reaches `default_slope_invalid_ratio_threshold`, or if the estimated H1/PSNR differences cannot form a positive slope, ASZ uses `default_slope_fallback`. A finite positive estimated slope is always used directly without clipping. The threshold and fallback are tuned by the reproducible experiments below.

The threshold screen tests 25%, 50%, 75%, and 100%. The 75% and 100% policies are identical on all 30 points. Lowering the threshold to 25% or 50% unnecessarily changes three CLDICE points and increases the six-dataset geometric-mean bitrate by 0.016%, so the fixed threshold remains 100%. At that threshold, six of the 30 points require fallback. Changing the fallback from 10,000 to 1,000 reduces geometric-mean bitrate by 2.801%. The gain is driven by a 15.81% LETKF reduction, while APS, Aramco, and CLDICE regress by only 0.070%, 0.038%, and 0.052%; Isabel and VideoLLaVA are unchanged.

A refinement over 500, 750, 1,000, 1,500, 2,000, 3,000, and 5,000 places 750 only 0.019% ahead of 1,000, but that marginal result is driven by CLDICE and reverses when CLDICE is excluded. The more stable fixed fallback is therefore 1,000. A separate no-clipping check covers the APS point whose valid estimated slope is 11,814.72; every fallback setting produces the same plan, BR, and PSNR at that point, confirming that fallback affects only invalid estimates.

The symmetric error-bound span used to estimate the default slope is screened with `run_default_slope_eb_span.sbatch` and refined with `run_default_slope_eb_span_refinement.sbatch`. A span `s` uses the two endpoints `abs_eb/s` and `abs_eb*s`. The complete grid contains 1.2, 1.3, 1.5, 1.75, 2, 3, and 4. Span 1.2 has the lowest six-dataset geometric-mean bitrate at 0.172% below the former span 2, but its result is driven by Isabel and it regresses LETKF by 0.253%. Span 1.5 is 0.158% below span 2, improves APS and Isabel, and changes each of the other four datasets by at most 0.006%. The fixed default is therefore the more stable `default_slope_eb_span=1.5`.

The dataset-wide cubic/quintic decision sample limit is screened with `run_predictor_family_sample_limit.sbatch` and analyzed with:

```bash
python analyze_predictor_family_sample_limit.py
```

The tested limits are 10,000, 50,000, 100,000, and 200,000. All four limits make the same decision at all 30 dataset/error-bound points, selecting cubic 15 times and quintic 15 times, and therefore produce identical compressed sizes. Reducing the limit from 200,000 to 10,000 reduces the internally measured family-selection time by 92.9%, from 14.95 ms to 1.01 ms on average. This phase is too small for its change to be distinguished from noise in the total plan-plus-compression time. The fixed default is therefore `predictor_family_sample_limit=10000`.

The cubic/quintic RD comparison is reproduced with `run_predictor_family_rd_extremes.sbatch` and `analyze_predictor_family_rd_extremes.py`. MSE-ratio threshold 0 forces cubic and 1e6 forces quintic while retaining the normal sampling path. On all six datasets, the sampled MSE ratio and the complete equal-PSNR RD curves select the same family. The nearest opposing cases are CLDICE, whose largest ratio is 0.948264 and whose quintic curve reduces bitrate by 19.97%, and VideoLLaVA, whose ratio is exactly 1 and whose cubic curve reduces bitrate by 4.84% relative to quintic. A fixed threshold of 0.97 places a simple margin between them: quintic must reduce sampled MSE by at least 3%.

The completed adaptive cubic-coefficient screen selected `t_min=1/16`, `t_max=6/16`, and `t_precision=32`, producing candidates `{2,3,...,12}/32`. Extending the lower bound to zero or the upper bound to `7/16` was worse; precision 16 increased bitrate by 0.398% relative to precision 32, while precision 64 improved it by only 0.030% and was less stable across datasets.

A named method's `name` controls its CSV column name while `compressor` selects the executable. This allows several ASZ plan strategies in one task without overwriting results. `read_plan` applies a saved plan; omitting it generates a plan from that file. `write_plan` saves generated plans and must contain `{stem}` or `{name}` when a task has multiple data paths.

Named ASZ methods may override `pivot_eb_ratio`, `eb_ratio`, `slope_ratio`, `block_pivot_ratio`, `max_layer_num`, `full_predictor_search_layer_num`, `generate_config_sample_stride`, `h1_block_sampling_num`, `stat_eb_ratio`, `predictor_family_sample_limit`, `predictor_family_mse_ratio_threshold`, `default_slope_invalid_ratio_threshold`, `default_slope_fallback`, `default_slope_eb_span`, `t_precision`, `t_min`, `t_max`, `t_policy`, and `block_t_policy`. Unspecified values use `0.05`, `0.76`, `0.54`, plan-generation sample stride 5, `AB_map` target sample count 256, statistics error-bound ratio 0.2, predictor-family sample limit 10,000, predictor-family MSE-ratio threshold 0.97, default-slope invalid-ratio threshold 1.0, default-slope fallback 1,000, default-slope error-bound span 1.5, at most 14 generated layers, full prediction-axis/traversal-order search in the first four generated layers, and adaptive per-block `t` selection at precision 32. Plan generation and default-slope estimation use all eleven candidates in `[1/16,6/16]`; block compression uses the five fixed peaks `{1/16,1/4,9/32,5/16,11/32}` by default. `block_t_policy` may be `peaks` or `full`; `full` is retained for controlled comparisons. `max_layer_num` and `full_predictor_search_layer_num` must be in `[1,63]`; generation may stop earlier when no valid predictor remains. `generate_config_sample_stride`, `h1_block_sampling_num`, and `predictor_family_sample_limit` must be positive integers and are used only by compression. `predictor_family_mse_ratio_threshold` must be nonnegative; quintic is selected exactly when its sampled MSE is less than cubic MSE multiplied by this threshold, so zero forces cubic and a sufficiently large value forces quintic. `stat_eb_ratio` and `default_slope_invalid_ratio_threshold` must be in `(0,1]`; `default_slope_fallback` must be positive and `default_slope_eb_span` must be greater than 1. These sampling and slope-selection controls are compression-only. `t_precision` must be a positive multiple of 16. `t_min` and `t_max` are compression-only, must be supplied together, must include 4/16 and 5/16, and must be exactly representable at the selected precision. `t_policy` may be `adaptive`, `fixed_4_16`, or `fixed_5_16`. Fixed policies encode one shared `t` value rather than per-block values. For `block_pivot_ratio`, the launcher passes `96` when `rel_eb<=1e-4` and `3` otherwise; an explicit value always overrides this rule. Controlled experiments may instead set `coarse_block_pivot_ratio` and `fine_block_pivot_ratio` together. Both compression and decompression receive the selected values. The C++ executables themselves retain the default block ratio `4` for compatibility with existing compressed streams. When `predictor_family` is omitted, ASZ first generates the normal plan and compares cubic and quintic MSE on up to 10,000 samples along its final-layer direction, then applies the family selected by the MSE-ratio threshold. `predictor_family` may explicitly force `cubic` or `quintic` for compatibility with saved plans. Version 2 plan files save the selected family; version 1 plans remain readable and default to cubic.

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
