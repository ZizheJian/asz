import argparse,csv,itertools,math
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean

project_root=Path(__file__).resolve().parent
dataset_suffixes={
    "APS_Kaz":"aps_kaz",
    "Aramco":"aramco",
    "CLDICE":"cldice",
    "Isabel_Pf01":"isabel",
    "LETKF_PRES":"letkf",
    "VideoLLaVA":"videollava",
}
rel_eb_list=(0.1,0.01,0.001,0.0001,0.00001)
ratio_list=(2,4,8,16,32,64)

def read_rows(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))

def is_smooth(policy):
    return all(left<=right<=2*left for left,right in zip(policy,policy[1:]))

def is_monotonic(policy):
    return all(left<=right for left,right in zip(policy,policy[1:]))

def main():
    parser=argparse.ArgumentParser(description="枚举逐误差界block_pivot_ratio规则")
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--baseline",type=Path,default=project_root/"csv/tuning_results.csv")
    parser.add_argument("--output",type=Path,default=project_root/"results/block_ratio_policy_ranking.csv")
    arguments=parser.parse_args()

    baseline={}
    for row in read_rows(arguments.baseline):
        baseline.setdefault(row["DATASET"],[]).append((float(row["ASZ_PSNR"]),float(row["ASZ_BR"])))

    grid={}
    for dataset,suffix in dataset_suffixes.items():
        path=arguments.result_directory/f"block_ratio_grid_{suffix}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"缺少grid结果：{path}")
        for row in read_rows(path):
            match=row["METHOD"].removeprefix("asz_b")
            ratio=int(match)
            rel_eb=float(row["REL_EB"])
            grid.setdefault(dataset,{})[(rel_eb,ratio)]=(float(row["PSNR"]),float(row["BR"]))
        expected={(rel_eb,ratio) for rel_eb in rel_eb_list for ratio in ratio_list}
        if set(grid[dataset])!=expected:
            raise ValueError(f"{dataset}的grid不完整")

    ranking=[]
    for policy in itertools.product(ratio_list,repeat=len(rel_eb_list)):
        dataset_ratios={}
        winning_fractions={}
        for dataset in dataset_suffixes:
            curve=[grid[dataset][(rel_eb,ratio)] for rel_eb,ratio in zip(rel_eb_list,policy)]
            rate_ratio,winning_fraction=compare_curves(curve,baseline[dataset])
            dataset_ratios[dataset]=rate_ratio
            winning_fractions[dataset]=winning_fraction
        ranking.append({
            **{f"RATIO_{rel_eb:g}":ratio for rel_eb,ratio in zip(rel_eb_list,policy)},
            "MONOTONIC":int(is_monotonic(policy)),
            "SMOOTH":int(is_smooth(policy)),
            "VS_CURRENT_PERCENT":100*(geometric_mean(dataset_ratios.values())-1),
            "MEAN_COMMON_PSNR_WIN_PERCENT":100*sum(winning_fractions.values())/len(winning_fractions),
            **{f"{dataset}_PERCENT":100*(dataset_ratios[dataset]-1) for dataset in dataset_suffixes},
        })
    ranking.sort(key=lambda row:row["VS_CURRENT_PERCENT"])

    arguments.output.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=arguments.output.with_name(arguments.output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=ranking[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    temporary_path.replace(arguments.output)

    best=ranking[0]
    best_monotonic=next(row for row in ranking if row["MONOTONIC"])
    best_smooth=next(row for row in ranking if row["SMOOTH"])
    current=next(row for row in ranking if tuple(row[f"RATIO_{rel_eb:g}"] for rel_eb in rel_eb_list)==(4,4,4,64,64))
    for name,row in (("unrestricted",best),("monotonic",best_monotonic),("smooth",best_smooth),("current",current)):
        policy=tuple(row[f"RATIO_{rel_eb:g}"] for rel_eb in rel_eb_list)
        print(f"{name}: policy={policy},vs_current={row['VS_CURRENT_PERCENT']:+.3f}%")
    print(f"写入排名：{arguments.output}")

if __name__=="__main__":
    main()
