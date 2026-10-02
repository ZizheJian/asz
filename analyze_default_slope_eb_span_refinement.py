import csv
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={"APS_Kaz":"aps_kaz.csv","Aramco":"aramco.csv","CLDICE":"cldice.csv","Isabel_Pf01":"isabel.csv","LETKF_PRES":"letkf.csv","VideoLLaVA":"videollava.csv"}
spans={1.2:("refinement","asz_span_12"),1.3:("refinement","asz_span_13"),1.5:("initial","asz_span_15"),1.75:("refinement","asz_span_175"),2:("initial","asz_span_2"),3:("initial","asz_span_3"),4:("initial","asz_span_4")}

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def main():
    curves={span:{} for span in spans}
    for dataset,suffix in dataset_suffixes.items():
        rows_by_group={"initial":read_rows(project_root/"results"/f"default_slope_eb_span_{suffix}"),"refinement":read_rows(project_root/"results"/f"default_slope_eb_span_refinement_{suffix}")}
        for span,(group,method) in spans.items():
            rows=[row for row in rows_by_group[group] if row["METHOD"]==method]
            if len(rows)!=5:
                raise ValueError(f"span={span},dataset={dataset}结果数应为5，实际为{len(rows)}")
            curves[span][dataset]=[(float(row["PSNR"]),float(row["BR"])) for row in rows]
    ranking=[]
    for span in spans:
        dataset_ratios={dataset:compare_curves(curves[span][dataset],curves[2][dataset])[0] for dataset in dataset_suffixes}
        ranking.append({"DEFAULT_SLOPE_EB_SPAN":span,"VS_SPAN_2_BITRATE_PERCENT":100*(geometric_mean(dataset_ratios.values())-1),**{f"{dataset}_BITRATE_PERCENT":100*(value-1) for dataset,value in dataset_ratios.items()}})
    ranking.sort(key=lambda row:row["VS_SPAN_2_BITRATE_PERCENT"])
    output=project_root/"csv/default_slope_eb_span_refinement_ranking.csv"
    temporary_path=output.with_name(output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=ranking[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    temporary_path.replace(output)
    for index,row in enumerate(ranking,1):
        print(f"{index}. span={row['DEFAULT_SLOPE_EB_SPAN']}: bitrate={row['VS_SPAN_2_BITRATE_PERCENT']:+.3f}%")
    print(f"写入排名：{output}")

if __name__=="__main__":
    main()
