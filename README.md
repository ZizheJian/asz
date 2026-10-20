# ASZ

ASZ is a research prototype for error-bounded lossy compression of three-dimensional float32 scientific data. It uses multilevel interpolation, an offline-generated plan for prediction axes and traversal orders, and adaptive per-block interpolation coefficients.

The current workflow separates two costs:

- Offline preprocessing generates a plan for a field and relative error bound. A plan can be reused across compatible time steps of the same field.
- Online compression reuses that plan and selects the interpolation coefficient `t` independently for each block.

The repository also contains launchers for SZ3, QoZ, ZFP, and SPERR. SZ3 and QoZ are built separately but use the repository's common Zstd version.

## Repository layout

- `c_codes/`: ASZ compressor, decompressor, final-round simulator, and core library.
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

The installed executables are `install/bin/s1_compress` and `install/bin/s1_decompress`. These two programs and `s2_many_prediction` are the three retained C++ entry points. The remaining compressor logic lives in `c_codes/asz_core/`.

## Final-round prediction diagnostics

`s2_many_prediction` exhaustively simulates the final prediction round for every requested prediction stencil, prediction axis, coefficient, and QB serialization order. It uses frozen original references and reports measured Huffman--Zstd bit rate, first-order entropy, reconstruction PSNR, prediction RMSE, prediction MAE, sample count, and internal encoding time. These are final-round symbol-stream diagnostics rather than complete compressed files.

```bash
sweep_build=$(mktemp -d /tmp/asz-sweep-build.XXXXXX)
g++ -std=c++20 -O3 -march=native -I c_codes/asz_core c_codes/s2_many_prediction.cpp build/common_zstd_build/lib/libzstd.a -pthread -o "$sweep_build/s2_many_prediction"
"$sweep_build/s2_many_prediction" --help
```

For a full-size run, use `s2_many_prediction INPUT DIM0 DIM1 DIM2 OUTPUT_PREFIX FAMILY [EB0,EB1,...]`. `FAMILY` is `1d4r`, `2d4r`, `1d6r`, or `all`. The program refuses to replace existing output CSVs. Full-size exhaustive sweeps can be expensive and should run in an appropriate compute allocation.

`summarize_prediction_sweep.py` is the single selector for the resulting CSVs. It estimates one shared local RD tangent from all candidates in scope and selects candidates while retaining the requested configuration dimensions. Its output always carries the selected axis, coefficient, QB order, BR, H1, PSNR, RMSE, and MAE.

```bash
# Figs. 7--8: retain every prediction axis and optimize coefficient and QB order.
python3 summarize_prediction_sweep.py PREFIX --family 1d4r --retain axis --output axis-curves.csv

# Fig. 9: retain every coefficient and optimize prediction axis and QB order.
python3 summarize_prediction_sweep.py PREFIX --family 1d6r --retain coefficient --output coefficient-curves.csv

# Fig. 10: retain every QB order and optimize prediction axis and coefficient.
python3 summarize_prediction_sweep.py PREFIX --family 1d4r --retain qb_order --output qb-order-curves.csv

# Fig. 12(b,c): restrict axis and QB order,then retain every coefficient.
python3 summarize_prediction_sweep.py PREFIX --family 1d4r --axis 0 --qb-order 0 --retain coefficient --output fixed-axis-order.csv
```

The criteria `br-psnr`, `h1-psnr`, `rmse`, `mae`, and `psnr` are available through `--criterion`. The selector validates complete error-bound grids, records source hashes and slope endpoints, handles equal-rate and vertical references explicitly, and refuses to overwrite an existing output.

`analyze_global_coefficient_selection.py` regenerates the coefficient-proxy validation in Section V-D from the retained S2 measurements. It compares $H_1$--PSNR and the alternative proxy criteria with measured BR--PSNR and exports the validation figure and provenance.

Paper Figs. 2--4 embed 300 dpi RGB PNGs instead of vector PDFs to reduce vector drawing work in PDF viewers. `rasterize_paper_figures.py` follows MRCZ's `pdftoppm` conversion workflow, using the final IEEEtran column width of 252 TeX points (1046 pixels at 300 dpi) and preserving each source figure's aspect ratio. Original vector PDFs and 400 dpi plot previews remain unchanged. After regenerating any of these figures, refresh the paper PNGs before compiling:

```bash
module load anaconda/2024.02-py311
python -m unittest -v test_paper_rasterization
python rasterize_paper_figures.py
module load texlive/20200406
cd 新论文
latexmk -pdf -interaction=nonstopmode -halt-on-error -silent main.tex
```

## Current 17-field evaluation

The current evaluation selects 17 fields from 12 scientific datasets. Isabel, Miranda, LETKF, CESM, and Nyx each contribute two fields. The other seven datasets contribute one field each. The authoritative list, input paths, per-method result files, and timing overrides are stored in `configs/final_seventeen.json`.

Measurement batches remain split because the largest inputs need separate Slurm allocations:

- `final_eighteen_asz_refresh_small.json`: seven ASZ refresh tasks.
- `final_eighteen_asz_refresh_aps_kaz.json`: APS Kaz with its integer-data error-bound grid.
- `final_eighteen_asz_refresh_e017.json`: E017.
- `final_eighteen_asz_refresh_apsu004.json`: APSU004.
- `final_eighteen_third_row.json`: six additional datasets with ASZ, SZ3, and QoZ.
- `final_eighteen_nyx_baryon.json`: Nyx baryon density with all three methods.
- `apsu006.json`: APSU006 with all three methods.

The retained batches also contain superseded candidate fields. Plotting and analysis load only the manifest, so RD and runtime cannot silently use different field lists. The `asz_refresh` configurations intentionally run only ASZ and reuse previously generated baseline results; they are not complete baseline regeneration workflows. Miranda density is the only planned field whose complete five-point result still needs to be generated with `configs/final_seventeen_miranda_density.json`.

Generate the current figures after those results are present:

```bash
python3 plot_final_rd.py
python3 plot_final_runtime.py
python3 analyze_final_evaluation.py
```

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
