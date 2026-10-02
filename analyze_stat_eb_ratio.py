import csv
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={"APS_Kaz":"aps_kaz.csv","Aramco":"aramco.csv","CLDICE":"cldice.csv","Isabel_Pf01":"isabel.csv","LETKF_PRES":"letkf.csv","VideoLLaVA":"videollava.csv"}
ratios=(0.0125,0.025,0.05,0.075,0.1,0.15,0.2,0.4)
method_names={0.0125:"asz_stat_00125",0.025:"asz_stat_0025",0.05:"asz_stat_005",0.075:"asz_stat_0075",0.1:"asz_stat_01",0.15:"asz_stat_015",0.2:"asz_stat_02",0.4:"asz_stat_04"}

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def paired_geometric_ratio(candidate,baseline,key):
    return geometric_mean([float(row[key])/float(baseline[point][key]) for point,row in candidate.items()])

def main():
    rows_by_method={method:{} for method in method_names.values()}
    curves={method:{} for method in method_names.values()}
    for dataset,suffix in dataset_suffixes.items():
        for prefix in ("stat_eb_ratio_","stat_eb_ratio_refinement_","stat_eb_ratio_high_refinement_"):
            path=project_root/"results"/f"{prefix}{suffix}"
            if not path.exists():
                continue
            for row in read_rows(path):
                if row["METHOD"] not in rows_by_method:
                    continue
                point=(dataset,float(row["REL_EB"]))
                rows_by_method[row["METHOD"]][point]=row
                curves[row["METHOD"]].setdefault(dataset,[]).append((float(row["PSNR"]),float(row["BR"])))
    baseline_method=method_names[0.1]
    expected_points={(dataset,rel_eb) for dataset in dataset_suffixes for rel_eb in (0.1,0.01,0.001,0.0001,0.00001)}
    for method,rows in rows_by_method.items():
        if set(rows)!=expected_points:
            raise ValueError(f"{method}结果不完整：expected={len(expected_points)},actual={len(rows)}")
    ranking=[]
    for ratio,method in method_names.items():
        dataset_ratios={dataset:compare_curves(curves[method][dataset],curves[baseline_method][dataset])[0] for dataset in dataset_suffixes}
        plan_time_ratio=paired_geometric_ratio(rows_by_method[method],rows_by_method[baseline_method],"GENERATE_CONFIG_TIME")
        encode_time_ratios=[]
        for point,row in rows_by_method[method].items():
            baseline=rows_by_method[baseline_method][point]
            encode_time_ratios.append((float(row["GENERATE_CONFIG_TIME"])+float(row["COMPRESSION_TIME"]))/(float(baseline["GENERATE_CONFIG_TIME"])+float(baseline["COMPRESSION_TIME"])))
        ranking.append({"STAT_EB_RATIO":ratio,"VS_01_BITRATE_PERCENT":100*(geometric_mean(dataset_ratios.values())-1),"VS_01_PLAN_TIME_PERCENT":100*(plan_time_ratio-1),"VS_01_TOTAL_ENCODE_TIME_PERCENT":100*(geometric_mean(encode_time_ratios)-1),**{f"{dataset}_BITRATE_PERCENT":100*(value-1) for dataset,value in dataset_ratios.items()}})
    ranking.sort(key=lambda row:row["VS_01_BITRATE_PERCENT"])
    output=project_root/"csv/stat_eb_ratio_ranking.csv"
    temporary_path=output.with_name(output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=ranking[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    temporary_path.replace(output)
    for index,row in enumerate(ranking,1):
        print(f"{index}. ratio={row['STAT_EB_RATIO']}: bitrate={row['VS_01_BITRATE_PERCENT']:+.3f}%,plan_time={row['VS_01_PLAN_TIME_PERCENT']:+.1f}%,total_encode={row['VS_01_TOTAL_ENCODE_TIME_PERCENT']:+.1f}%")
    print("leave-one-dataset-out:")
    for held_out in dataset_suffixes:
        training=[dataset for dataset in dataset_suffixes if dataset!=held_out]
        best_row=min(ranking,key=lambda row:geometric_mean([1+row[f"{dataset}_BITRATE_PERCENT"]/100 for dataset in training]))
        training_ratio=geometric_mean([1+best_row[f"{dataset}_BITRATE_PERCENT"]/100 for dataset in training])
        print(f"  {held_out}: ratio={best_row['STAT_EB_RATIO']},train={100*(training_ratio-1):+.3f}%,held={best_row[f'{held_out}_BITRATE_PERCENT']:+.3f}%")
    best=ranking[0]["STAT_EB_RATIO"]
    print(f"best={best},boundary={best in (ratios[0],ratios[-1])}")
    print(f"写入排名：{output}")

if __name__=="__main__":
    main()
