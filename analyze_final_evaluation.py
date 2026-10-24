import argparse
import csv
import math
import statistics
from pathlib import Path

from evaluation_datasets import compression_time,default_manifest,load_datasets,load_timings,preprocessing_time,read_curves,row_at_rel_eb,runtime_methods

project_root=Path(__file__).resolve().parent
fieldnames=["DATASET","RUNTIME_REL_EB","ASZ_CR_X_SZ3","ASZ_CR_X_QOZ","ASZ_CR_X_ZFP","ASZ_CR_X_SPERR","ASZ_CR_X_HIGH_PERFORMANCE_ENVELOPE","ASZ_CR_X_BEST_BASELINE","ASZ_TOTAL_TIME","SZ3_TOTAL_TIME","QOZ_TOTAL_TIME","ASZ_PREPROCESSING_SHARE_PERCENT","ASZ_VS_SZ3_TIME_REDUCTION_PERCENT","ASZ_VS_QOZ_TIME_REDUCTION_PERCENT"]


def geometric_mean(values):
    return math.exp(math.fsum(math.log(value) for value in values)/len(values))


def pareto_curve(points):
    best_by_psnr={}
    for psnr,bitrate in points:
        if not math.isfinite(psnr) or not math.isfinite(bitrate) or bitrate<=0:
            raise ValueError(f"invalid RD point: psnr={psnr},bitrate={bitrate}")
        best_by_psnr[psnr]=min(bitrate,best_by_psnr.get(psnr,math.inf))
    frontier=[]
    best_bitrate=math.inf
    for psnr in sorted(best_by_psnr,reverse=True):
        bitrate=best_by_psnr[psnr]
        if bitrate<best_bitrate:
            frontier.append((psnr,bitrate))
            best_bitrate=bitrate
    frontier.sort()
    if len(frontier)<2:
        raise ValueError("Pareto RD curve requires at least two points")
    return frontier


def interpolate_log_bitrate(points,target_psnr):
    for left,right in zip(points,points[1:]):
        if left[0]<=target_psnr<=right[0]:
            weight=(target_psnr-left[0])/(right[0]-left[0])
            return math.log(left[1])+weight*(math.log(right[1])-math.log(left[1]))
    raise ValueError(f"PSNR {target_psnr} is outside the RD curve")


def compare_curves(candidate,baseline):
    candidate=pareto_curve(candidate)
    baseline=pareto_curve(baseline)
    common_left=max(candidate[0][0],baseline[0][0])
    common_right=min(candidate[-1][0],baseline[-1][0])
    if common_left>=common_right:
        raise ValueError("RD curves have no common PSNR interval")
    knots=sorted({common_left,common_right,*[psnr for psnr,_ in candidate if common_left<psnr<common_right],*[psnr for psnr,_ in baseline if common_left<psnr<common_right]})
    integral=0
    for left,right in zip(knots,knots[1:]):
        left_difference=interpolate_log_bitrate(candidate,left)-interpolate_log_bitrate(baseline,left)
        right_difference=interpolate_log_bitrate(candidate,right)-interpolate_log_bitrate(baseline,right)
        integral+=(right-left)*(left_difference+right_difference)/2
    return math.exp(integral/(common_right-common_left))


def curve_contains(curve,psnr):
    return curve[0][0]<=psnr<=curve[-1][0]


def envelope_log_bitrate(curves,psnr):
    return min(interpolate_log_bitrate(curve,psnr) for curve in curves if curve_contains(curve,psnr))


def compare_to_envelope(candidate,baselines):
    candidate=pareto_curve(candidate)
    baselines=[pareto_curve(curve) for curve in baselines]
    common_left=max(candidate[0][0],min(curve[0][0] for curve in baselines))
    common_right=min(candidate[-1][0],max(curve[-1][0] for curve in baselines))
    if common_left>=common_right:
        raise ValueError("ASZ and the baseline envelope have no common PSNR interval")
    raw_knots=sorted({common_left,common_right,*[psnr for psnr,_ in candidate if common_left<psnr<common_right],*[psnr for curve in baselines for psnr,_ in curve if common_left<psnr<common_right]})
    crossings=[]
    for left,right in zip(raw_knots,raw_knots[1:]):
        active=[curve for curve in baselines if curve_contains(curve,left) and curve_contains(curve,right)]
        for first_index,first in enumerate(active):
            for second in active[first_index+1:]:
                left_difference=interpolate_log_bitrate(first,left)-interpolate_log_bitrate(second,left)
                right_difference=interpolate_log_bitrate(first,right)-interpolate_log_bitrate(second,right)
                if left_difference*right_difference<0:
                    crossings.append(left+(right-left)*(-left_difference)/(right_difference-left_difference))
    knots=sorted({*raw_knots,*crossings})
    integral=0
    for left,right in zip(knots,knots[1:]):
        left_difference=interpolate_log_bitrate(candidate,left)-envelope_log_bitrate(baselines,left)
        right_difference=interpolate_log_bitrate(candidate,right)-envelope_log_bitrate(baselines,right)
        integral+=(right-left)*(left_difference+right_difference)/2
    return math.exp(integral/(common_right-common_left))


def psnr_bitrate_curve(points):
    return [(psnr,bitrate) for bitrate,psnr in points]


def total_time(row,include_preprocessing=False):
    total=compression_time(row)+float(row["DECOMPRESSION_TIME"])
    return total+preprocessing_time(row) if include_preprocessing else total


def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".tmp")
    with open(temporary,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main():
    parser=argparse.ArgumentParser(description="Summarize RD and runtime for the final 18-field evaluation")
    parser.add_argument("--manifest",type=Path,default=default_manifest)
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--rel-eb",type=float)
    parser.add_argument("--output",type=Path,default=project_root/"results/final_eighteen_analysis.csv")
    arguments=parser.parse_args()
    datasets=load_datasets(arguments.manifest)
    rows=[]
    for dataset in datasets:
        curves=read_curves(arguments.result_directory,dataset)
        asz=psnr_bitrate_curve(curves["asz"])
        sz3=psnr_bitrate_curve(curves["sz3"])
        qoz=psnr_bitrate_curve(curves["qoz"])
        zfp=psnr_bitrate_curve(curves["zfp"])
        sperr=psnr_bitrate_curve(curves["sperr"])
        asz_over_sz3=compare_curves(asz,sz3)
        asz_over_qoz=compare_curves(asz,qoz)
        asz_over_zfp=compare_curves(asz,zfp)
        asz_over_sperr=compare_curves(asz,sperr)
        asz_over_high_performance=compare_to_envelope(asz,[sz3,qoz,zfp])
        asz_over_best=compare_to_envelope(asz,[sz3,qoz,zfp,sperr])
        timings=load_timings(arguments.result_directory,dataset,runtime_methods)
        selected_rel_eb=arguments.rel_eb if arguments.rel_eb is not None else dataset["rel_eb_list"][len(dataset["rel_eb_list"])//2]
        asz_timing=row_at_rel_eb(timings["asz"],selected_rel_eb)
        sz3_timing=row_at_rel_eb(timings["sz3"],selected_rel_eb)
        qoz_timing=row_at_rel_eb(timings["qoz"],selected_rel_eb)
        asz_total=total_time(asz_timing,True)
        sz3_total=total_time(sz3_timing)
        qoz_total=total_time(qoz_timing)
        rows.append({"DATASET":dataset["title"],"RUNTIME_REL_EB":selected_rel_eb,"ASZ_CR_X_SZ3":1/asz_over_sz3,"ASZ_CR_X_QOZ":1/asz_over_qoz,"ASZ_CR_X_ZFP":1/asz_over_zfp,"ASZ_CR_X_SPERR":1/asz_over_sperr,"ASZ_CR_X_HIGH_PERFORMANCE_ENVELOPE":1/asz_over_high_performance,"ASZ_CR_X_BEST_BASELINE":1/asz_over_best,"ASZ_TOTAL_TIME":asz_total,"SZ3_TOTAL_TIME":sz3_total,"QOZ_TOTAL_TIME":qoz_total,"ASZ_PREPROCESSING_SHARE_PERCENT":100*preprocessing_time(asz_timing)/asz_total,"ASZ_VS_SZ3_TIME_REDUCTION_PERCENT":100*(1-asz_total/sz3_total),"ASZ_VS_QOZ_TIME_REDUCTION_PERCENT":100*(1-asz_total/qoz_total)})
    summary={"DATASET":"__SUMMARY__","RUNTIME_REL_EB":"","ASZ_CR_X_SZ3":geometric_mean([float(row["ASZ_CR_X_SZ3"]) for row in rows]),"ASZ_CR_X_QOZ":geometric_mean([float(row["ASZ_CR_X_QOZ"]) for row in rows]),"ASZ_CR_X_ZFP":geometric_mean([float(row["ASZ_CR_X_ZFP"]) for row in rows]),"ASZ_CR_X_SPERR":geometric_mean([float(row["ASZ_CR_X_SPERR"]) for row in rows]),"ASZ_CR_X_HIGH_PERFORMANCE_ENVELOPE":geometric_mean([float(row["ASZ_CR_X_HIGH_PERFORMANCE_ENVELOPE"]) for row in rows]),"ASZ_CR_X_BEST_BASELINE":geometric_mean([float(row["ASZ_CR_X_BEST_BASELINE"]) for row in rows]),"ASZ_TOTAL_TIME":"","SZ3_TOTAL_TIME":"","QOZ_TOTAL_TIME":"","ASZ_PREPROCESSING_SHARE_PERCENT":statistics.mean(float(row["ASZ_PREPROCESSING_SHARE_PERCENT"]) for row in rows),"ASZ_VS_SZ3_TIME_REDUCTION_PERCENT":statistics.mean(float(row["ASZ_VS_SZ3_TIME_REDUCTION_PERCENT"]) for row in rows),"ASZ_VS_QOZ_TIME_REDUCTION_PERCENT":statistics.mean(float(row["ASZ_VS_QOZ_TIME_REDUCTION_PERCENT"]) for row in rows)}
    rows.append(summary)
    write_csv(arguments.output,rows)
    print(f"asz_cr_x_sz3={summary['ASZ_CR_X_SZ3']:.6f}")
    print(f"asz_cr_x_qoz={summary['ASZ_CR_X_QOZ']:.6f}")
    print(f"asz_cr_x_zfp={summary['ASZ_CR_X_ZFP']:.6f}")
    print(f"asz_cr_x_sperr={summary['ASZ_CR_X_SPERR']:.6f}")
    print(f"asz_cr_x_high_performance_envelope={summary['ASZ_CR_X_HIGH_PERFORMANCE_ENVELOPE']:.6f}")
    print(f"asz_cr_x_best_baseline={summary['ASZ_CR_X_BEST_BASELINE']:.6f}")
    print(f"asz_vs_qoz_time_reduction_percent={summary['ASZ_VS_QOZ_TIME_REDUCTION_PERCENT']:.6f}")
    print(f"output={arguments.output}")


if __name__=="__main__":
    main()
