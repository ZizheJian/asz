import argparse,csv,math
from pathlib import Path

datasets=("aps_kaz","aramco","cldice","isabel","letkf","videollava","e017","apsu")
rel_eb_by_dataset={
    "aps_kaz":(0.1,0.05,0.02,0.01,0.008),
    "aramco":(0.1,0.01,0.001,0.0001,0.00001),
    "cldice":(0.1,0.01,0.001,0.0001,0.00001),
    "isabel":(0.1,0.01,0.001,0.0001,0.00001),
    "letkf":(0.1,0.01,0.001,0.0001,0.00001),
    "videollava":(0.1,0.01,0.001,0.0001,0.00001),
    "e017":(0.1,0.01,0.001,0.0003,0.00013),
    "apsu":(0.1,0.01,0.001,0.0003,0.00013),
}
methods=("asz","sz3","qoz")
preferred_fields=("DATA_PATH","REL_EB","METHOD","CR","BR","PSNR","CR_DROP_PERCENT","MAX_ERROR","ABSOLUTE_EB","COMPRESSED_BYTES","GET_DEFAULT_SLOPE_TIME","GENERATE_CONFIG_TIME","PREDICTOR_FAMILY_SELECTION_TIME","COMPRESSION_TIME","DECOMPRESSION_TIME","DEFAULT_SLOPE","DEFAULT_SLOPE_MAX_INVALID_RATIO","DEFAULT_SLOPE_FALLBACK_USED","DEFAULT_SLOPE_FALLBACK_REASON","PREDICTOR_FAMILY","PREDICTOR_FAMILY_DIRECTION","PREDICTOR_FAMILY_SAMPLES","PREDICTOR_FAMILY_FALLBACK","CUBIC_MSE","QUINTIC_MSE","T_HISTOGRAM","T_FALLBACK_COUNT")

def canonical_rel_eb(dataset,value):
    matches=[target for target in rel_eb_by_dataset[dataset] if math.isclose(value,target,rel_tol=1e-12,abs_tol=0)]
    if len(matches)!=1:
        raise ValueError(f"未知rel_eb：{value}")
    return matches[0]

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        reader=csv.DictReader(input_file)
        if reader.fieldnames is None:
            raise ValueError(f"空CSV：{path}")
        return reader.fieldnames,list(reader)

def main():
    parser=argparse.ArgumentParser(description="用冻结版ASZ结果替换八数据旧ASZ结果，同时复用SZ3/QoZ baseline")
    parser.add_argument("--result-directory",type=Path,default=Path(__file__).resolve().parent/"results")
    arguments=parser.parse_args()

    for dataset in datasets:
        baseline_path=arguments.result_directory/f"final_eight_{dataset}.csv"
        refresh_path=arguments.result_directory/f"final_eight_asz_refresh_{dataset}.csv"
        output_path=arguments.result_directory/f"final_eight_frozen_{dataset}.csv"
        baseline_fields,baseline_rows=read_rows(baseline_path)
        refresh_fields,refresh_rows=read_rows(refresh_path)
        records={}
        for row in refresh_rows:
            if row.get("METHOD")!="asz":
                raise ValueError(f"刷新文件包含非ASZ结果：{refresh_path}")
            rel_eb=canonical_rel_eb(dataset,float(row["REL_EB"]))
            key=(rel_eb,"asz")
            if key in records:
                raise ValueError(f"刷新文件包含重复结果：{refresh_path},rel_eb={rel_eb:g}")
            records[key]=row
        for row in baseline_rows:
            method=row.get("METHOD")
            if method=="asz":
                continue
            if method not in ("sz3","qoz"):
                raise ValueError(f"baseline文件包含未知方法：{baseline_path},method={method}")
            rel_eb=canonical_rel_eb(dataset,float(row["REL_EB"]))
            key=(rel_eb,method)
            if key in records:
                raise ValueError(f"baseline文件包含重复结果：{baseline_path},rel_eb={rel_eb:g},method={method}")
            records[key]=row
        expected={(rel_eb,method) for rel_eb in rel_eb_by_dataset[dataset] for method in methods}
        if set(records)!=expected:
            raise ValueError(f"{dataset}结果不完整：missing={sorted(expected-set(records))},extra={sorted(set(records)-expected)}")
        all_fields=set(baseline_fields)|set(refresh_fields)
        fieldnames=[field for field in preferred_fields if field in all_fields]
        fieldnames.extend(sorted(all_fields-set(fieldnames)))
        temporary_path=output_path.with_name(output_path.name+".tmp")
        with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
            writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n",extrasaction="ignore")
            writer.writeheader()
            for key in sorted(records,key=lambda item:(-item[0],methods.index(item[1]))):
                writer.writerow(records[key])
        temporary_path.replace(output_path)
        print(f"写入冻结结果：{output_path}")

if __name__=="__main__":
    main()
