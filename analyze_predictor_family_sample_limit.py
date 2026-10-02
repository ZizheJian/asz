import csv
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={"APS_Kaz":"aps_kaz.csv","Aramco":"aramco.csv","CLDICE":"cldice.csv","Isabel_Pf01":"isabel.csv","LETKF_PRES":"letkf.csv","VideoLLaVA":"videollava.csv"}
limits=(10000,50000,100000,200000)

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def main():
    methods={f"asz_qsample_{limit}":limit for limit in limits}
    rows_by_method={method:{} for method in methods}
    curves={method:{} for method in methods}
    for dataset,suffix in dataset_suffixes.items():
        for row in read_rows(project_root/"results"/f"predictor_family_sample_limit_{suffix}"):
            method=row["METHOD"]
            point=(dataset,float(row["REL_EB"]))
            rows_by_method[method][point]=row
            curves[method].setdefault(dataset,[]).append((float(row["PSNR"]),float(row["BR"])))
    baseline_method="asz_qsample_200000"
    expected_points={(dataset,rel_eb) for dataset in dataset_suffixes for rel_eb in (0.1,0.01,0.001,0.0001,0.00001)}
    for method,rows in rows_by_method.items():
        if set(rows)!=expected_points:
            raise ValueError(f"{method}结果不完整：expected={len(expected_points)},actual={len(rows)}")
    ranking=[]
    disagreement_rows=[]
    for method,limit in methods.items():
        dataset_ratios={dataset:compare_curves(curves[method][dataset],curves[baseline_method][dataset])[0] for dataset in dataset_suffixes}
        selection_time_ratio=geometric_mean([float(row["PREDICTOR_FAMILY_SELECTION_TIME"])/float(rows_by_method[baseline_method][point]["PREDICTOR_FAMILY_SELECTION_TIME"]) for point,row in rows_by_method[method].items()])
        total_time_ratio=geometric_mean([(float(row["GENERATE_CONFIG_TIME"])+float(row["PREDICTOR_FAMILY_SELECTION_TIME"])+float(row["COMPRESSION_TIME"]))/(float(rows_by_method[baseline_method][point]["GENERATE_CONFIG_TIME"])+float(rows_by_method[baseline_method][point]["PREDICTOR_FAMILY_SELECTION_TIME"])+float(rows_by_method[baseline_method][point]["COMPRESSION_TIME"])) for point,row in rows_by_method[method].items()])
        disagreement_count=0
        fallback_count=0
        quintic_count=0
        for point,row in rows_by_method[method].items():
            baseline=rows_by_method[baseline_method][point]
            fallback_count+=row["PREDICTOR_FAMILY_FALLBACK"]=="True"
            quintic_count+=row["PREDICTOR_FAMILY"]=="quintic"
            if row["PREDICTOR_FAMILY"]!=baseline["PREDICTOR_FAMILY"]:
                disagreement_count+=1
                disagreement_rows.append({"SAMPLE_LIMIT":limit,"DATASET":point[0],"REL_EB":point[1],"FAMILY":row["PREDICTOR_FAMILY"],"BASELINE_FAMILY":baseline["PREDICTOR_FAMILY"],"CUBIC_MSE":row["CUBIC_MSE"],"QUINTIC_MSE":row["QUINTIC_MSE"]})
        ranking.append({"SAMPLE_LIMIT":limit,"VS_200000_BITRATE_PERCENT":100*(geometric_mean(dataset_ratios.values())-1),"VS_200000_SELECTION_TIME_PERCENT":100*(selection_time_ratio-1),"VS_200000_TOTAL_ENCODE_TIME_PERCENT":100*(total_time_ratio-1),"FAMILY_DISAGREEMENT_COUNT":disagreement_count,"QUINTIC_COUNT":quintic_count,"NO_SAMPLE_FALLBACK_COUNT":fallback_count,**{f"{dataset}_BITRATE_PERCENT":100*(ratio-1) for dataset,ratio in dataset_ratios.items()}})
    ranking.sort(key=lambda row:(row["FAMILY_DISAGREEMENT_COUNT"],row["SAMPLE_LIMIT"]))
    output=project_root/"csv/predictor_family_sample_limit_ranking.csv"
    temporary_path=output.with_name(output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=ranking[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    temporary_path.replace(output)
    disagreement_output=project_root/"csv/predictor_family_sample_limit_disagreements.csv"
    if disagreement_rows:
        temporary_disagreement_path=disagreement_output.with_name(disagreement_output.name+".tmp")
        with open(temporary_disagreement_path,"w",newline="",encoding="utf-8") as output_file:
            writer=csv.DictWriter(output_file,fieldnames=disagreement_rows[0].keys(),lineterminator="\n")
            writer.writeheader()
            writer.writerows(disagreement_rows)
        temporary_disagreement_path.replace(disagreement_output)
    elif disagreement_output.exists():
        disagreement_output.unlink()
    for index,row in enumerate(ranking,1):
        print(f"{index}. sample_limit={row['SAMPLE_LIMIT']}: bitrate={row['VS_200000_BITRATE_PERCENT']:+.3f}%,selection_time={row['VS_200000_SELECTION_TIME_PERCENT']:+.1f}%,total_encode={row['VS_200000_TOTAL_ENCODE_TIME_PERCENT']:+.1f}%,disagreements={row['FAMILY_DISAGREEMENT_COUNT']},quintic={row['QUINTIC_COUNT']},fallback={row['NO_SAMPLE_FALLBACK_COUNT']}")
    print(f"写入排名：{output}")
    if disagreement_rows:
        print(f"写入分歧：{disagreement_output}")

if __name__=="__main__":
    main()
