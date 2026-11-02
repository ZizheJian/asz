import csv
import json
import math
from pathlib import Path

project_root=Path(__file__).resolve().parent
default_manifest=project_root/"configs/final_eighteen.json"
rd_methods=("asz","sz3","qoz","zfp","sperr")
throughput_methods=rd_methods
runtime_methods=("asz","sz3","qoz")
timing_methods=throughput_methods
methods=rd_methods
styles={
    "asz":{"label":"ASZ","color":"#000000","linestyle":"-","marker":"o"},
    "sz3":{"label":"SZ3","color":"#d62728","linestyle":"--","marker":"s"},
    "qoz":{"label":"QoZ","color":"#e6a700","linestyle":"-.","marker":"^"},
    "zfp":{"label":"ZFP","color":"#1f77b4","linestyle":":","marker":"D"},
    "sperr":{"label":"SPERR","color":"#2ca02c","linestyle":"--","marker":"v"},
}


def load_datasets(path=default_manifest):
    with open(path,encoding="utf-8") as input_file:
        datasets=json.load(input_file)
    if len(datasets)!=18:
        raise ValueError(f"evaluation manifest must contain 18 fields,found {len(datasets)}")
    titles=[dataset["title"] for dataset in datasets]
    if len(set(titles))!=len(titles):
        raise ValueError("evaluation manifest contains duplicate titles")
    for dataset in datasets:
        missing=set(rd_methods)-set(dataset["results"])
        if missing:
            raise ValueError(f"{dataset['title']} is missing result files for {','.join(sorted(missing))}")
        bounds=dataset.get("rel_eb_list",())
        if len(bounds)!=5:
            raise ValueError(f"{dataset['title']} must define five relative error bounds")
        if len(set(bounds))!=len(bounds) or any(not isinstance(bound,(int,float)) or not math.isfinite(bound) or bound<=0 for bound in bounds):
            raise ValueError(f"{dataset['title']} must define five distinct positive finite relative error bounds")
        shape=dataset.get("shape",())
        if len(shape)!=3 or any(not isinstance(size,int) or size<=0 for size in shape):
            raise ValueError(f"{dataset['title']} must define three positive integer dimensions")
    return datasets


def dataset_size(dataset):
    if "size_bytes" in dataset:
        return int(dataset["size_bytes"])
    return Path(dataset["data_path"]).stat().st_size


def format_size(byte_count):
    units=("B","KiB","MiB","GiB")
    value=float(byte_count)
    for unit in units:
        if value<1024 or unit==units[-1]:
            return f"{value:.2f} {unit}"
        value/=1024
    raise AssertionError("unreachable")


def result_filename(dataset,method,timing=False):
    if timing and method in dataset.get("timing_results",{}):
        return dataset["timing_results"][method]
    return dataset["results"][method]


def read_method_rows(result_directory,dataset,method,timing=False,expected=5):
    path=result_directory/result_filename(dataset,method,timing)
    if not path.exists():
        raise FileNotFoundError(f"missing {method} results for {dataset['title']}: {path}")
    with open(path,newline="",encoding="utf-8") as input_file:
        reader=csv.DictReader(input_file)
        fieldnames=set(reader.fieldnames or ())
        rows=[row for row in reader if row["METHOD"]==method]
    match_path=dataset.get("result_data_path",dataset.get("data_path"))
    if match_path is not None:
        if "DATA_PATH" not in fieldnames:
            raise ValueError(f"{path} cannot select {dataset['title']} because it has no DATA_PATH column")
        rows=[row for row in rows if row["DATA_PATH"]==match_path]
    elif "DATA_PATH" in fieldnames and len({row["DATA_PATH"] for row in rows})>1:
        raise ValueError(f"{path} contains multiple inputs but {dataset['title']} has no result_data_path")
    if len(rows)!=expected:
        raise ValueError(f"{path} must contain {expected} {method} points for {dataset['title']},found {len(rows)}")
    actual_bounds=[float(row["REL_EB"]) for row in rows]
    if len(set(actual_bounds))!=len(actual_bounds):
        raise ValueError(f"{path} contains duplicate {method} relative error bounds for {dataset['title']}")
    expected_bounds=dataset.get("rel_eb_list")
    if expected_bounds is not None:
        unmatched=list(actual_bounds)
        for expected_bound in expected_bounds:
            matches=[bound for bound in unmatched if math.isclose(bound,expected_bound,rel_tol=1e-12,abs_tol=0)]
            if len(matches)!=1:
                raise ValueError(f"{path} {method} relative error bounds do not match {dataset['title']}")
            unmatched.remove(matches[0])
        if unmatched:
            raise ValueError(f"{path} {method} relative error bounds do not match {dataset['title']}")
    return rows


def read_curves(result_directory,dataset):
    return {method:sorted((float(row["BR"]),float(row["PSNR"])) for row in read_method_rows(result_directory,dataset,method)) for method in rd_methods}


def load_timings(result_directory,dataset,selected_methods=timing_methods):
    rows={method:read_method_rows(result_directory,dataset,method,timing=True) for method in selected_methods}
    for method,method_rows in rows.items():
        for row in method_rows:
            if not row.get("COMPRESSION_TIME") or not row.get("DECOMPRESSION_TIME"):
                raise ValueError(f"{dataset['title']} {method} is missing compression or decompression time")
    return rows


def preprocessing_time(row):
    if row.get("PREPROCESSING_TIME"):
        return float(row["PREPROCESSING_TIME"])
    return sum(float(row.get(key) or 0) for key in ("GET_DEFAULT_SLOPE_TIME","GENERATE_CONFIG_TIME","PREDICTOR_FAMILY_SELECTION_TIME"))


# ASZ输出的Compression time已经包含数据范围扫描，DATA_RANGE_TIME只是其中的一部分
def compression_time(row):
    return float(row["COMPRESSION_TIME"])


def row_at_rel_eb(rows,rel_eb):
    matches=[row for row in rows if math.isclose(float(row["REL_EB"]),rel_eb,rel_tol=1e-12,abs_tol=0)]
    if len(matches)!=1:
        raise ValueError(f"rel_eb={rel_eb:g} must have one timing point,found {len(matches)}")
    return matches[0]
