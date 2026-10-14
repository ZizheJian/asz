# ASZ

ASZ is a research prototype for error-bounded lossy compression of three-dimensional float32 scientific data. It uses multilevel interpolation, an offline-generated plan for prediction axes and traversal orders, and adaptive per-block interpolation coefficients.

The current workflow separates two costs:

- Offline preprocessing generates a plan for a field and relative error bound. A plan can be reused across compatible time steps of the same field.
- Online compression reuses that plan and selects the interpolation coefficient `t` independently for each block.

The repository also contains launchers for SZ3, QoZ, ZFP, and SPERR. SZ3 and QoZ are built separately but use the repository's common Zstd version.

## Repository layout

- `c_codes/`: ASZ compressor, decompressor, core library, and validation programs.
- `configs/`: JSON experiment definitions.
- `plans/`: saved ASZ plans, including the Isabel plan-transfer experiment.
- `csv/`: retained numerical summaries and tuning provenance.
- `results/`: generated experiment output; ignored by Git.
- `third_party/`: Git submodules for baseline compressors and supporting libraries.
- `新论文/`: current ICDE manuscript and figures.
- `旧论文/`: earlier manuscripts retained for reference.

## Requirements

- Linux with a C++20 compiler, an AVX2/FMA-capable CPU, and CMake 3.10 or newer.
- Python 3 with NumPy.
- Matplotlib for figures.
- h5py and hdf5plugin only when converting compressed HDF5 data.
- Slurm for the provided Anvil batch scripts.

Initialize the third-party repositories after cloning:

```bash
git submodule update --init --recursive
```

Install the Python packages needed by the launchers, plots, and HDF5 converter:

```bash
python3 -m pip install numpy matplotlib h5py hdf5plugin
```

## Running compressor experiments

`t1_start_compressors.py` reads a task list from `configs/`. A configuration can be addressed by its basename or by a path:

```bash
python3 t1_start_compressors.py isabel_pf01
python3 t1_start_compressors.py configs/isabel_pf01.json
```

Useful options are:

```bash
python3 t1_start_compressors.py isabel_pf01 --dry-run
python3 t1_start_compressors.py isabel_pf01 --skip-build
python3 t1_start_compressors.py isabel_pf01 --skip-build --no-csv
```

`--dry-run` validates the JSON and prints commands without running them. `--skip-build` reuses installed binaries. `--no-csv` prevents per-input CSV files while still allowing a configured summary CSV.

The launcher measures compressed size from the actual bitstream and independently computes PSNR, RMSE, and maximum error from the reconstructed float32 file. ASZ accepts maximum error up to `1.01*rel_eb*data_range`. Set `cleanup_after_each_test` to remove compressed and reconstructed files after their metrics have been recorded.

See [configs/README.md](configs/README.md) for the JSON schema and plan examples.

## Building ASZ directly

```bash
cmake -S c_codes -B build -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PWD/install"
cmake --build build --target s1_compress s1_decompress --parallel 4
cmake --install build
```

The installed executables are `install/bin/s1_compress` and `install/bin/s1_decompress`.

Validation programs `s2_many_prediction` through `s8_get_AB_distribution` are launched with `t2_start_other_c_codes.py`:

```bash
python3 t2_start_other_c_codes.py 2
python3 t2_start_other_c_codes.py s8_get_AB_distribution --skip-build
```

## Predictor-family diagnostics

The original `s2_many_prediction`/`s3_conclude_sp_result` experiment now accepts input paths, shapes, predictor families, and output paths as arguments. It retains the original coefficient grids, full target sets (`stride=1`), three traversal orders, and two-stage tangent-based selection. It uses frozen original references, not multilevel reconstructed references, and measures the encoded quantization-symbol stream rather than a complete compressor file. Different stencil orientations can have different target sets, as in the original experiment; traversal orders for a given stencil process the same targets.

```bash
legacy_build=$(mktemp -d /tmp/asz-legacy-build.XXXXXX)
g++ -std=c++20 -O3 -march=native -I c_codes/asz_core c_codes/s2_many_prediction.cpp build/common_zstd_build/lib/libzstd.a -pthread -o "$legacy_build/s2_many_prediction"
g++ -std=c++20 -O3 -march=native c_codes/s3_conclude_sp_result.cpp -o "$legacy_build/s3_conclude_sp_result"
ASZ_LEGACY_SWEEP="$legacy_build/s2_many_prediction" ASZ_LEGACY_CONCLUDE="$legacy_build/s3_conclude_sp_result" python3 -m unittest -v test_legacy_predictor_experiment.py
"$legacy_build/s2_many_prediction" --help
"$legacy_build/s3_conclude_sp_result" --help
```

For a full-size run, use `s2_many_prediction INPUT DIM0 DIM1 DIM2 OUTPUT_PREFIX FAMILY [EB0,EB1,...]`, followed by `s3_conclude_sp_result OUTPUT_PREFIX FAMILY OUTPUT.csv`. `FAMILY` is `1d4r`, `2d4r`, or `1d6r`; the sweep also accepts `all`. The default error bounds remain `1e-2,1e-3,1e-4,1e-5,1e-6`. Both programs refuse to replace existing output CSVs. Full-size exhaustive sweeps can be expensive and should be run in an appropriate compute allocation.

At each error bound, the original scoring first estimates a slope from the neighboring coefficient-averaged RD points for each stencil/order and maximizes `(PSNR-slope*BR)/sqrt(1+slope*slope)` over coefficients. It then averages the coefficient-selected points across orders, estimates a new neighboring slope, and uses the same score to select the order. Endpoints use one-sided differences. Summary CSVs retain actual measured BR/PSNR and now also record the selected coefficients, traversal order, both slopes, score kinds, and final score. At either selection stage, a zero bitrate span is handled by comparing PSNR only if all current candidates have exactly equal bit rates; its slope remains undefined and its score kind is recorded as `equal_rate_psnr`. Other zero spans and nonfinite metrics are rejected explicitly. The legacy 1D6R coefficient grid is unchanged; it is not the expanded grid used in the sampled diagnostic below.

`run_legacy_predictor_families.py` runs the 1D4R/2D4R comparison on Isabel Pf24, CESM CLDICE t31, and Aramco 1800. Its `benchmark` mode spatially downsamples small inputs solely to estimate runtime from the C++ program's internal timers; those RD values are not used in the results. `run_legacy_predictor_families.sbatch` runs the six dataset/family tasks concurrently on six cores of allocation `cis240669`, with a two-hour limit based on that preliminary estimate. Each job gets a fresh result directory containing source/binary hashes, raw CSVs, selected configurations, logs, and a three-panel figure of actual selected points without interpolated envelopes.

The legacy 1D4R diagnostic tests `t=0:1/32:12/32`; 2D4R tests `t=-6/24:1/24:6/24`. These grids describe diagnostic search potential, not the current online ASZ search cost. Current ASZ defaults use `t=2/32:1/32:12/32` for offline configuration search and `{2,8,9,10,11}/32` for online block tuning (`block_t_policy=peaks`); `block_t_policy=full` uses all eleven online.

The coefficient-selection validation used in paper Section III-C is reproducible with `analyze_global_coefficient_selection.py`, `run_coefficient_blockwise_validation.sbatch`, and `analyze_coefficient_blockwise_validation.py`. The global test covers six files, five error bounds, three directions, three QB orders, and eleven coefficients. Its 270 cases give 95.93% agreement between H1--PSNR and measured Huffman--Zstd QB-stream BR--PSNR, with mean/max normalized score losses of `7.379116e-5` and `0.006494917`. The complete-compression test freezes one plan per file/error-bound, forces 1D4R, includes coefficient metadata, and compares the two block-wise policies against the lower envelope of eleven globally fixed-coefficient RD curves. The five-candidate policy reduces equal-PSNR bitrate on four of six files but increases the six-file geometric mean by 4.10%; the full grid increases it by 5.40%. In particular, the five-candidate CESM T curve is 41.68% worse than the global envelope. These measurements do not reproduce the previously expected roughly 8% block-wise gain and must not be replaced by that estimate. Raw results, completion hashes, and final analysis are in `results/coefficient-proxy-global-20261012-complete` and `results/coefficient-blockwise-20261012/analysis-final`. An audit of the older six-file coefficient-policy experiment found that all 15 runs for each of Aramco, CLDICE, and LETKF PRES used fixed-quintic 1D6R, making half of its 90 runs ineligible for evaluating 1D4R coefficient tuning. A controlled reproduction with commit `45c856e`, one frozen plan, the complete legacy global grid, and only the three naturally cubic datasets gives equal-PSNR bitrate reductions of `0.808%` on APS Kaz, `5.378%` on Isabel Pf01, and `-0.294%` on VideoLLaVA, with a three-file geometric-mean reduction of `1.995%`. Its scripts, family audit, raw CSVs, and analysis are in `results/coefficient-blockwise-legacy-1d4r-20261012`.

`analyze_1d6r_coefficients.py` reuses the original full 1D6R sweep CSVs to study fixed coefficient pairs. Unlike `s3_conclude_sp_result`, it retains every `(t1,t2)` and independently selects the best of the nine direction/QB-order combinations at each error bound. One shared RD tangent per dataset/error bound is estimated from all coefficient/direction/order-averaged points; all choices use that same reference. Endpoints use one-sided differences, equal-rate zero-span cases compare PSNR, and vertical references compare bit rate. Other undefined or nonmonotone references are rejected by default. The explicit `--expand-flat-reference` option handles a fully coincident local averaged reference with unequal current candidate rates by increasing the error-bound index radius until the averaged endpoints differ. It changes no already-defined references, records the expanded endpoints in CSV/JSON, and still rejects fully flat datasets and nonmonotone expanded references. All nine raw files and the complete coefficient/error-bound grids are required; incomplete running jobs cannot silently produce partial curves.

```bash
python3 -m unittest -v test_1d6r_coefficients.py
python3 analyze_1d6r_coefficients.py --input results/predictor-family-4r6r-middle-21250842 --datasets aramco --output results/1d6r-coefficients-aramco-new
```

Multiple original raw directories can be supplied with `--input results/predictor-family-4r6r-middle-21250842 results/predictor-family-4r6r-supplement-21274865`. The output contains `selected.csv` (one measured point for every coefficient/error-bound pair, including selected axis, QB order, BR/PSNR, scores, and source CSV), `best-coefficients.csv` (the best coefficient at each error bound under the common score), and `report.json` (method and input hashes). A transition-grid dataset produces 42 coefficient curves and 210 selected points from 1,890 raw measurements. Original measurements are never changed, no compression is rerun, and existing analysis directories are never overwritten. Score losses are not bitrate percentages; the results remain single-round symbol-stream diagnostics, not full-compressor results. The completed supplement shows little overall 1D6R benefit on CLDICE and a more modest benefit on LETKF PRES than Aramco. With explicit flat-reference expansion, PRES's 0.1 endpoint uses averaged points at 0.1 and 0.001; every other reference is unchanged. A failed analysis does not create a partial output directory.

`plot_1d6r_coefficients.py` draws all retained fixed-pair curves without smoothing, point markers or coordinate jitter. Fixed quintic interpolation is red solid and all other coefficient pairs share the same light-gray thin solid style. The dashed black curve chooses the best coefficient independently at each measured error bound; it is not another fixed coefficient pair or a matched-quality envelope. The upper legend identifies all three styles as Fixed quintic, Best per error bound, and Other coefficients; these encodings are not repeated in the paper caption. Exports use a 3.5-inch single-column canvas and 8-point type. In Figs. 2--4, `rd_plot_layout.py` sets every plotting rectangle's physical width/height ratio to 1.618 and places the shared horizontal-axis title below the subfigure captions; the canvas height is computed from the panel dimensions and point-based text spacing. The detail view clips the same curves around the two finest quintic/best observations without changing selection. `--paper-placeholder` can add an explicitly unmeasured panel to an incomplete study; it is not used for the completed paper figure.

The completed third beneficial case is QMCPACK orbital 0 (`115x69x69`, no temporal dimension), selected for this illustrative study from existing raw-reference cubic/quintic MSE records, not from an unbiased prevalence survey. `results/predictor-family-4r6r-qmcpack-orbital0-20261011` contains its complete 2,475-observation full-target 1D4R/1D6R sweep using the same five bounds, transition grid, and shared targets. Internal sweep times were 7.415191 s for 1D4R and 62.849408 s for 1D6R. All 15 direction/bound summaries select exact quintic coefficients. `results/1d6r-coefficients-three-20261011` combines its raw measurements with Aramco and LETKF PRES, retaining 630 fixed-pair selected observations; quintic is best at all five bounds on Aramco and QMCPACK, and four of five on PRES. Paper Fig. 3 now uses Isabel/CESM T/LETKF QV above Aramco/LETKF PRES/QMCPACK; the completed CLDICE measurements remain intact but are not one of these six illustrative panels. Fig. 4 has three measured panels and no pending dataset.

```bash
python3 analyze_1d6r_coefficients.py --input results/predictor-family-4r6r-middle-21250842 results/predictor-family-4r6r-supplement-21274865 results/predictor-family-4r6r-qmcpack-orbital0-20261011 --datasets aramco letkf qmcpack --expand-flat-reference --output results/1d6r-coefficients-three-new
module load anaconda/2024.02-py311
python -m unittest -v test_1d6r_coefficient_plot
python plot_1d6r_coefficients.py --input results/1d6r-coefficients-three-new --output 新论文/revised-fig/1d6r-coefficients-middle
```

Paper Figs. 2--4 embed 300 dpi RGB PNGs instead of vector PDFs to reduce vector drawing work in PDF viewers. `rasterize_paper_figures.py` follows MRCZ's `pdftoppm` conversion workflow, using the final IEEEtran column width of 252 TeX points (1046 pixels at 300 dpi) and preserving each source figure's aspect ratio. Original vector PDFs and 400 dpi plot previews remain unchanged. After regenerating any of these figures, refresh the paper PNGs before compiling:

```bash
module load anaconda/2024.02-py311
python -m unittest -v test_paper_rasterization
python rasterize_paper_figures.py
module load texlive/20200406
cd 新论文
latexmk -pdf -interaction=nonstopmode -halt-on-error -silent main.tex
```

`c_codes/s9_predictor_family_sweep.cpp` and `analyze_predictor_families.py` generate three-panel comparisons of 1D4R versus 2D4R, 1D4R versus 1D6R, and fixed quintic versus grid-tuned six-reference prediction. These are sampled, single-round diagnostics with frozen original references, common target locations, and fixed row-major symbol order, not end-to-end ASZ compression results. The sweep includes exact quintic coefficients, a dense neighborhood around them, and all tested 1D4R candidates inside the 1D6R grid.

```bash
sweep_build=$(mktemp -d /tmp/asz-family-build.XXXXXX)
cmake -S c_codes -B "$sweep_build" -DCODE_NAME=s9_predictor_family_sweep -DCMAKE_BUILD_TYPE=Release
cmake --build "$sweep_build" --target s9_predictor_family_sweep --parallel 4
"$sweep_build/s9_predictor_family_sweep" --self-test
module load anaconda/2024.02-py311
python -m unittest -v test_predictor_families.py
python analyze_predictor_families.py --executable "$sweep_build/s9_predictor_family_sweep" --blocks 256 --output results/predictor-family-paper-refined --figures 新论文/revised-fig/predictor-family-refined
```

The sweep refuses to replace existing CSV files. Use a fresh output directory to rerun it, or `--skip-run` to regenerate figures from existing results. `provenance.json` records input paths, shapes, sampling settings, coefficient grids, and source hashes. Its historical family-selector audit is separate from the primary validation below: it compares raw MSE ordering with matched-PSNR bit rates from retained full-compressor curves, excludes quality points requiring extrapolation, leaves Kendall's tau undefined for MSE ties, and does not verify shared plans/settings. It no longer applies a runtime preference margin. Previously generated historical summaries are not rewritten automatically.

## Prediction-MSE family-selector validation

`run_family_mse_validation.py` tests whether the fixed-cubic/fixed-quintic prediction-MSE ordering predicts the final RD ordering of adaptive 1D4R versus fixed-quintic 1D6R. The first compression records the unpenalized MSE comparison (`--predictor-family-mse-ratio-threshold 1`); the second forces the opposite family with the first run's exact plan. Runtime configuration signatures must also match. Both complete bitstreams are decompressed, and BR/PSNR are independently measured from file sizes and reconstructed float32 values. Original inputs are read-only; temporary bitstreams/reconstructions are created and cleaned inside a new result directory. Production ASZ defaults are unchanged.

The specialized manifest `configs/family_mse_validation.json` selects all six Figure 3 inputs: Isabel Pf24, CESM T t31, LETKF QV (log10), Aramco 1800, LETKF PRES, and QMCPACK orbital 0. Each uses five relative error bounds from `1e-1` to `1e-5`. It is for this dedicated runner, not `t1_start_compressors.py`. Inspect the 60 planned full-compression runs before submitting the one-CPU,8-GB,15-minute Slurm job on `cis240669`:

```bash
module load anaconda/2024.02-py311
python run_family_mse_validation.py --dry-run --output results/family-mse-six-new
sbatch run_family_mse_validation.sbatch
```

The job creates `results/family-mse-six-JOBID`. Its `raw.csv` records both MSEs and each actual stencil's CR, BR, PSNR, compressed size, maximum error, and in-program compression/decompression times. Other outputs include paired plan/settings hashes, commands, logs, source/binary provenance, and `analysis/{cases.csv,summary.csv,report.json}`. Existing result directories are never overwritten. To analyze collected rows separately:

```bash
python analyze_family_mse.py --input results/family-mse-six-JOBID/raw.csv --output results/family-mse-analysis-new
ASZ_FAMILY_MSE_EXECUTABLES="$PWD/install/bin" python -m unittest -v test_family_mse.py
```

For each file/error-bound case, the primary analysis compares the two paths with the same tangent of their averaged actual BR--PSNR curve. Neighboring error bounds estimate the tangent; endpoints use one-sided differences, and a vertical tangent uses the limiting score `-BR`. It computes pairwise tau only within cases, never across files. MSE/RD ties (relative tolerance `1e-12`,zero absolute tolerance) and undefined/nonmonotone references are reported separately. Accuracy and mean/max RD-score regret use only the non-tied comparable cases; score regret is not a bitrate percentage. Retained historical CSVs can be audited only with explicit `--allow-unverified-plans`; such observations remain marked unverified and cannot stand in for new controlled measurements.

## Current 18-dataset evaluation

The current paper set is split because the largest inputs need separate Slurm allocations:

- `final_eighteen_asz_refresh_small.json`: seven ASZ refresh tasks.
- `final_eighteen_asz_refresh_aps_kaz.json`: APS Kaz with its integer-data error-bound grid.
- `final_eighteen_asz_refresh_e017.json`: E017.
- `final_eighteen_asz_refresh_apsu004.json`: APSU004.
- `final_eighteen_third_row.json`: six additional datasets with ASZ, SZ3, and QoZ.
- `final_eighteen_nyx_baryon.json`: Nyx baryon density with all three methods.
- `apsu006.json`: APSU006 with all three methods.

Together these files name 18 distinct inputs. The `asz_refresh` configurations intentionally run only ASZ and reuse previously generated baseline results; they are not a complete baseline regeneration workflow. `plot_final_eighteen_rd.py` and `plot_final_eighteen_runtime.py` expect the corresponding CSV files under `results/`.

Generate the current figures after those results are present:

```bash
python3 plot_final_eighteen_rd.py
python3 plot_final_eighteen_runtime.py
```

## Slurm jobs and temporary builds

The root-level `run_*.sbatch` files are Anvil-specific and currently use allocation `cis240669`. Large data paths point to `/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/`.

Batch jobs compile into a job-specific directory such as `/tmp/asz-final18-small-${SLURM_JOB_ID}/build`. This is disposable node-local storage used to avoid stale CMake caches and collisions between the main ASZ binaries. Source files remain in the repository and CSV results are written to `results/`.

## Plans and compatibility

Plans are JSON documents indexed by relative error bound. Each entry records the dataset-wide predictor family and the ordered layer predictors. `write_plan` creates a plan; `read_plan` applies one.

Plan reuse is intended for equal-shape time steps of the same physical field. The Isabel experiment validates this mode. The project does not claim that a plan transfers between unrelated datasets.

ASZ bitstreams intentionally do not embed `rel_eb` or the tuned compressor parameters. Compression and decompression must therefore use identical settings. Changing those settings without regenerating both sides can make a stream undecodable.

## Data format

ASZ currently expects a raw, contiguous, three-dimensional float32 array and a matching `data_shape`. HDF5 inputs can be converted in chunks:

```bash
python3 convert_hdf5_to_f32.py input.h5 output.f32 --dataset /entry/data/data --shape 4096,1558,1813 --chunk-size 8
```

The data catalog lives with the tensor data rather than in this source repository. Paths in the checked-in configurations are therefore specific to the Anvil project allocation.
