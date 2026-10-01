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
    for left,right in zip(points,points[1:]):
        if left[0]<=target_psnr<=right[0]:
            weight=(target_psnr-left[0])/(right[0]-left[0])
            return math.log(left[1])+weight*(math.log(right[1])-math.log(left[1]))
    raise ValueError(f"PSNR {target_psnr}不在基准曲线[{points[0][0]},{points[-1][0]}]内")

def geometric_mean(values):
    return math.exp(sum(math.log(value) for value in values)/len(values))

def pareto_curve(points):
    best_by_psnr={}
    for psnr,br in points:
        if not math.isfinite(psnr) or not math.isfinite(br) or br<=0:
            raise ValueError(f"RD点无效：psnr={psnr},br={br}")
        best_by_psnr[psnr]=min(br,best_by_psnr.get(psnr,math.inf))
    frontier=[]
    best_br=math.inf
    for psnr in sorted(best_by_psnr,reverse=True):
        br=best_by_psnr[psnr]
        if br<best_br:
            frontier.append((psnr,br))
            best_br=br
    frontier.sort()
    if len(frontier)<2:
        raise ValueError("Pareto RD曲线不足两个点")
    return frontier

def compare_curves(candidate,baseline):
    candidate=pareto_curve(candidate)
    baseline=pareto_curve(baseline)
    common_left=max(candidate[0][0],baseline[0][0])
    common_right=min(candidate[-1][0],baseline[-1][0])
    if common_left>=common_right:
        raise ValueError("候选曲线和基准曲线没有共同PSNR区间")
    knots=sorted({common_left,common_right,*[psnr for psnr,_ in candidate if common_left<psnr<common_right],*[psnr for psnr,_ in baseline if common_left<psnr<common_right]})
    log_ratio_integral=0
    winning_length=0
    for left,right in zip(knots,knots[1:]):
        left_diff=interpolate_log_br(candidate,left)-interpolate_log_br(baseline,left)
        right_diff=interpolate_log_br(candidate,right)-interpolate_log_br(baseline,right)
        length=right-left
        log_ratio_integral+=length*(left_diff+right_diff)/2
        if left_diff<0 and right_diff<0:
            winning_length+=length
        elif (left_diff<0)!=(right_diff<0):
            crossing=left+length*(-left_diff)/(right_diff-left_diff)
            winning_length+=(crossing-left) if left_diff<0 else (right-crossing)
    interval=common_right-common_left
    return math.exp(log_ratio_integral/interval),winning_length/interval

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
    winning_fractions={}
    if arguments.curve_baseline_method:
        if arguments.curve_baseline_method not in result_curves:
            raise ValueError(f"结果中没有基准method：{arguments.curve_baseline_method}")
        reference_curves=result_curves[arguments.curve_baseline_method]
    else:
        reference_curves=baseline
    for method,dataset_curves in result_curves.items():
        for dataset,candidate in dataset_curves.items():
            ratio,winning_fraction=compare_curves(candidate,reference_curves[dataset])
            ratios.setdefault(method,{})[dataset]=ratio
            winning_fractions.setdefault(method,{})[dataset]=winning_fraction

    ranking=[]
    for method,dataset_ratios in ratios.items():
        match=re.fullmatch(r"asz_l(\d+)_e(\d+)",method)
        pivot_match=re.fullmatch(r"asz_p(\d+)",method)
        if set(dataset_ratios)!=set(dataset_suffixes):
            raise ValueError(f"{method}缺少数据集结果")
        overall_ratio=geometric_mean(dataset_ratios.values())
        ranking.append({
            "METHOD":method,
            "MAX_LAYER_NUM":int(match.group(1)) if match else "",
            "EB_RATIO":int(match.group(2))/100 if match else "",
            "PIVOT_EB_RATIO":int(pivot_match.group(1))/10**len(pivot_match.group(1)) if pivot_match else "",
            "DATASET_COUNT":len(dataset_ratios),
            "VS_DEFAULT_PERCENT":100*(overall_ratio-1),
            "MEAN_COMMON_PSNR_WIN_PERCENT":100*sum(winning_fractions[method].values())/len(winning_fractions[method]),
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
