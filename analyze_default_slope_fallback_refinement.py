import csv
import math
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={"APS_Kaz":"aps_kaz.csv","Aramco":"aramco.csv","CLDICE":"cldice.csv","Isabel_Pf01":"isabel.csv","LETKF_PRES":"letkf.csv","VideoLLaVA":"videollava.csv"}
fallbacks=(500,750,1000,1500,2000,3000,5000)

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def main():
    baseline_rows={}
    for dataset,suffix in dataset_suffixes.items():
        rows=read_rows(project_root/"results"/f"default_slope_fallback_{suffix}")
        baseline_rows[dataset]={float(row["REL_EB"]):row for row in rows if row["METHOD"]=="asz_slope_f1000"}
    no_cap_rows=read_rows(project_root/"results/default_slope_no_cap_aps.csv")
    baseline_rows["APS_Kaz"][0.0001]=next(row for row in no_cap_rows if row["METHOD"]=="asz_slope_f1000")
    refinement_rows={fallback:{} for fallback in fallbacks}
    for dataset,suffix in dataset_suffixes.items():
        path=project_root/"results"/f"default_slope_fallback_refinement_{suffix}"
        if not path.exists():
            continue
        for row in read_rows(path):
            fallback=int(row["METHOD"].removeprefix("asz_slope_r"))
            refinement_rows[fallback][(dataset,float(row["REL_EB"]))]=row
    curves={}
    for fallback in fallbacks:
        curves[fallback]={}
        for dataset,points in baseline_rows.items():
            merged=dict(points)
            for rel_eb in points:
                replacement=refinement_rows[fallback].get((dataset,rel_eb))
                if replacement is not None and (dataset,rel_eb)!=("APS_Kaz",0.0001):
                    merged[rel_eb]=replacement
            curves[fallback][dataset]=[(float(row["PSNR"]),float(row["BR"])) for row in merged.values()]
    for point,row in refinement_rows[1000].items():
        if point==("APS_Kaz",0.0001):
            continue
        baseline=baseline_rows[point[0]][point[1]]
        if not math.isclose(float(row["BR"]),float(baseline["BR"]),rel_tol=0,abs_tol=1e-12) or not math.isclose(float(row["PSNR"]),float(baseline["PSNR"]),rel_tol=0,abs_tol=1e-12):
            raise ValueError(f"1000重复实验与第一阶段不一致：{point}")
    ranking=[]
    for fallback in fallbacks:
        dataset_ratios={dataset:compare_curves(curves[fallback][dataset],curves[1000][dataset])[0] for dataset in dataset_suffixes}
        ranking.append({"DEFAULT_SLOPE_FALLBACK":fallback,"VS_1000_BITRATE_PERCENT":100*(geometric_mean(dataset_ratios.values())-1),**{f"{dataset}_BITRATE_PERCENT":100*(value-1) for dataset,value in dataset_ratios.items()}})
    ranking.sort(key=lambda row:row["VS_1000_BITRATE_PERCENT"])
    output=project_root/"csv/default_slope_fallback_refinement_ranking.csv"
    temporary_path=output.with_name(output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=ranking[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    temporary_path.replace(output)
    for index,row in enumerate(ranking,1):
        print(f"{index}. fallback={row['DEFAULT_SLOPE_FALLBACK']}: bitrate={row['VS_1000_BITRATE_PERCENT']:+.3f}%")
    print(f"写入排名：{output}")

if __name__=="__main__":
    main()
