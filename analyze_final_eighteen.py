import argparse,csv,math,statistics
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean
from plot_final_eighteen_rd import datasets,read_curves
from plot_final_eighteen_runtime import load_timings,preprocessing_time,row_at_rel_eb
from promote_asz_tuning_results import compare_to_envelope

project_root=Path(__file__).resolve().parent
fieldnames=["DATASET","ASZ_CR_X_SZ3","ASZ_CR_X_QOZ","ASZ_CR_X_BEST_BASELINE","ASZ_TOTAL_TIME","SZ3_TOTAL_TIME","QOZ_TOTAL_TIME","ASZ_PREPROCESSING_SHARE_PERCENT","ASZ_VS_SZ3_TIME_REDUCTION_PERCENT","ASZ_VS_QOZ_TIME_REDUCTION_PERCENT"]


def psnr_bitrate_curve(points):
    return [(psnr,bitrate) for bitrate,psnr in points]


def total_time(row,include_preprocessing=False):
    total=float(row["COMPRESSION_TIME"])+float(row["DECOMPRESSION_TIME"])
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
    parser=argparse.ArgumentParser(description="汇总最终18个数据的等PSNR压缩率和1e-3运行时间")
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--rel-eb",type=float,default=1e-3)
    parser.add_argument("--output",type=Path,default=project_root/"results/final_eighteen_analysis.csv")
    arguments=parser.parse_args()

    rows=[]
    for dataset in datasets:
        title,_,asz_filename,baseline_filename=dataset
        curves=read_curves(arguments.result_directory,asz_filename,baseline_filename)
        asz=psnr_bitrate_curve(curves["asz"])
        sz3=psnr_bitrate_curve(curves["sz3"])
        qoz=psnr_bitrate_curve(curves["qoz"])
        asz_over_sz3,_=compare_curves(asz,sz3)
        asz_over_qoz,_=compare_curves(asz,qoz)
        asz_over_best,_,_=compare_to_envelope(asz,[sz3,qoz])
        timings=load_timings(arguments.result_directory,dataset)
        asz_timing=row_at_rel_eb(timings["asz"],arguments.rel_eb)
        sz3_timing=row_at_rel_eb(timings["sz3"],arguments.rel_eb)
        qoz_timing=row_at_rel_eb(timings["qoz"],arguments.rel_eb)
        asz_total=total_time(asz_timing,True)
        sz3_total=total_time(sz3_timing)
        qoz_total=total_time(qoz_timing)
        rows.append({"DATASET":title,"ASZ_CR_X_SZ3":1/asz_over_sz3,"ASZ_CR_X_QOZ":1/asz_over_qoz,"ASZ_CR_X_BEST_BASELINE":1/asz_over_best,"ASZ_TOTAL_TIME":asz_total,"SZ3_TOTAL_TIME":sz3_total,"QOZ_TOTAL_TIME":qoz_total,"ASZ_PREPROCESSING_SHARE_PERCENT":100*preprocessing_time(asz_timing)/asz_total,"ASZ_VS_SZ3_TIME_REDUCTION_PERCENT":100*(1-asz_total/sz3_total),"ASZ_VS_QOZ_TIME_REDUCTION_PERCENT":100*(1-asz_total/qoz_total)})

    summary={"DATASET":"__SUMMARY__","ASZ_CR_X_SZ3":geometric_mean([float(row["ASZ_CR_X_SZ3"]) for row in rows]),"ASZ_CR_X_QOZ":geometric_mean([float(row["ASZ_CR_X_QOZ"]) for row in rows]),"ASZ_CR_X_BEST_BASELINE":geometric_mean([float(row["ASZ_CR_X_BEST_BASELINE"]) for row in rows]),"ASZ_TOTAL_TIME":"","SZ3_TOTAL_TIME":"","QOZ_TOTAL_TIME":"","ASZ_PREPROCESSING_SHARE_PERCENT":statistics.mean(float(row["ASZ_PREPROCESSING_SHARE_PERCENT"]) for row in rows),"ASZ_VS_SZ3_TIME_REDUCTION_PERCENT":statistics.mean(float(row["ASZ_VS_SZ3_TIME_REDUCTION_PERCENT"]) for row in rows),"ASZ_VS_QOZ_TIME_REDUCTION_PERCENT":statistics.mean(float(row["ASZ_VS_QOZ_TIME_REDUCTION_PERCENT"]) for row in rows)}
    rows.append(summary)
    write_csv(arguments.output,rows)
    print(f"asz_cr_x_sz3={summary['ASZ_CR_X_SZ3']:.6f}")
    print(f"asz_cr_x_qoz={summary['ASZ_CR_X_QOZ']:.6f}")
    print(f"asz_cr_x_best_baseline={summary['ASZ_CR_X_BEST_BASELINE']:.6f}")
    print(f"asz_vs_qoz_time_reduction_percent={summary['ASZ_VS_QOZ_TIME_REDUCTION_PERCENT']:.6f}")
    print(f"output={arguments.output}")


if __name__=="__main__":
    main()
