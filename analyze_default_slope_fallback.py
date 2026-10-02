import csv
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={"APS_Kaz":"aps_kaz.csv","Aramco":"aramco.csv","CLDICE":"cldice.csv","Isabel_Pf01":"isabel.csv","LETKF_PRES":"letkf.csv","VideoLLaVA":"videollava.csv"}
fallbacks=(30,100,300,1000,10000)

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def main():
    methods={fallback:f"asz_slope_f{fallback}" for fallback in fallbacks}
    rows_by_method={method:{} for method in methods.values()}
    curves={method:{} for method in methods.values()}
    for dataset,suffix in dataset_suffixes.items():
        for row in read_rows(project_root/"results"/f"default_slope_fallback_{suffix}"):
            point=(dataset,float(row["REL_EB"]))
            rows_by_method[row["METHOD"]][point]=row
    for row in read_rows(project_root/"results/default_slope_no_cap_aps.csv"):
        rows_by_method[row["METHOD"]][("APS_Kaz",float(row["REL_EB"]))]=row
    for method,rows in rows_by_method.items():
        for (dataset,_),row in rows.items():
            curves[method].setdefault(dataset,[]).append((float(row["PSNR"]),float(row["BR"])))
    baseline_method=methods[10000]
    expected_points={(dataset,rel_eb) for dataset in dataset_suffixes for rel_eb in (0.1,0.01,0.001,0.0001,0.00001)}
    ranking=[]
    for fallback,method in methods.items():
        if set(rows_by_method[method])!=expected_points:
            raise ValueError(f"{method}结果不完整：expected={len(expected_points)},actual={len(rows_by_method[method])}")
        dataset_ratios={dataset:compare_curves(curves[method][dataset],curves[baseline_method][dataset])[0] for dataset in dataset_suffixes}
        fallback_count=sum(row["DEFAULT_SLOPE_FALLBACK_USED"]=="True" for row in rows_by_method[method].values())
        ranking.append({"DEFAULT_SLOPE_FALLBACK":fallback,"VS_10000_BITRATE_PERCENT":100*(geometric_mean(dataset_ratios.values())-1),"FALLBACK_POINT_COUNT":fallback_count,**{f"{dataset}_BITRATE_PERCENT":100*(value-1) for dataset,value in dataset_ratios.items()}})
    ranking.sort(key=lambda row:row["VS_10000_BITRATE_PERCENT"])
    output=project_root/"csv/default_slope_fallback_ranking.csv"
    temporary_path=output.with_name(output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=ranking[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    temporary_path.replace(output)
    for index,row in enumerate(ranking,1):
        print(f"{index}. fallback={row['DEFAULT_SLOPE_FALLBACK']}: bitrate={row['VS_10000_BITRATE_PERCENT']:+.3f}%,fallback_points={row['FALLBACK_POINT_COUNT']}")
    print(f"写入排名：{output}")

if __name__=="__main__":
    main()
