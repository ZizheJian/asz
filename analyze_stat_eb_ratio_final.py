import csv
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={"APS_Kaz":"aps_kaz.csv","Aramco":"aramco.csv","CLDICE":"cldice.csv","Isabel_Pf01":"isabel.csv","LETKF_PRES":"letkf.csv","VideoLLaVA":"videollava.csv"}
methods={0.075:"asz_stat_0075",0.1:"asz_stat_01",0.2:"asz_stat_02"}

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def main():
    rows_by_method={method:{} for method in methods.values()}
    curves={method:{} for method in methods.values()}
    for dataset,suffix in dataset_suffixes.items():
        for row in read_rows(project_root/"results"/f"stat_eb_ratio_final_{suffix}"):
            point=(dataset,float(row["REL_EB"]))
            rows_by_method[row["METHOD"]][point]=row
            curves[row["METHOD"]].setdefault(dataset,[]).append((float(row["PSNR"]),float(row["BR"])))
    baseline_method=methods[0.1]
    ranking=[]
    for ratio,method in methods.items():
        dataset_ratios={dataset:compare_curves(curves[method][dataset],curves[baseline_method][dataset])[0] for dataset in dataset_suffixes}
        plan_time_ratios=[]
        encode_time_ratios=[]
        for point,row in rows_by_method[method].items():
            baseline=rows_by_method[baseline_method][point]
            plan_time_ratios.append(float(row["GENERATE_CONFIG_TIME"])/float(baseline["GENERATE_CONFIG_TIME"]))
            encode_time_ratios.append((float(row["GENERATE_CONFIG_TIME"])+float(row["COMPRESSION_TIME"]))/(float(baseline["GENERATE_CONFIG_TIME"])+float(baseline["COMPRESSION_TIME"])))
        ranking.append({"STAT_EB_RATIO":ratio,"VS_01_BITRATE_PERCENT":100*(geometric_mean(dataset_ratios.values())-1),"VS_01_PLAN_TIME_PERCENT":100*(geometric_mean(plan_time_ratios)-1),"VS_01_TOTAL_ENCODE_TIME_PERCENT":100*(geometric_mean(encode_time_ratios)-1),**{f"{dataset}_BITRATE_PERCENT":100*(value-1) for dataset,value in dataset_ratios.items()}})
    ranking.sort(key=lambda row:row["VS_01_BITRATE_PERCENT"])
    output=project_root/"csv/stat_eb_ratio_final_ranking.csv"
    temporary_path=output.with_name(output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=ranking[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    temporary_path.replace(output)
    for index,row in enumerate(ranking,1):
        print(f"{index}. ratio={row['STAT_EB_RATIO']}: bitrate={row['VS_01_BITRATE_PERCENT']:+.3f}%,plan_time={row['VS_01_PLAN_TIME_PERCENT']:+.1f}%,total_encode={row['VS_01_TOTAL_ENCODE_TIME_PERCENT']:+.1f}%")
    print(f"写入排名：{output}")

if __name__=="__main__":
    main()
