import argparse,csv,math,re
from pathlib import Path

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

def interpolate_log_br(points,target_psnr):
    points=sorted(points)
    for left,right in zip(points,points[1:]):
        if left[0]<=target_psnr<=right[0]:
            weight=(target_psnr-left[0])/(right[0]-left[0])
            return math.log(left[1])+weight*(math.log(right[1])-math.log(left[1]))
    raise ValueError(f"PSNR {target_psnr}不在基准曲线[{points[0][0]},{points[-1][0]}]内")

def geometric_mean(values):
    return math.exp(sum(math.log(value) for value in values)/len(values))

def compare_curves(candidate,baseline):
    candidate=sorted(candidate)
    baseline=sorted(baseline)
    common_left=max(candidate[0][0],baseline[0][0])
    common_right=min(candidate[-1][0],baseline[-1][0])
    if common_left>=common_right:
        raise ValueError("候选曲线和基准曲线没有共同PSNR区间")
    knots=sorted({common_left,common_right,*[psnr for psnr,_ in candidate if common_left<psnr<common_right],*[psnr for psnr,_ in baseline if common_left<psnr<common_right]})
    ratio_integral=0
    winning_length=0
    for left,right in zip(knots,knots[1:]):
        left_diff=interpolate_log_br(candidate,left)-interpolate_log_br(baseline,left)
        right_diff=interpolate_log_br(candidate,right)-interpolate_log_br(baseline,right)
        length=right-left
        if math.isclose(left_diff,right_diff,rel_tol=0,abs_tol=1e-14):
            ratio_integral+=length*math.exp(left_diff)
        else:
            ratio_integral+=length*(math.exp(right_diff)-math.exp(left_diff))/(right_diff-left_diff)
        if left_diff<0 and right_diff<0:
            winning_length+=length
        elif (left_diff<0)!=(right_diff<0):
            crossing=left+length*(-left_diff)/(right_diff-left_diff)
            winning_length+=(crossing-left) if left_diff<0 else (right-crossing)
    interval=common_right-common_left
    return ratio_integral/interval,winning_length/interval

def main():
    parser=argparse.ArgumentParser(description="按等PSNR bitrate汇总max_layer_num和eb_ratio粗筛结果")
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--result-prefix",default="layer_eb_")
    parser.add_argument("--baseline",type=Path,default=project_root/"csv/tuning_results.csv")
    parser.add_argument("--curve-baseline-method")
    parser.add_argument("--output",type=Path,default=project_root/"results/layer_eb_ranking.csv")
    arguments=parser.parse_args()

    baseline_rows=read_rows(arguments.baseline)
    baseline={}
    for row in baseline_rows:
        baseline.setdefault(row["DATASET"],[]).append((float(row["ASZ_PSNR"]),float(row["ASZ_BR"])))

    result_curves={}
    for dataset,suffix in dataset_suffixes.items():
        path=arguments.result_directory/f"{arguments.result_prefix}{suffix}"
        if not path.is_file():
            raise FileNotFoundError(f"缺少筛选结果：{path}")
        for row in read_rows(path):
            result_curves.setdefault(row["METHOD"],{}).setdefault(dataset,[]).append((float(row["PSNR"]),float(row["BR"])))

    ratios={}
    point_wins={}
    point_counts={}
    if arguments.curve_baseline_method:
        if arguments.curve_baseline_method not in result_curves:
            raise ValueError(f"结果中没有基准method：{arguments.curve_baseline_method}")
        for method,dataset_curves in result_curves.items():
            for dataset,candidate in dataset_curves.items():
                ratio,winning_fraction=compare_curves(candidate,result_curves[arguments.curve_baseline_method][dataset])
                ratios.setdefault(method,{})[dataset]=[ratio]
                point_wins[method]=point_wins.get(method,0)+winning_fraction
                point_counts[method]=point_counts.get(method,0)+1
    else:
        for method,dataset_curves in result_curves.items():
            for dataset,points in dataset_curves.items():
                for candidate_psnr,candidate_br in points:
                    baseline_br=math.exp(interpolate_log_br(baseline[dataset],candidate_psnr))
                    ratio=candidate_br/baseline_br
                    ratios.setdefault(method,{}).setdefault(dataset,[]).append(ratio)
                    point_wins[method]=point_wins.get(method,0)+(ratio<1)
                    point_counts[method]=point_counts.get(method,0)+1

    ranking=[]
    for method,dataset_points in ratios.items():
        match=re.fullmatch(r"asz_l(\d+)_e(\d+)",method)
        dataset_ratios={dataset:geometric_mean(values) for dataset,values in dataset_points.items()}
        if set(dataset_ratios)!=set(dataset_suffixes):
            raise ValueError(f"{method}缺少数据集结果")
        overall_ratio=geometric_mean(dataset_ratios.values())
        ranking.append({
            "METHOD":method,
            "MAX_LAYER_NUM":int(match.group(1)) if match else "",
            "EB_RATIO":int(match.group(2))/100 if match else "",
            "DATASET_COUNT":len(dataset_ratios),
            "POINT_COUNT":point_counts[method],
            "VS_DEFAULT_PERCENT":100*(overall_ratio-1),
            "WINNING_POINT_FRACTION_PERCENT":100*point_wins[method]/point_counts[method],
            **{f"{dataset}_PERCENT":100*(ratio-1) for dataset,ratio in dataset_ratios.items()},
        })
    ranking.sort(key=lambda row:row["VS_DEFAULT_PERCENT"])

    arguments.output.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=arguments.output.with_name(arguments.output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=ranking[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    temporary_path.replace(arguments.output)
    for index,row in enumerate(ranking,1):
        print(f"{index:2d}. {row['METHOD']}: {row['VS_DEFAULT_PERCENT']:+.3f}%")
    print(f"写入排名：{arguments.output}")

if __name__=="__main__":
    main()
