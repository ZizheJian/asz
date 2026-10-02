import csv
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={"APS_Kaz":"aps_kaz.csv","Aramco":"aramco.csv","CLDICE":"cldice.csv","Isabel_Pf01":"isabel.csv","LETKF_PRES":"letkf.csv","VideoLLaVA":"videollava.csv"}

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def main():
    results=[]
    for dataset,suffix in dataset_suffixes.items():
        rows=read_rows(project_root/"results"/f"predictor_family_rd_extremes_{suffix}")
        cubic={float(row["REL_EB"]):row for row in rows if row["METHOD"]=="asz_threshold_0"}
        quintic={float(row["REL_EB"]):row for row in rows if row["METHOD"]=="asz_threshold_1e6"}
        if len(cubic)!=5 or len(quintic)!=5 or set(cubic)!=set(quintic):
            raise ValueError(f"{dataset}的两条RD曲线不完整")
        mse_ratios=[]
        for rel_eb in cubic:
            if cubic[rel_eb]["PREDICTOR_FAMILY"]!="cubic" or quintic[rel_eb]["PREDICTOR_FAMILY"]!="quintic":
                raise ValueError(f"{dataset},rel_eb={rel_eb}的极端阈值没有得到目标family")
            for field in ("CUBIC_MSE","QUINTIC_MSE","PREDICTOR_FAMILY_DIRECTION","PREDICTOR_FAMILY_SAMPLES"):
                if cubic[rel_eb][field]!=quintic[rel_eb][field]:
                    raise ValueError(f"{dataset},rel_eb={rel_eb}的{field}在两次运行间不一致")
            mse_ratios.append(float(cubic[rel_eb]["QUINTIC_MSE"])/float(cubic[rel_eb]["CUBIC_MSE"]))
        cubic_curve=[(float(row["PSNR"]),float(row["BR"])) for row in cubic.values()]
        quintic_curve=[(float(row["PSNR"]),float(row["BR"])) for row in quintic.values()]
        bitrate_ratio,_=compare_curves(quintic_curve,cubic_curve)
        mse_ratio=geometric_mean(mse_ratios)
        mse_family="quintic" if mse_ratio<1 else "cubic"
        rd_family="quintic" if bitrate_ratio<1 else "cubic"
        results.append({"DATASET":dataset,"MSE_RATIO_GEOMEAN":mse_ratio,"MSE_RATIO_MIN":min(mse_ratios),"MSE_RATIO_MAX":max(mse_ratios),"MSE_PREFERS":mse_family,"QUINTIC_VS_CUBIC_BITRATE_PERCENT":100*(bitrate_ratio-1),"RD_PREFERS":rd_family,"AGREES":mse_family==rd_family})
    output=project_root/"csv/predictor_family_rd_extremes.csv"
    temporary_path=output.with_name(output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=results[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    temporary_path.replace(output)
    for row in results:
        print(f"{row['DATASET']}: mse_ratio={row['MSE_RATIO_GEOMEAN']:.6f},quintic_bitrate={row['QUINTIC_VS_CUBIC_BITRATE_PERCENT']:+.3f}%,winner={row['RD_PREFERS']}")
    print(f"MSE/RD agreement: {sum(row['AGREES'] for row in results)}/{len(results)}")
    print(f"写入结果：{output}")

if __name__=="__main__":
    main()
