import argparse,csv,math
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_files={
    "APS_Kaz":"final_eight_aps_kaz.csv",
    "Aramco":"final_eight_aramco.csv",
    "CLDICE":"final_eight_cldice.csv",
    "Isabel":"final_eight_isabel.csv",
    "LETKF":"final_eight_letkf.csv",
    "VideoLLaVA":"final_eight_videollava.csv",
    "E017":"final_eight_e017.csv",
    "APSU":"final_eight_apsu.csv",
}
methods=("asz","sz3","qoz")

def read_curves(path):
    curves={method:[] for method in methods}
    with open(path,newline="",encoding="utf-8") as input_file:
        rows=list(csv.DictReader(input_file))
    for row in rows:
        method=row["METHOD"]
        if method not in curves:
            raise ValueError(f"{path}包含未知method：{method}")
        curves[method].append((float(row["PSNR"]),float(row["BR"])))
    for method,points in curves.items():
        if len(points)!=5:
            raise ValueError(f"{path}的{method}应有5个RD点，实际有{len(points)}个")
    return curves

def main():
    parser=argparse.ArgumentParser(description="汇总最终八数据上的ASZ、SZ3和QoZ等PSNR bitrate结果")
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--output",type=Path,default=project_root/"results/final_eight_comparison.csv")
    arguments=parser.parse_args()

    rows=[]
    ratios={baseline:[] for baseline in ("sz3","qoz")}
    winning_fractions={baseline:[] for baseline in ("sz3","qoz")}
    for dataset,filename in dataset_files.items():
        path=arguments.result_directory/filename
        if not path.is_file():
            raise FileNotFoundError(f"缺少最终结果：{path}")
        curves=read_curves(path)
        for baseline in ("sz3","qoz"):
            ratio,winning_fraction=compare_curves(curves["asz"],curves[baseline])
            ratios[baseline].append(ratio)
            winning_fractions[baseline].append(winning_fraction)
            rows.append({"DATASET":dataset,"BASELINE":baseline.upper(),"ASZ_TO_BASELINE_BITRATE_RATIO":ratio,"BITRATE_SAVING_PERCENT":100*(1-ratio),"COMMON_PSNR_WIN_PERCENT":100*winning_fraction})

    for baseline in ("sz3","qoz"):
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
        print(f"{row['DATASET']:10s} vs {row['BASELINE']:3s}: bitrate_ratio={row['ASZ_TO_BASELINE_BITRATE_RATIO']:.6f},saving={row['BITRATE_SAVING_PERCENT']:+.3f}%,win={row['COMMON_PSNR_WIN_PERCENT']:.1f}%")
    print(f"写入汇总：{arguments.output}")

if __name__=="__main__":
    main()
