# ASZ

English | [中文](README_CN.md)

ASZ is a research prototype of a prediction-based, error-bounded lossy compressor for three-dimensional float32 scientific data. It extends the SZ compression pipeline with three round-wise tuning dimensions and with fast methods that tune them. This repository contains the ASZ implementation, launchers for the baseline compressors SZ3, QoZ, ZFP, and SPERR, and the scripts that produce the experiments and figures of the paper *ASZ: Error-Bounded Lossy Compression with Round-Wise Configurability and Efficient Tuning*.

## Features

- **Round-wise prediction axes.** Each coarse-to-fine interpolation round selects its own prediction axis, so an axis can be used several times in a row where the data are smoothest.
- **Variable-coefficient prediction.** The four-reference 1D4R predictor selects its coefficient `t` separately for every data block during compression. A fixed-coefficient six-reference 1D6R (quintic) predictor is selected for the whole file when it scores better.
- **Round-wise QB serialization orders.** Each round selects the fastest-varying axis used to serialize its quantization-bin (QB) indices before Huffman coding and Zstd.
- **Fast tuning.** Coefficients are compared with an H₁–PSNR proxy that is evaluated from one reusable joint distribution, and a reverse-greedy search builds the per-round configuration from the final round backward.
- **Plan reuse.** The selected stencil, axes, and QB orders form a configuration plan that can be saved and reused on related files, such as other time steps of the same field. Block coefficients are still selected for every file.

## Requirements

- Linux with a C++20 compiler, an AVX2/FMA-capable CPU, and CMake 3.10 or newer.
- Python 3 with NumPy for the experiment launcher, plus Matplotlib and Pillow for figures.
- h5py and hdf5plugin only for converting HDF5 inputs.
- Slurm for large experiments on a cluster (optional).
- TeX Live for the manuscript and for the LaTeX-rendered figures (optional).

## Getting the code

The baseline compressors and helper libraries are Git submodules:

```bash
git clone --recursive git@github.com:ZizheJian/asz.git
cd asz
```

For an existing clone:

```bash
git submodule update --init --recursive
```

Install the Python dependencies and the figure-layout helper:

```bash
python3 -m pip install numpy matplotlib pillow h5py hdf5plugin
python3 -m pip install --no-build-isolation -e third_party/paperfig
```

## Building

```bash
cmake -S c_codes -B build -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PWD/install"
cmake --build build --target s1_compress s1_decompress --parallel 4
cmake --install build
```

This installs `install/bin/s1_compress` and `install/bin/s1_decompress`. The experiment launcher builds ASZ and all baselines automatically unless `--skip-build` is given.

## Quick start

Inputs are raw float32 binary files without a header. The three dimensions are given from the slowest-varying (`DIM0`) to the fastest-varying (`DIM2`). The error bound is relative to the value range of the input.

```bash
install/bin/s1_compress -f -i data.f32 -z data.asz -o data.asz.out -3 100 500 500 -M REL 1e-3
install/bin/s1_decompress -f -z data.asz -o data.asz.out -3 100 500 500 -M REL 1e-3
```

`s1_compress` generates a configuration plan for the input and error bound, and then compresses the data. Run either program with `--help` for its usage line. Useful options include:

- `--predictor-family cubic|quintic`: force the 1D4R or 1D6R stencil for the whole file.
- `--predictor-plan PLAN`: skip plan generation and reuse a plan, given as a comma-separated list of per-round entries `cubic<axis>_<order>`, where `<axis>` is 0, 1, or 2 and `<order>` is one of `012`, `021`, or `120`.
- `--t-min` and `--t-max`: restrict the range of the 1D4R coefficient.

The remaining tuning options are documented in [configs/README.md](configs/README.md).

## Running experiments

`t1_start_compressors.py` runs ASZ and the baselines on a list of tasks defined in a JSON file under `configs/`:

```bash
python3 t1_start_compressors.py isabel_pf01
python3 t1_start_compressors.py configs/isabel_pf01.json --dry-run
python3 t1_start_compressors.py isabel_pf01 --skip-build --no-csv
```

`--dry-run` validates the configuration and the input files and prints the commands without running them. `--skip-build` reuses installed binaries, and `--no-csv` suppresses the per-input CSV files. The launcher measures the compressed size from the actual bitstream and computes PSNR and maximum error independently from the reconstructed file. A task can save ASZ plans with `write_plan` or reuse them with `read_plan`. [configs/README.md](configs/README.md) describes the JSON format, the ASZ parameters, and the maintained experiment groups.

## Reproducing the paper

The 18-field evaluation is defined by `configs/final_eighteen.json`, which lists the input files, their shapes, the five error bounds, and the result files of every compressor. The measured results of this evaluation are included under `results/final18/` and `results/final18_throughput/`, so the corresponding numbers and figures can be regenerated without the input data.

| Paper item | Script |
|---|---|
| Headline compression-ratio and runtime numbers | `analyze_final_evaluation.py` |
| Fig. 7–9 (stencil and coefficient comparisons) | `plot_predictor_rd.py` |
| Fig. 10 (QB serialization orders) | `plot_qb_order_rd.py` |
| Fig. 12 (coefficient-proxy validation) | `analyze_global_coefficient_selection.py` |
| Fig. 13 (rate–distortion on 18 fields) | `plot_final_rd.py` |
| Fig. 14 (total runtime) | `plot_final_runtime.py` |
| Fig. 15 (temporal plan reuse) | `plot_temporal_plan_reuse.py` |
| Fig. 16 (non-temporal plan reuse) | `plot_cross_array_plan_reuse.py` |

Figures other than Fig. 13 and Fig. 14 read measurement outputs under `results/`, which are produced by the launcher and the Slurm scripts in `scripts/`. The input datasets are not included in this repository. `convert_hdf5_to_f32.py` converts HDF5 inputs into the raw float32 format.

## Final-round prediction diagnostics

`s2_many_prediction` exhaustively simulates the final prediction round for every requested stencil, prediction axis, coefficient, and QB serialization order, using frozen original references. It reports the measured Huffman–Zstd bit rate, H₁, PSNR, prediction RMSE and MAE, and is the source of the stencil, coefficient, QB-order, and proxy studies in the paper. Build it against the Zstd library that the launcher builds for SZ3 and QoZ:

```bash
mkdir -p build/predictor_dimensionality
g++ -std=c++20 -O3 -march=native -I c_codes/asz_core c_codes/s2_many_prediction.cpp build/common_zstd_build/lib/libzstd.a -pthread -o build/predictor_dimensionality/s2_many_prediction
build/predictor_dimensionality/s2_many_prediction --help
```

The full form is `s2_many_prediction INPUT DIM0 DIM1 DIM2 OUTPUT_PREFIX FAMILY [EB0,EB1,... [SIX_GRID [TARGET_MODE]]]`, where `FAMILY` is `1d4r`, `2d4r`, `1d6r`, or `all`. `TARGET_MODE=common` evaluates all families, axes, and QB orders on the same checkerboard of targets. The CSVs use the paper's notation: `t` for 1D4R and 2D4R, and `a,b` for 1D6R, where `a` weights the references at ±5h, `b` weights those at ±3h, and 1/2−a−b weights those at ±h.

`summarize_prediction_sweep.py` selects the best candidates from these CSVs, for example:

```bash
python3 summarize_prediction_sweep.py PREFIX --family 1d4r --retain axis --output axis-curves.csv
python3 summarize_prediction_sweep.py PREFIX --family 1d6r --retain coefficient --output coefficient-curves.csv
python3 summarize_prediction_sweep.py PREFIX --family 1d4r --retain qb_order --output qb-order-curves.csv
```

The criteria `br-psnr`, `h1-psnr`, `rmse`, `mae`, and `psnr` are available through `--criterion`. Full-size sweeps are expensive and should run on a compute node.

## Repository layout

- `c_codes/`: ASZ compressor (`s1_compress.cpp`), decompressor (`s1_decompress.cpp`), final-round simulator (`s2_many_prediction.cpp`), and the core library in `asz_core/`.
- `configs/`: JSON experiment definitions and the 18-field evaluation manifest.
- `plans/`: saved ASZ plans, including those of the plan-reuse experiments.
- `scripts/`: Slurm batch scripts and experiment-preparation helpers.
- `csv/`: compact numerical summaries and tuning provenance.
- `results/`: experiment outputs. Only the 18-field results are tracked.
- `third_party/`: SZ3, QoZ, ZFP, SPERR, Zstd, and helper libraries as Git submodules.
- `t1_start_compressors.py`: experiment launcher. The other top-level Python files analyze results and plot the paper's figures.

## Tests

```bash
MPLCONFIGDIR=/tmp/asz-matplotlib python3 -m unittest discover -v
```

## Manuscript

The manuscript is maintained in a separate Overleaf project, cloned into `overleaf/`, which this repository ignores. Pull before editing and compile with `make -C overleaf pdf`. The Makefile stays outside the Overleaf project, so a fresh clone needs it copied from `../unsz/overleaf/Makefile`.

## Citation

If you use ASZ, please cite:

```bibtex
@unpublished{jian2026asz,
  title={{ASZ}: Error-Bounded Lossy Compression with Round-Wise Configurability and Efficient Tuning},
  author={Jian, Zizhe and Huang, Yafan and Yang, Zhuoxun and Di, Sheng and Jiang, Bo and Wu, Shixun and Huang, Jiajun and Zhao, Kai and Underwood, Robert and Chu, Miaoqi and Myint, Peco and Schwarz, Nicholas and Chen, Jessie and Jin, Sian and Rao, Vishwas and Chen, Zizhong and Cappello, Franck},
  note={Under review},
  year={2026}
}
```
