import csv,itertools,math
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={
    "APS_Kaz":"aps_kaz.csv",
    "Aramco":"aramco.csv",
    "CLDICE":"cldice.csv",
    "Isabel_Pf01":"isabel.csv",
    "LETKF_PRES":"letkf.csv",
    "VideoLLaVA":"videollava.csv",
}
rel_eb_list=(0.1,0.01,0.001,0.0001,0.00001)
coarse_ratios=(2,3,4)
fine_ratios=(32,40,48,64,80,96,128)
source_prefixes=("layer_eb_recheck_","layer_block_decoupling_","layer_block_local_","layer_block_fine_expansion_")
coarse_sources={2:"asz_l14_b2_40",3:"asz_l14_b3_40",4:"asz_l14_e76"}
fine_sources={32:"asz_l14_b3_32",40:"asz_l14_b3_40",48:"asz_l14_b3_48",64:"asz_l14_e76",80:"asz_l14_b3_80",96:"asz_l14_b3_96",128:"asz_l14_b3_128"}

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def policy_curve(results,dataset,coarse_ratio,fine_ratio):
    curve=[]
    for rel_eb in rel_eb_list:
        method=fine_sources[fine_ratio] if rel_eb<=1e-4 else coarse_sources[coarse_ratio]
        curve.append(results[(method,dataset,rel_eb)])
    return curve

def main():
    results={}
    for dataset,suffix in dataset_suffixes.items():
        for prefix in source_prefixes:
            for row in read_rows(project_root/"results"/f"{prefix}{suffix}"):
                results[(row["METHOD"],dataset,float(row["REL_EB"]))]=(float(row["PSNR"]),float(row["BR"]))
    required_keys={("asz_l12_e76",dataset,rel_eb) for dataset in dataset_suffixes for rel_eb in rel_eb_list}
    required_keys|={(method,dataset,rel_eb) for method in coarse_sources.values() for dataset in dataset_suffixes for rel_eb in rel_eb_list if rel_eb>1e-4}
    required_keys|={(method,dataset,rel_eb) for method in fine_sources.values() for dataset in dataset_suffixes for rel_eb in rel_eb_list if rel_eb<=1e-4}
    missing=[key for key in required_keys if key not in results]
    if missing:
        raise ValueError(f"缺少策略结果：{missing[0]}，共{len(missing)}项")

    reference_policy={dataset:policy_curve(results,dataset,3,40) for dataset in dataset_suffixes}
    reference_l12={dataset:[results[("asz_l12_e76",dataset,rel_eb)] for rel_eb in rel_eb_list] for dataset in dataset_suffixes}
    ranking=[]
    policy_dataset_ratios={}
    for coarse_ratio,fine_ratio in itertools.product(coarse_ratios,fine_ratios):
        dataset_ratios={}
        l12_ratios={}
        winning_fractions={}
        for dataset in dataset_suffixes:
            curve=policy_curve(results,dataset,coarse_ratio,fine_ratio)
            dataset_ratios[dataset],winning_fractions[dataset]=compare_curves(curve,reference_policy[dataset])
            l12_ratios[dataset],_=compare_curves(curve,reference_l12[dataset])
        policy=(coarse_ratio,fine_ratio)
        policy_dataset_ratios[policy]=dataset_ratios
        ranking.append({
            "COARSE_BLOCK_PIVOT_RATIO":coarse_ratio,
            "FINE_BLOCK_PIVOT_RATIO":fine_ratio,
            "VS_B3_40_PERCENT":100*(geometric_mean(dataset_ratios.values())-1),
            "VS_L12_B4_64_PERCENT":100*(geometric_mean(l12_ratios.values())-1),
            "MEAN_COMMON_PSNR_WIN_PERCENT":100*sum(winning_fractions.values())/len(winning_fractions),
            **{f"{dataset}_VS_B3_40_PERCENT":100*(dataset_ratios[dataset]-1) for dataset in dataset_suffixes},
        })
    ranking.sort(key=lambda row:row["VS_B3_40_PERCENT"])

    output=project_root/"csv/layer_block_policy_ranking.csv"
    temporary_path=output.with_name(output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=ranking[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    temporary_path.replace(output)
    for index,row in enumerate(ranking,1):
        print(f"{index:2d}. ({row['COARSE_BLOCK_PIVOT_RATIO']},{row['FINE_BLOCK_PIVOT_RATIO']}): vs_b3_40={row['VS_B3_40_PERCENT']:+.3f}%,vs_l12={row['VS_L12_B4_64_PERCENT']:+.3f}%")

    print("leave-one-dataset-out:")
    for held_out in dataset_suffixes:
        training=[dataset for dataset in dataset_suffixes if dataset!=held_out]
        best=min(policy_dataset_ratios,key=lambda policy:geometric_mean([policy_dataset_ratios[policy][dataset] for dataset in training]))
        training_ratio=geometric_mean([policy_dataset_ratios[best][dataset] for dataset in training])
        held_out_ratio=policy_dataset_ratios[best][held_out]
        print(f"  {held_out}: policy={best},train={100*(training_ratio-1):+.3f}%,held={100*(held_out_ratio-1):+.3f}%")
    best=(ranking[0]["COARSE_BLOCK_PIVOT_RATIO"],ranking[0]["FINE_BLOCK_PIVOT_RATIO"])
    boundary=best[0] in (coarse_ratios[0],coarse_ratios[-1]) or best[1] in (fine_ratios[0],fine_ratios[-1])
    print(f"best={best},boundary={boundary}")
    print(f"写入排名：{output}")

if __name__=="__main__":
    main()
