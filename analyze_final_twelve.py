import argparse,csv
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean
from promote_asz_tuning_results import compare_to_envelope

project_root=Path(__file__).resolve().parent
dataset_files={
    "APS_Kaz":"aps_kaz.csv",
    "APSU":"apsu.csv",
    "Aramco_1800":"aramco_1800.csv",
    "CESM_CLDICE_t31":"cldice_t31.csv",
    "CESM_T_t31":"cesm_t31.csv",
    "E017":"e017.csv",
    "EXAFEL_3D":"exafel_3d.csv",
    "Isabel_Pf24":"isabel_pf24.csv",
    "LETKF_PRES":"letkf_pres.csv",
    "LETKF_QV_log10":"letkf_qv_log10.csv",
    "Miranda_pressure":"miranda_pressure.csv",
    "VideoLLaVA_embeds5":"videollava_embeds5.csv",
}
methods=("asz","sz3","qoz")

def read_curves(path):
    curves={method:[] for method in methods}
    with open(path,newline="",encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            method=row["METHOD"]
            if method not in curves:
                raise ValueError(f"{path}包含未知method：{method}")
            curves[method].append((float(row["PSNR"]),float(row["BR"])))
    for method,points in curves.items():
        if len(points)!=5:
            raise ValueError(f"{path}的{method}应有5个RD点，实际有{len(points)}个")
    return curves

def main():
    parser=argparse.ArgumentParser(description="汇总正式十二数据上的ASZ、SZ3和QoZ等PSNR bitrate结果")
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--file-prefix",default="final_twelve_")
    parser.add_argument("--output",type=Path,default=project_root/"results/final_twelve_comparison.csv")
    arguments=parser.parse_args()

    rows=[]
    ratios={baseline:[] for baseline in ("sz3","qoz","best")}
    winning_fractions={baseline:[] for baseline in ("sz3","qoz","best")}
    for dataset,filename in dataset_files.items():
        path=arguments.result_directory/f"{arguments.file_prefix}{filename}"
        if not path.is_file():
            raise FileNotFoundError(f"缺少正式结果：{path}")
        curves=read_curves(path)
        for baseline in ("sz3","qoz"):
            ratio,winning_fraction=compare_curves(curves["asz"],curves[baseline])
            ratios[baseline].append(ratio)
            winning_fractions[baseline].append(winning_fraction)
            rows.append({"DATASET":dataset,"BASELINE":baseline.upper(),"ASZ_TO_BASELINE_BITRATE_RATIO":ratio,"BITRATE_SAVING_PERCENT":100*(1-ratio),"COMMON_PSNR_WIN_PERCENT":100*winning_fraction})
        ratio,winning_fraction,_=compare_to_envelope(curves["asz"],[curves["sz3"],curves["qoz"]])
        ratios["best"].append(ratio)
        winning_fractions["best"].append(winning_fraction)
        rows.append({"DATASET":dataset,"BASELINE":"BEST","ASZ_TO_BASELINE_BITRATE_RATIO":ratio,"BITRATE_SAVING_PERCENT":100*(1-ratio),"COMMON_PSNR_WIN_PERCENT":100*winning_fraction})

    for baseline in ("sz3","qoz","best"):
        ratio=geometric_mean(ratios[baseline])
        rows.append({"DATASET":"GEOMEAN","BASELINE":baseline.upper(),"ASZ_TO_BASELINE_BITRATE_RATIO":ratio,"BITRATE_SAVING_PERCENT":100*(1-ratio),"COMMON_PSNR_WIN_PERCENT":100*sum(winning_fractions[baseline])/len(winning_fractions[baseline])})

    arguments.output.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=arguments.output.with_name(arguments.output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=rows[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary_path.replace(arguments.output)
    for row in rows:
        print(f"{row['DATASET']:20s} vs {row['BASELINE']:4s}: bitrate_ratio={row['ASZ_TO_BASELINE_BITRATE_RATIO']:.6f},saving={row['BITRATE_SAVING_PERCENT']:+.3f}%,win={row['COMMON_PSNR_WIN_PERCENT']:.1f}%")
    print(f"写入汇总：{arguments.output}")

if __name__=="__main__":
    main()
