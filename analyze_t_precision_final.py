import csv,json
from collections import Counter
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={"APS_Kaz":"aps_kaz.csv","Aramco":"aramco.csv","CLDICE":"cldice.csv","Isabel_Pf01":"isabel.csv","LETKF_PRES":"letkf.csv","VideoLLaVA":"videollava.csv"}
precisions={16:("asz_t_16_p16","t_precision_final_"),32:("asz_t_16_p32","t_range_lower_extension_"),64:("asz_t_16_p64","t_precision_final_")}

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def main():
    methods={method for method,_ in precisions.values()}
    rows_by_method={method:{} for method in methods}
    curves={method:{} for method in methods}
    histograms={method:{dataset:Counter() for dataset in dataset_suffixes} for method in methods}
    fallback_counts={method:{dataset:0 for dataset in dataset_suffixes} for method in methods}
    for dataset,suffix in dataset_suffixes.items():
        for prefix in {prefix for _,prefix in precisions.values()}:
            for row in read_rows(project_root/"results"/f"{prefix}{suffix}"):
                method=row["METHOD"]
                if method not in methods:
                    continue
                point=(dataset,float(row["REL_EB"]))
                rows_by_method[method][point]=row
                curves[method].setdefault(dataset,[]).append((float(row["PSNR"]),float(row["BR"])))
                if not row["T_HISTOGRAM"] or row["T_FALLBACK_COUNT"]=="":
                    raise ValueError(f"{method} {dataset} rel_eb={row['REL_EB']}缺少t选择统计")
                histograms[method][dataset].update({int(key):value for key,value in json.loads(row["T_HISTOGRAM"]).items()})
                fallback_counts[method][dataset]+=int(row["T_FALLBACK_COUNT"])
    baseline_method=precisions[32][0]
    expected_points={(dataset,rel_eb) for dataset in dataset_suffixes for rel_eb in (0.1,0.01,0.001,0.0001,0.00001)}
    for method,rows in rows_by_method.items():
        if set(rows)!=expected_points:
            raise ValueError(f"{method}结果不完整：expected={len(expected_points)},actual={len(rows)}")
    ranking=[]
    for precision,(method,_) in precisions.items():
        dataset_ratios={dataset:compare_curves(curves[method][dataset],curves[baseline_method][dataset])[0] for dataset in dataset_suffixes}
        plan_ratios=[float(row["GENERATE_CONFIG_TIME"])/float(rows_by_method[baseline_method][point]["GENERATE_CONFIG_TIME"]) for point,row in rows_by_method[method].items()]
        encode_ratios=[(float(row["GENERATE_CONFIG_TIME"])+float(row["COMPRESSION_TIME"]))/(float(rows_by_method[baseline_method][point]["GENERATE_CONFIG_TIME"])+float(rows_by_method[baseline_method][point]["COMPRESSION_TIME"])) for point,row in rows_by_method[method].items()]
        aggregate=sum(histograms[method].values(),Counter())
        fallback_count=sum(fallback_counts[method].values())
        linear_key=precision//4
        aggregate[linear_key]-=fallback_count
        if aggregate[linear_key]<0:
            raise ValueError(f"{method}的fallback数量超过linear选择数量")
        tuned_total=sum(aggregate.values())
        ranking.append({"T_PRECISION":precision,"VS_P32_BITRATE_PERCENT":100*(geometric_mean(dataset_ratios.values())-1),"VS_P32_PLAN_TIME_PERCENT":100*(geometric_mean(plan_ratios)-1),"VS_P32_TOTAL_ENCODE_TIME_PERCENT":100*(geometric_mean(encode_ratios)-1),"FALLBACK_PERCENT":100*fallback_count/(tuned_total+fallback_count),"LOWER_BOUNDARY_PERCENT":100*aggregate[precision//16]/tuned_total,"UPPER_BOUNDARY_PERCENT":100*aggregate[6*precision//16]/tuned_total,**{f"{dataset}_BITRATE_PERCENT":100*(ratio-1) for dataset,ratio in dataset_ratios.items()}})
    ranking.sort(key=lambda row:row["VS_P32_BITRATE_PERCENT"])
    output=project_root/"csv/t_precision_final_ranking.csv"
    temporary_path=output.with_name(output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=ranking[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    temporary_path.replace(output)
    for index,row in enumerate(ranking,1):
        print(f"{index}. precision={row['T_PRECISION']}: bitrate={row['VS_P32_BITRATE_PERCENT']:+.3f}%,plan_time={row['VS_P32_PLAN_TIME_PERCENT']:+.1f}%,total_encode={row['VS_P32_TOTAL_ENCODE_TIME_PERCENT']:+.1f}%,fallback={row['FALLBACK_PERCENT']:.1f}%,boundaries={row['LOWER_BOUNDARY_PERCENT']:.1f}%/{row['UPPER_BOUNDARY_PERCENT']:.1f}%")
    print("leave-one-dataset-out:")
    for held_out in dataset_suffixes:
        training=[dataset for dataset in dataset_suffixes if dataset!=held_out]
        best_row=min(ranking,key=lambda row:geometric_mean([1+row[f"{dataset}_BITRATE_PERCENT"]/100 for dataset in training]))
        training_ratio=geometric_mean([1+best_row[f"{dataset}_BITRATE_PERCENT"]/100 for dataset in training])
        print(f"  {held_out}: precision={best_row['T_PRECISION']},train={100*(training_ratio-1):+.3f}%,held={best_row[f'{held_out}_BITRATE_PERCENT']:+.3f}%")
    print(f"写入排名：{output}")

if __name__=="__main__":
    main()
