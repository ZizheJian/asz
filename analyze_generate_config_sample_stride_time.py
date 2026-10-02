import csv,math
from pathlib import Path

from analyze_layer_eb_screen import geometric_mean

project_root=Path(__file__).resolve().parent
suffixes=("aps_kaz.csv","aramco.csv","cldice.csv","isabel.csv","letkf.csv","videollava.csv")

def main():
    plan_ratios=[]
    encode_ratios=[]
    for suffix in suffixes:
        with open(project_root/"results"/f"generate_config_sample_stride_timing_{suffix}",newline="",encoding="utf-8") as input_file:
            rows={row["METHOD"]:row for row in csv.DictReader(input_file)}
        for repetition in "abc":
            stride5=rows[f"asz_stride5_{repetition}"]
            stride8=rows[f"asz_stride8_{repetition}"]
            plan5=float(stride5["GENERATE_CONFIG_TIME"])
            plan8=float(stride8["GENERATE_CONFIG_TIME"])
            encode5=plan5+float(stride5["COMPRESSION_TIME"])
            encode8=plan8+float(stride8["COMPRESSION_TIME"])
            plan_ratios.append(plan5/plan8)
            encode_ratios.append(encode5/encode8)
    print(f"pairs={len(plan_ratios)}")
    print(f"stride5_vs_stride8_plan_time={100*(geometric_mean(plan_ratios)-1):+.3f}%")
    print(f"stride5_vs_stride8_total_encode_time={100*(geometric_mean(encode_ratios)-1):+.3f}%")

if __name__=="__main__":
    main()
