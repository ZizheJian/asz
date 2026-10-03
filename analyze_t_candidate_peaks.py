import csv
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={"APS_Kaz":"aps_kaz.csv","Aramco":"aramco.csv","CLDICE":"cldice.csv","Isabel_Pf01":"isabel.csv","LETKF_PRES":"letkf.csv","VideoLLaVA":"videollava.csv"}
baseline_method="asz_t_full"
candidate_method="asz_t_block_peaks"
legacy_candidate_method="asz_t_block_peaks_9"

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def paired_ratio(candidate_rows,baseline_rows,key):
    return geometric_mean([float(row[key])/float(baseline_rows[point][key]) for point,row in candidate_rows.items()])

def paired_sum_ratio(candidate_rows,baseline_rows,keys):
    return geometric_mean([sum(float(row[key]) for key in keys)/sum(float(baseline_rows[point][key]) for key in keys) for point,row in candidate_rows.items()])

def main():
    rows_by_method={baseline_method:{},candidate_method:{}}
    curves={method:{dataset:[] for dataset in dataset_suffixes} for method in rows_by_method}
    for dataset,suffix in dataset_suffixes.items():
        for row in read_rows(project_root/"results"/f"t_candidate_block_peaks_{suffix}"):
            method=row["METHOD"]
            if method==legacy_candidate_method:
                method=candidate_method
            point=(dataset,float(row["REL_EB"]))
            rows_by_method[method][point]=row
            curves[method][dataset].append((float(row["PSNR"]),float(row["BR"])))
    expected={(dataset,rel_eb) for dataset in dataset_suffixes for rel_eb in (0.1,0.01,0.001,0.0001,0.00001)}
    for method,rows in rows_by_method.items():
        if set(rows)!=expected:
            raise ValueError(f"{method}结果不完整：expected={len(expected)},actual={len(rows)}")
    dataset_ratios={}
    winning_fractions={}
    for dataset in dataset_suffixes:
        dataset_ratios[dataset],winning_fractions[dataset]=compare_curves(curves[candidate_method][dataset],curves[baseline_method][dataset])
    candidate_rows=rows_by_method[candidate_method]
    baseline_rows=rows_by_method[baseline_method]
    row={
        "BLOCK_T_POLICY":"peaks",
        "VS_FULL_BITRATE_PERCENT":100*(geometric_mean(dataset_ratios.values())-1),
        "VS_FULL_COMPRESSION_TIME_PERCENT":100*(paired_ratio(candidate_rows,baseline_rows,"COMPRESSION_TIME")-1),
        "VS_FULL_DECOMPRESSION_TIME_PERCENT":100*(paired_ratio(candidate_rows,baseline_rows,"DECOMPRESSION_TIME")-1),
        "VS_FULL_ONLINE_ROUNDTRIP_TIME_PERCENT":100*(paired_sum_ratio(candidate_rows,baseline_rows,("COMPRESSION_TIME","DECOMPRESSION_TIME"))-1),
        "VS_FULL_PLAN_TIME_PERCENT":100*(paired_ratio(candidate_rows,baseline_rows,"GENERATE_CONFIG_TIME")-1),
        **{f"{dataset}_BITRATE_PERCENT":100*(ratio-1) for dataset,ratio in dataset_ratios.items()},
        **{f"{dataset}_WINNING_PSNR_FRACTION":winning_fractions[dataset] for dataset in dataset_suffixes},
    }
    output=project_root/"csv/t_candidate_peaks_ranking.csv"
    temporary_path=output.with_name(output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=row.keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
    temporary_path.replace(output)
    print(f"bitrate={row['VS_FULL_BITRATE_PERCENT']:+.6f}%")
    print(f"compression_time={row['VS_FULL_COMPRESSION_TIME_PERCENT']:+.3f}%")
    print(f"decompression_time={row['VS_FULL_DECOMPRESSION_TIME_PERCENT']:+.3f}%")
    print(f"online_roundtrip_time={row['VS_FULL_ONLINE_ROUNDTRIP_TIME_PERCENT']:+.3f}%")
    print(f"plan_time={row['VS_FULL_PLAN_TIME_PERCENT']:+.3f}%")
    for dataset in dataset_suffixes:
        print(f"{dataset}: bitrate={row[f'{dataset}_BITRATE_PERCENT']:+.6f}%,winning_psnr_fraction={100*winning_fractions[dataset]:.2f}%")
    print(f"写入排名：{output}")

if __name__=="__main__":
    main()
