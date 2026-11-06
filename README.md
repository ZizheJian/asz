# ASZ

ASZ is a research prototype for error-bounded lossy compression of three-dimensional float32 scientific data. It uses multilevel interpolation, an offline-generated plan for prediction axes and quantization-bin (QB) serialization orders, and adaptive per-block interpolation coefficients.

The current workflow separates two costs:

- Offline preprocessing generates a plan and selects the dataset-wide 1D4R or 1D6R prediction stencil for a field and relative error bound. A plan can be reused across compatible time steps of the same field.
- Online compression reuses that plan and selects the interpolation coefficient `t` independently for each block.

The repository also contains launchers for SZ3, QoZ, ZFP, and SPERR. SZ3 and QoZ are built separately but use the repository's common Zstd version.

## Repository layout

- `c_codes/`: ASZ compressor, decompressor, final-round simulator, and core library.
- `configs/`: JSON experiment definitions and the final evaluation manifest.
- `plans/`: saved ASZ plans, including the Isabel plan-transfer experiment.
- `csv/`: retained numerical summaries and tuning provenance.
- `results/`: generated experiment output; ignored by Git.
- `third_party/`: Git submodules for baseline compressors and supporting libraries.
- `新论文/`: current ICDE manuscript and figures.
- `旧论文/`: earlier manuscripts retained for reference.

`t1_start_compressors.py` launches experiments. `evaluation_datasets.py` loads the shared evaluation manifest and result files, while `analyze_final_evaluation.py`, `plot_final_rd.py`, and `plot_final_runtime.py` produce the aggregate analysis and final figures. `paper_plot_layout.py` supplies shared plotting styles and layout helpers.

## Requirements

- Linux with a C++20 compiler, an AVX2/FMA-capable CPU, and CMake 3.10 or newer.
- Python 3 with NumPy.
- Matplotlib for figures.
- h5py and hdf5plugin only when converting compressed HDF5 data.
- Slurm for large experiments on Anvil. Historical batch scripts are available in Git history; submit the current Python launcher through an allocation appropriate to the input size.
- TeX Live and `latexmk` for the manuscript; Pillow and `pdftoppm` for optional figure rasterization.

Initialize the third-party repositories after cloning:

```bash
git submodule update --init --recursive
```

Install the shared publication-figure geometry helper in the active Python environment:

```bash
python3 -m pip install --no-build-isolation -e third_party/paperfig
```

Install the Python packages needed by the launchers, plots, and HDF5 converter:

```bash
python3 -m pip install numpy matplotlib pillow h5py hdf5plugin
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

`--dry-run` validates the JSON, checks input file existence and size, and prints commands without running the codecs. `--skip-build` reuses installed binaries. `--no-csv` prevents per-input CSV files while still allowing a configured summary CSV.

The launcher measures compressed size from the actual bitstream and independently computes PSNR, RMSE, and maximum error from the reconstructed float32 file. ASZ accepts maximum error up to `1.01*rel_eb*data_range`. Set `cleanup_after_each_test` to remove compressed and reconstructed files after their metrics have been recorded.

The default predictor-family selector simulates the final six rounds with both 1D4R and 1D6R on as many as eight stratified blocks. Sampled blocks cover at most 32,768 values and 2% of the input. The probe uses `block_pivot_ratio=3` above relative error bound `1e-4` and `block_pivot_ratio=4` at or below it, independently of the formal compression block geometry. It selects 1D6R only when its sampled `PSNR-default_slope*H1` score is strictly higher, so a tie selects 1D4R. The reported predictor-family selection time belongs to preprocessing and is excluded from `Compression time`.

See [configs/README.md](configs/README.md) for the JSON schema and plan examples.

## Building ASZ directly

```bash
cmake -S c_codes -B build -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PWD/install"
cmake --build build --target s1_compress s1_decompress --parallel 4
cmake --install build
```

The installed executables are `install/bin/s1_compress` and `install/bin/s1_decompress`. These two programs and `s2_many_prediction` are the three retained C++ entry points. The remaining compressor logic lives in `c_codes/asz_core/`.

## Final-round prediction diagnostics

`s2_many_prediction` exhaustively simulates the final prediction round for every requested prediction stencil, prediction axis, coefficient, and QB serialization order. It uses frozen original references and reports measured Huffman--Zstd bit rate, first-order entropy, reconstruction PSNR, prediction RMSE, prediction MAE, sample count, and internal encoding time. These are final-round symbol-stream diagnostics rather than complete compressed files.

The following standalone build uses `build/common_zstd_build/lib/libzstd.a`, which the experiment launcher builds for SZ3 and QoZ:

```bash
sweep_build=build/predictor_dimensionality
mkdir -p "$sweep_build"
g++ -std=c++20 -O3 -march=native -I c_codes/asz_core c_codes/s2_many_prediction.cpp build/common_zstd_build/lib/libzstd.a -pthread -o "$sweep_build/s2_many_prediction"
"$sweep_build/s2_many_prediction" --help
```

For a full-size run, use `s2_many_prediction INPUT DIM0 DIM1 DIM2 OUTPUT_PREFIX FAMILY [EB0,EB1,... [SIX_GRID [TARGET_MODE]]]`. `FAMILY` is `1d4r`, `2d4r`, `1d6r`, or `all`. `TARGET_MODE=common` evaluates every family, prediction direction, and QB order on one fixed checkerboard of targets after excluding five layers from every boundary. This mode makes cross-family comparisons use exactly the same data points and supports all 1D6R references. The sweep CSVs use the manuscript's coefficient notation: `t` for 1D4R and 2D4R, and `a,b` for 1D6R, where `a` weights each reference at $\pm5h$, `b` weights each reference at $\pm3h$, and $1/2-a-b$ weights each reference at $\pm h$. The fixed-quintic setting is therefore `a=3/256,b=-25/256`. Use `--require-uniform-samples` when summarizing these runs so that an inconsistent sweep fails instead of producing a figure. The program refuses to replace existing output CSVs. Full-size exhaustive sweeps can be expensive and should run in an appropriate compute allocation.

`summarize_prediction_sweep.py` is the single selector for the resulting CSVs. Its output always carries the selected axis, coefficient, QB order, BR, H1, PSNR, RMSE, and MAE. Summary CSVs store `t` for 1D4R and 2D4R and `a,b` for 1D6R; the reader converts historical 1D6R `t1,t2` files to `a=1/6-t1,b=1/6-t2`. Before selection, it verifies every expected axis, QB order, coefficient, and error bound. The recognized coefficient grids are the 13-candidate 1D4R and 2D4R grids and the 40-, 42-, and 52-candidate 1D6R grids.

```bash
# Retain every prediction axis and optimize coefficient and QB order.
python3 summarize_prediction_sweep.py PREFIX --family 1d4r --retain axis --output axis-curves.csv

# Retain every coefficient and optimize prediction axis and QB order.
python3 summarize_prediction_sweep.py PREFIX --family 1d6r --retain coefficient --output coefficient-curves.csv

# Retain every QB order and optimize prediction axis and coefficient.
python3 summarize_prediction_sweep.py PREFIX --family 1d4r --retain qb_order --output qb-order-curves.csv

# Restrict axis and QB order,then retain every coefficient.
python3 summarize_prediction_sweep.py PREFIX --family 1d4r --axis 0 --qb-order 0 --retain coefficient --output fixed-axis-order.csv

# Average BR and PSNR across both families at each measured error bound,use one neighboring-bound slope per error bound,and retain each axis or axis pair.
python3 summarize_prediction_sweep.py PREFIX --family 1d4r 2d4r --retain axis --selection shared-slope --target-bound 0.1 0.01 0.001 0.0001 0.00001 --output dimensionality-curves.csv
```

The default `joint` selection estimates a tangent from the candidates in scope. `two-stage` reproduces the historical coefficient-then-QB-order selector. `shared-slope` first averages the rate metric and PSNR over every candidate at each error bound,computes one slope from the neighboring averaged points,and applies that slope to every family,axis,coefficient,and QB order at the target error bound. The optional `--slope-span` uses explicitly measured multiplicative endpoints instead. The criteria `br-psnr`, `h1-psnr`, `rmse`, `mae`, and `psnr` are available through `--criterion`. The selector records source hashes and slope endpoints,handles equal-rate and vertical references explicitly,and refuses to overwrite an existing output.

`analyze_global_coefficient_selection.py` regenerates the manuscript's coefficient-proxy validation from the retained S2 measurements. It compares $H_1$--PSNR and the alternative proxy criteria with measured BR--PSNR and exports the validation figure and provenance. It requires `pdflatex` and an output directory that does not already exist, supplied through `--output`.

`plot_predictor_rd.py` generates the prediction-stencil and coefficient RD figures from retained sweep measurements. `plot_qb_order_rd.py` generates the QB-order comparison from three selected-candidate CSVs. Each QB order in those summaries independently selects its best prediction axis and coefficient at every error bound. Their default input paths refer to retained files under `results/`.

## Manuscript and figures

The current manuscript entry point is `新论文/main.tex`. Figures 7--10 are 300 dpi PNGs generated with `paperfig` at the IEEE single-column width, with a `sqrt(2):1` aspect ratio for every panel. Regenerate them from existing results with:

```bash
module load anaconda/2024.02-py311
python plot_predictor_rd.py fig7-final18 fig8-final18 fig9
python plot_qb_order_rd.py
```

Run the test suite in the same plotting environment:

```bash
module load anaconda/2024.02-py311
MPLCONFIGDIR=/tmp/asz-matplotlib python3 -m unittest discover -v
```

Compile the manuscript from the repository root:

```bash
module load texlive/20200406
cd 新论文
latexmk -pdf -interaction=nonstopmode -halt-on-error -silent main.tex
```

## Current 18-field evaluation

The evaluation uses QMCPACK Orbital 144; FLASH density at time step 22; APS Kaz; Isabel PRECIP and QGRAUP at time step 24; Miranda velocity-$x$ and velocity-$z$; RTM Small 0360; Aramco 1800; SCALE-LETKF PRES and T; CESM VD01 and UU at time step 31; APS CSSI L0471; Nyx baryon density and temperature at index 632; and APSU 004 and 006. `configs/final_eighteen.json` is the authoritative analysis manifest for input paths, shapes, error bounds, and result files.

Each field is measured at five relative error bounds with ASZ, SZ3, QoZ, ZFP, and SPERR. APS Kaz uses `0.1,0.05,0.02,0.01,0.008`. APS CSSI L0471 uses `0.1,0.01,0.001,0.0003,0.00013` to distribute its measured PSNRs more evenly. APSU 004 and 006 use the same list because both contain integer detector counts over the observed range `[0,4095]`; the lowest bound gives an absolute error bound of `0.53235`, just above half an integer interval, while `1e-4` would already be below that threshold. All other fields use `0.1,0.01,0.001,0.0001,0.00001`. Final result CSV files live under `results/final18/`; they must be regenerated after compressor changes.

When only ASZ changes, the baselines do not need to be rerun. `python3 scripts/prepare_final18_rd.py --prepare-rerun asz` writes ASZ-only configurations whose results go to `results/final18_asz/`, and `scripts/run_final18_rd.sbatch` runs them with the groups `asz_small`, `asz_medium`, `asz_nyx`, `asz_apsu004`, and the array group `asz_apsu006`. `python3 scripts/prepare_final18_rd.py --merge-rerun asz` then replaces the ASZ rows in `results/final18/` and recomputes `CR_DROP_PERCENT`. ASZ timing comes from these RD runs, so each group runs its tasks sequentially. The APSU timings vary by up to 1.8× between runs, even within one job, so each of ASZ, SZ3, and QoZ is timed twice on these fields: `--prepare-rerun timing` writes the groups `timing_apsu004` and `timing_apsu006` (an array with one error bound per task, each on a full 128-core node), and `--merge-rerun timing` checks that CR and PSNR are unchanged and keeps whichever of the existing row and the new row has the shorter total time.

The manifest has a different schema from runnable launcher configurations. Measurement batches should be split by input size so that the largest inputs receive separate Slurm allocations. The few historical focused configurations kept in `configs/` do not define the final field list, and removed screening configurations remain recoverable from Git history.

The final RD manifest is also the authoritative dataset pool for every measured figure in the paper. Predictor-family, coefficient-selection, plan-reuse, ablation, throughput, and runtime figures must use fields present in that manifest. After the 18-field manifest is frozen, regenerate earlier figures that still use superseded fields.

Generate the current figures and numerical summary from those results:

```bash
python3 plot_final_rd.py
python3 plot_final_runtime.py
python3 analyze_final_evaluation.py
```

The two final figures are 300 dpi PNG files under `新论文/figs/5/`: `rate-distortion-final-eighteen-log.png` and `time-breakdown-final-eighteen-vs-rel-eb.png`. The time figure reports preprocessing, compression, and decompression for ASZ and compression and decompression for SZ3, QoZ, ZFP, and SPERR at all five relative error bounds. Timings exclude input/output operations and post-run error verification. ASZ's compression stage includes its recorded data-range scan. The analysis writes `results/final_eighteen_analysis.csv`. All three scripts accept `--manifest` and `--result-directory` to select their inputs.

The RD summary integrates the log-bit-rate difference over the shared PSNR interval and reports ASZ's geometric-mean compression-ratio gain against each baseline separately. Runtime analysis defaults to the middle error bound of each field and includes ASZ preprocessing, compression, and decompression. Pass `--rel-eb` to `analyze_final_evaluation.py` to override this behavior with one common bound.

## Plans and compatibility

Plans are JSON documents indexed by relative error bound. Version 2 records one dataset-wide predictor family and the prediction axis and QB traversal order for every round. The loader remains compatible with version 1 plans. `write_plan` creates a version 2 plan; `read_plan` applies one.

Plan reuse targets compatible arrays with the same shape. The manuscript's temporal reuse experiment covers Isabel PRECIP time steps 01--48, RTM Small snapshots 0335--0385, and CESM UU time steps 00--62 at relative error bounds `1e-2,1e-3,1e-4`. The same scripts also run QMCPACK orbitals 0--287 (field `qmcpack_orbital`, sliced from `einspline_288_115_69_69.pre.f32` into `QMCPACK/orbitals/`) as a non-temporal sequence ordered by orbital index. For `m` files sharing one plan, `floor(T/m)` windows of `m` files are placed at the center of each sequence and the middle file of each window generates the plan. The leftover files at the two ends, with the extra file at the back, are excluded from the statistics for that `m`. Every file first generates its own plan, then every distinct representative--target pair is compressed once and shared by all `m` values. `analyze_temporal_plan_reuse.py` interpolates `log(BR)` over PSNR at the self-plan PSNR of `1e-3` and reports the relative compression ratio `BR_self/BR_reuse`, where 1 means no change. The average uses BR and NMSE averaged over the evaluated files at each error bound, and the minimum and maximum come from individual files. `plot_temporal_plan_reuse.py` plots the average and minimum against `m`, one panel per field.

```bash
python3 scripts/prepare_temporal_plan_reuse.py
sbatch --cpus-per-task=16 --time=00:20:00 scripts/run_temporal_plan_reuse.sbatch isabel_precip
sbatch --cpus-per-task=16 --time=00:20:00 scripts/run_temporal_plan_reuse.sbatch rtm_small
sbatch --cpus-per-task=32 --time=00:45:00 scripts/run_temporal_plan_reuse.sbatch cesm_uu 16
bash scripts/run_temporal_plan_reuse.sbatch qmcpack_orbital 4
python3 plot_temporal_plan_reuse.py
```

The optional second argument of the batch script sets the number of concurrent launcher processes; CESM UU uses half of the CPUs because one process reaches about 2 GB. The batch script skips configurations whose summary CSV already exists. `configs/aramco_plan_transfer.json` defines an earlier Aramco temporal check. `configs/isabel_wind_plan_transfer.json` defines reuse across the Isabel U, V, and W wind components, and `configs/apsu_plan_transfer.json` applies APSU 004 plans to APSU 006 on a full 128-core node. `plot_cross_array_plan_reuse.py` combines the QMCPACK orbital sequence, the wind components, and APSU 004 to 006 into the non-temporal reuse figure. The transferred plan fixes the dataset-wide predictor family and every round's axis and traversal order, while block coefficients remain adaptive for the target file. Transfer quality must be evaluated for each related group.

ASZ bitstreams intentionally do not embed `rel_eb` or the tuned compressor parameters. Compression and decompression must therefore use identical settings. Changing those settings without regenerating both sides can make a stream undecodable.

## Data format

ASZ currently expects a raw, contiguous, three-dimensional float32 array and a matching `data_shape`; every dimension must contain at least seven values. HDF5 inputs can be converted in chunks:

```bash
python3 convert_hdf5_to_f32.py input.h5 output.f32 --dataset /entry/data/data --shape 4096,1558,1813 --chunk-size 8
```

The source data catalog is `/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/data.json`. Paths in the checked-in configurations are specific to the Anvil project allocation.
