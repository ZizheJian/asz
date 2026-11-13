# ASZ

[English](README.md) | 中文

ASZ 是一个面向三维 float32 科学数据的预测式误差有界有损压缩器的研究原型。它在 SZ 压缩流程的基础上开放了三个逐 round 的调参维度，并提供了快速调参方法。本仓库包含 ASZ 的实现、基线压缩器 SZ3、QoZ、ZFP 和 SPERR 的启动脚本，以及生成论文 *ASZ: Error-Bounded Lossy Compression with Round-Wise Configurability and Efficient Tuning* 中实验和图表的脚本。

## 功能

- **逐 round 选择预测轴。** 由粗到细的每一轮插值都单独选择预测轴，因此可以在数据最平滑的方向上连续多轮预测。
- **可变系数预测。** 四参考点的 1D4R 预测器在压缩时为每个数据块单独选择系数 `t`。当系数固定的六参考点 1D6R（五次插值）预测器得分更高时，整个文件改用 1D6R。
- **逐 round 选择 QB 序列化顺序。** 每一轮在 Huffman 编码和 Zstd 之前，单独选择量化区间（QB）索引序列化时变化最快的轴。
- **快速调参。** 系数比较使用 H₁–PSNR proxy，所有候选系数的评估共用一个可复用的联合分布。逐 round 配置由 reverse-greedy 搜索从最后一轮倒序确定。
- **Plan 复用。** 选出的预测模板、各轮预测轴和 QB 顺序组成一份 configuration plan，可以保存下来并复用到相关文件上，例如同一物理场的其他时间步。复用时每个文件仍会单独选择块系数。

## 环境要求

- Linux、支持 C++20 的编译器、支持 AVX2/FMA 的 CPU，以及 CMake 3.10 或更新版本。
- 实验启动脚本需要 Python 3 和 NumPy，作图还需要 Matplotlib 和 Pillow。
- 仅在转换 HDF5 输入时需要 h5py 和 hdf5plugin。
- 在集群上跑大型实验时需要 Slurm（可选）。
- 编译论文和用 LaTeX 渲染的图需要 TeX Live（可选）。

## 获取代码

基线压缩器和辅助库以 Git 子模块的形式引入：

```bash
git clone --recursive git@github.com:ZizheJian/asz.git
cd asz
```

已有的克隆可以这样补全子模块：

```bash
git submodule update --init --recursive
```

安装 Python 依赖和作图布局辅助库：

```bash
python3 -m pip install numpy matplotlib pillow h5py hdf5plugin
python3 -m pip install --no-build-isolation -e third_party/paperfig
```

## 编译

```bash
cmake -S c_codes -B build -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PWD/install"
cmake --build build --target s1_compress s1_decompress --parallel 4
cmake --install build
```

编译后得到 `install/bin/s1_compress` 和 `install/bin/s1_decompress`。实验启动脚本会自动编译 ASZ 和所有基线，除非指定 `--skip-build`。

## 快速上手

输入是不带文件头的 float32 原始二进制文件。三个维度从变化最慢的 `DIM0` 到变化最快的 `DIM2` 依次给出。误差界是相对于输入数据值域的相对误差界。

```bash
install/bin/s1_compress -f -i data.f32 -z data.asz -o data.asz.out -3 100 500 500 -M REL 1e-3
install/bin/s1_decompress -f -z data.asz -o data.asz.out -3 100 500 500 -M REL 1e-3
```

`s1_compress` 先针对输入数据和误差界生成 configuration plan，然后压缩数据。两个程序都可以用 `--help` 查看用法。常用选项包括：

- `--predictor-family cubic|quintic`：整个文件强制使用 1D4R 或 1D6R 预测模板。
- `--predictor-plan PLAN`：跳过 plan 生成，直接复用给定的 plan。PLAN 是逗号分隔的逐 round 条目 `cubic<axis>_<order>`，其中 `<axis>` 取 0、1 或 2，`<order>` 取 `012`、`021` 或 `120`。
- `--t-min` 和 `--t-max`：限制 1D4R 系数的取值范围。

其余调参选项见 [configs/README.md](configs/README.md)。

## 运行实验

`t1_start_compressors.py` 按 `configs/` 下 JSON 文件定义的任务列表运行 ASZ 和各个基线：

```bash
python3 t1_start_compressors.py isabel_pf01
python3 t1_start_compressors.py isabel_pf01 --skip-build --no-csv
```

`--skip-build` 复用已安装的程序，`--no-csv` 不生成每个输入单独的 CSV 文件。启动脚本根据实际码流计算压缩后大小，并从重建文件独立计算 PSNR 和最大误差。任务可以用 `write_plan` 保存 ASZ 的 plan，也可以用 `read_plan` 复用已有的 plan。JSON 格式、ASZ 参数和现有的实验组见 [configs/README.md](configs/README.md)。

## 复现论文结果

18 个场的评测由 `configs/final_eighteen.json` 定义，其中列出了输入文件、数据形状、五个误差界以及各压缩器的结果文件。这组评测的测量结果已包含在 `results/final18/` 和 `results/final18_throughput/` 中，因此不需要输入数据也能重新生成相应的数字和图。

| 论文内容 | 脚本 |
|---|---|
| 摘要和正文中的压缩比与运行时间数字 | `analyze_final_evaluation.py` |
| Fig. 7–9（预测模板和系数比较） | `plot_predictor_rd.py` |
| Fig. 10（QB 序列化顺序） | `plot_qb_order_rd.py` |
| Fig. 12（系数 proxy 验证） | `analyze_global_coefficient_selection.py` |
| Fig. 13（18 个场的率失真曲线） | `plot_final_rd.py` |
| Fig. 14（总运行时间） | `plot_final_runtime.py` |
| Fig. 15（时间维度上的 plan 复用） | `plot_temporal_plan_reuse.py` |
| Fig. 16（非时间维度上的 plan 复用） | `plot_cross_array_plan_reuse.py` |

除 Fig. 13 和 Fig. 14 外，其余图需要读取 `results/` 下的测量结果，这些结果由启动脚本和 `scripts/` 中的 Slurm 脚本生成。本仓库不包含输入数据集。`convert_hdf5_to_f32.py` 可以把 HDF5 输入转换成 float32 原始格式。

## 最后一轮预测的诊断工具

`s2_many_prediction` 以冻结的原始值作为参考点，对最后一轮预测穷举所有指定的预测模板、预测轴、系数和 QB 序列化顺序。它输出实测的 Huffman–Zstd 码率、H₁、PSNR 以及预测误差的 RMSE 和 MAE，论文中关于预测模板、系数、QB 顺序和 proxy 的分析都来自这个工具。编译时链接启动脚本为 SZ3 和 QoZ 编译的 Zstd 库：

```bash
mkdir -p build/predictor_dimensionality
g++ -std=c++20 -O3 -march=native -I c_codes/asz_core c_codes/s2_many_prediction.cpp build/common_zstd_build/lib/libzstd.a -pthread -o build/predictor_dimensionality/s2_many_prediction
build/predictor_dimensionality/s2_many_prediction --help
```

完整用法是 `s2_many_prediction INPUT DIM0 DIM1 DIM2 OUTPUT_PREFIX FAMILY [EB0,EB1,... [SIX_GRID [TARGET_MODE]]]`，其中 `FAMILY` 取 `1d4r`、`2d4r`、`1d6r` 或 `all`。`TARGET_MODE=common` 让所有预测模板、预测轴和 QB 顺序在同一组棋盘格目标点上评估。CSV 沿用论文的记号：1D4R 和 2D4R 用 `t`，1D6R 用 `a,b`，其中 `a` 是 ±5h 处参考点的权重，`b` 是 ±3h 处参考点的权重，±h 处参考点的权重为 1/2−a−b。

`summarize_prediction_sweep.py` 从这些 CSV 中挑选最优候选，例如：

```bash
python3 summarize_prediction_sweep.py PREFIX --family 1d4r --retain axis --output axis-curves.csv
python3 summarize_prediction_sweep.py PREFIX --family 1d6r --retain coefficient --output coefficient-curves.csv
python3 summarize_prediction_sweep.py PREFIX --family 1d4r --retain qb_order --output qb-order-curves.csv
```

可以通过 `--criterion` 选择 `br-psnr`、`h1-psnr`、`rmse`、`mae` 或 `psnr` 作为评价标准。全尺寸的穷举开销很大，应在计算节点上运行。

## 目录结构

- `c_codes/`：ASZ 压缩器（`s1_compress.cpp`）、解压器（`s1_decompress.cpp`）、最后一轮模拟器（`s2_many_prediction.cpp`），以及 `asz_core/` 中的核心库。
- `configs/`：JSON 实验定义和 18 个场的评测清单。
- `plans/`：保存的 ASZ plan，包括 plan 复用实验用到的 plan。
- `scripts/`：Slurm 批处理脚本和实验准备脚本。
- `csv/`：精简的数值汇总和调参记录。
- `results/`：实验输出，只有 18 个场的结果纳入版本管理。
- `third_party/`：以 Git 子模块形式引入的 SZ3、QoZ、ZFP、SPERR、Zstd 和辅助库。
- `t1_start_compressors.py`：实验启动脚本。顶层的其他 Python 文件用于分析结果和绘制论文中的图。

## 测试

```bash
MPLCONFIGDIR=/tmp/asz-matplotlib python3 -m unittest discover -v
```

## 论文稿件

论文稿件放在单独的 Overleaf 项目中，克隆在 `overleaf/` 目录下，本仓库忽略这个目录。编辑前先 pull，用 `make -C overleaf pdf` 编译。Makefile 不放在 Overleaf 项目里，新克隆的副本需要从 `../unsz/overleaf/Makefile` 复制一份。

## 引用

如果使用了 ASZ，请引用：

```bibtex
@unpublished{jian2026asz,
  title={{ASZ}: Error-Bounded Lossy Compression with Round-Wise Configurability and Efficient Tuning},
  author={Jian, Zizhe and Huang, Yafan and Yang, Zhuoxun and Di, Sheng and Jiang, Bo and Wu, Shixun and Huang, Jiajun and Zhao, Kai and Underwood, Robert and Chu, Miaoqi and Myint, Peco and Schwarz, Nicholas and Chen, Jessie and Jin, Sian and Rao, Vishwas and Chen, Zizhong and Cappello, Franck},
  note={Under review},
  year={2026}
}
```
