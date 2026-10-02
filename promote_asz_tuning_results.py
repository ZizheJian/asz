import argparse,csv,json,math,re
from datetime import date
from pathlib import Path

from analyze_layer_eb_screen import geometric_mean,interpolate_log_br,pareto_curve

project_root=Path(__file__).resolve().parent
dataset_suffixes={
    "APS_Kaz":"aps_kaz.csv",
    "Aramco":"aramco.csv",
    "CLDICE":"cldice.csv",
    "Isabel_Pf01":"isabel.csv",
    "LETKF_PRES":"letkf.csv",
    "VideoLLaVA":"videollava.csv",
}

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def curve_contains(curve,psnr):
    return curve[0][0]<=psnr<=curve[-1][0]

def envelope_log_br(curves,psnr):
    return min(interpolate_log_br(curve,psnr) for curve in curves if curve_contains(curve,psnr))

def compare_to_envelope(candidate,baselines):
    candidate=pareto_curve(candidate)
    baselines=[pareto_curve(curve) for curve in baselines]
    common_left=max(candidate[0][0],min(curve[0][0] for curve in baselines))
    common_right=min(candidate[-1][0],max(curve[-1][0] for curve in baselines))
    if common_left>=common_right:
        raise ValueError("ASZ曲线和baseline envelope没有共同PSNR区间")
    raw_knots=sorted({common_left,common_right,*[psnr for psnr,_ in candidate if common_left<psnr<common_right],*[psnr for curve in baselines for psnr,_ in curve if common_left<psnr<common_right]})
    crossings=[]
    for left,right in zip(raw_knots,raw_knots[1:]):
        active=[curve for curve in baselines if curve_contains(curve,left) and curve_contains(curve,right)]
        if len(active)!=2:
            continue
        left_diff=interpolate_log_br(active[0],left)-interpolate_log_br(active[1],left)
        right_diff=interpolate_log_br(active[0],right)-interpolate_log_br(active[1],right)
        if left_diff*right_diff<0:
            crossings.append(left+(right-left)*(-left_diff)/(right_diff-left_diff))
    knots=sorted({*raw_knots,*crossings})
    log_ratio_integral=0
    winning_length=0
    for left,right in zip(knots,knots[1:]):
        left_diff=interpolate_log_br(candidate,left)-envelope_log_br(baselines,left)
        right_diff=interpolate_log_br(candidate,right)-envelope_log_br(baselines,right)
        length=right-left
        log_ratio_integral+=length*(left_diff+right_diff)/2
        if left_diff<0 and right_diff<0:
            winning_length+=length
        elif (left_diff<0)!=(right_diff<0):
            crossing=left+length*(-left_diff)/(right_diff-left_diff)
            winning_length+=(crossing-left) if left_diff<0 else (right-crossing)
    interval=common_right-common_left
    return math.exp(log_ratio_integral/interval),winning_length/interval,(common_left,common_right)

def write_csv(path,rows,fieldnames):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=path.with_name(path.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary_path.replace(path)

def encode_json(value):
    return json.dumps(value,separators=(",",":"),ensure_ascii=False)

def write_metadata(path,metadata):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=path.with_name(path.name+".tmp")
    lines=[
        "{",
        f'  "generated_at":{encode_json(metadata["generated_at"])},',
        f'  "datasets":{encode_json(metadata["datasets"])},',
        f'  "rel_eb_list":{encode_json(metadata["rel_eb_list"])},',
        f'  "point_count":{encode_json(metadata["point_count"])},',
        '  "metrics":{',
    ]
    metric_items=list(metadata["metrics"].items())
    for index,(key,value) in enumerate(metric_items):
        lines.append(f'    {encode_json(key)}:{encode_json(value)}{"," if index+1<len(metric_items) else ""}')
    lines.extend(['  },','  "comparison":{'])
    comparison_items=[(key,value) for key,value in metadata["comparison"].items() if key!="per_dataset"]
    for key,value in comparison_items:
        lines.append(f'    {encode_json(key)}:{encode_json(value)},')
    lines.append('    "per_dataset":[')
    dataset_statistics=metadata["comparison"]["per_dataset"]
    for index,value in enumerate(dataset_statistics):
        lines.append(f'      {encode_json(value)}{"," if index+1<len(dataset_statistics) else ""}')
    lines.extend([
        "    ]",
        "  },",
        f'  "baseline_version_metadata":{encode_json(metadata["baseline_version_metadata"])}',
        "}",
    ])
    with open(temporary_path,"w",encoding="utf-8") as output_file:
        output_file.write("\n".join(lines)+"\n")
    temporary_path.replace(path)

def main():
    parser=argparse.ArgumentParser(description="将选定ASZ实验曲线提升为canonical tuning results")
    parser.add_argument("--result-prefix",required=True)
    parser.add_argument("--method",required=True)
    parser.add_argument("--fine-result-prefix")
    parser.add_argument("--fine-method")
    parser.add_argument("--fine-max-rel-eb",type=float,default=1e-4)
    parser.add_argument("--coarse-block-pivot-ratio",type=int)
    parser.add_argument("--fine-block-pivot-ratio",type=int)
    parser.add_argument("--generate-config-sample-stride",type=int)
    parser.add_argument("--h1-block-sampling-num",type=int)
    parser.add_argument("--stat-eb-ratio",type=float)
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--template-csv",type=Path,default=project_root/"csv/tuning_results.csv")
    parser.add_argument("--template-metadata",type=Path,default=project_root/"csv/tuning_results.metadata.json")
    parser.add_argument("--output-csv",type=Path,default=project_root/"csv/tuning_results.csv")
    parser.add_argument("--output-metadata",type=Path,default=project_root/"csv/tuning_results.metadata.json")
    arguments=parser.parse_args()
    if (arguments.fine_result_prefix is None)!=(arguments.fine_method is None):
        parser.error("--fine-result-prefix和--fine-method必须同时设置")
    if (arguments.coarse_block_pivot_ratio is None)!=(arguments.fine_block_pivot_ratio is None):
        parser.error("--coarse-block-pivot-ratio和--fine-block-pivot-ratio必须同时设置")

    selected={}
    for dataset,suffix in dataset_suffixes.items():
        path=arguments.result_directory/f"{arguments.result_prefix}{suffix}"
        for row in read_rows(path):
            if row["METHOD"]==arguments.method:
                selected[(dataset,float(row["REL_EB"]))]=(row["BR"],row["PSNR"])
        if arguments.fine_result_prefix is not None:
            path=arguments.result_directory/f"{arguments.fine_result_prefix}{suffix}"
            for row in read_rows(path):
                rel_eb=float(row["REL_EB"])
                if row["METHOD"]==arguments.fine_method and rel_eb<=arguments.fine_max_rel_eb:
                    selected[(dataset,rel_eb)]=(row["BR"],row["PSNR"])
    template_rows=read_rows(arguments.template_csv)
    expected={(row["DATASET"],float(row["REL_EB"])) for row in template_rows}
    if set(selected)!=expected:
        raise ValueError(f"选定结果不完整：expected={len(expected)},actual={len(selected)}")
    promoted=[]
    for row in template_rows:
        output_row=dict(row)
        output_row["ASZ_BR"],output_row["ASZ_PSNR"]=selected[(row["DATASET"],float(row["REL_EB"]))]
        promoted.append(output_row)
    write_csv(arguments.output_csv,promoted,template_rows[0].keys())

    with open(arguments.template_metadata,encoding="utf-8") as input_file:
        metadata=json.load(input_file)
    method_match=re.fullmatch(r"asz_l(\d+)_e(\d+)",arguments.method)
    if method_match:
        metadata["metrics"]["asz_max_layer_num"]=int(method_match.group(1))
        metadata["metrics"]["asz_eb_ratio"]=int(method_match.group(2))/100
    if arguments.coarse_block_pivot_ratio is not None:
        metadata["metrics"]["asz_coarse_block_pivot_ratio"]=arguments.coarse_block_pivot_ratio
        metadata["metrics"]["asz_fine_block_pivot_ratio"]=arguments.fine_block_pivot_ratio
    if arguments.generate_config_sample_stride is not None:
        metadata["metrics"]["asz_generate_config_sample_stride"]=arguments.generate_config_sample_stride
    if arguments.h1_block_sampling_num is not None:
        metadata["metrics"]["asz_h1_block_sampling_num"]=arguments.h1_block_sampling_num
    if arguments.stat_eb_ratio is not None:
        metadata["metrics"]["asz_stat_eb_ratio"]=arguments.stat_eb_ratio
    dataset_statistics=[]
    dataset_ratios=[]
    for dataset in dataset_suffixes:
        rows=[row for row in promoted if row["DATASET"]==dataset]
        candidate=[(float(row["ASZ_PSNR"]),float(row["ASZ_BR"])) for row in rows]
        baselines=[[(float(row[f"{method}_PSNR"]),float(row[f"{method}_BR"])) for row in rows] for method in ("SZ3","QOZ")]
        ratio,winning_fraction,common_psnr=compare_to_envelope(candidate,baselines)
        dataset_ratios.append(ratio)
        dataset_statistics.append({
            "dataset":dataset,
            "common_psnr":[round(value,6) for value in common_psnr],
            "rate_saving_percent":round(100*(1-ratio),6),
            "winning_psnr_fraction_percent":round(100*winning_fraction,3),
        })
    metadata["generated_at"]=date.today().isoformat()
    metadata["point_count"]=len(promoted)
    metadata["comparison"]["equal_dataset_rate_saving_percent"]=round(100*(1-geometric_mean(dataset_ratios)),6)
    metadata["comparison"]["per_dataset"]=dataset_statistics
    write_metadata(arguments.output_metadata,metadata)
    print(f"写入canonical CSV：{arguments.output_csv}")
    print(f"写入metadata：{arguments.output_metadata}")
    print(f"相对SZ3/QoZ envelope的等权rate saving：{metadata['comparison']['equal_dataset_rate_saving_percent']:.6f}%")

if __name__=="__main__":
    main()
