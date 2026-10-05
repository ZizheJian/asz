import argparse,csv
from pathlib import Path

from analyze_layer_eb_screen import compare_curves,geometric_mean
from promote_asz_tuning_results import compare_to_envelope

project_root=Path(__file__).resolve().parent

def read_curves(path):
    curves={}
    with open(path,newline="",encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            curves.setdefault(row["DATA_PATH"],{}).setdefault(row["METHOD"],[]).append((float(row["PSNR"]),float(row["BR"])))
    return curves

def cr_percent(bitrate_ratio):
    return 100*(1/bitrate_ratio-1)

def main():
    parser=argparse.ArgumentParser(description="按等PSNR比较跨time step共享plan、自生成plan、SZ3和QoZ")
    parser.add_argument("result",type=Path)
    parser.add_argument("--shared-method",default="asz_middle_plan")
    parser.add_argument("--self-method",default="asz_self_plan")
    parser.add_argument("--output",type=Path)
    arguments=parser.parse_args()
    result_path=arguments.result if arguments.result.is_absolute() else project_root/arguments.result
    curves=read_curves(result_path)
    required={arguments.shared_method,arguments.self_method,"sz3","qoz"}
    rows=[]
    ratios={"self":[],"sz3":[],"qoz":[],"best":[]}
    wins={"self":[],"sz3":[],"qoz":[],"best":[]}
    for data_path,methods in sorted(curves.items()):
        missing=required-methods.keys()
        if missing:
            raise ValueError(f"{data_path}缺少method：{','.join(sorted(missing))}")
        shared=methods[arguments.shared_method]
        comparisons={}
        for key,method in (("self",arguments.self_method),("sz3","sz3"),("qoz","qoz")):
            ratio,win=compare_curves(shared,methods[method])
            comparisons[key]=(ratio,win)
            ratios[key].append(ratio)
            wins[key].append(win)
        best_ratio,best_win,interval=compare_to_envelope(shared,[methods["sz3"],methods["qoz"]])
        ratios["best"].append(best_ratio)
        wins["best"].append(best_win)
        rows.append({
            "DATA_PATH":data_path,
            "SHARED_VS_SELF_CR_PERCENT":cr_percent(comparisons["self"][0]),
            "SHARED_VS_SELF_WIN_PERCENT":100*comparisons["self"][1],
            "SHARED_VS_SZ3_CR_PERCENT":cr_percent(comparisons["sz3"][0]),
            "SHARED_VS_QOZ_CR_PERCENT":cr_percent(comparisons["qoz"][0]),
            "SHARED_VS_BEST_CR_PERCENT":cr_percent(best_ratio),
            "SHARED_VS_BEST_WIN_PERCENT":100*best_win,
            "COMMON_PSNR_MIN":interval[0],
            "COMMON_PSNR_MAX":interval[1]
        })
    aggregate={
        "DATA_PATH":"__GEOMETRIC_MEAN__",
        "SHARED_VS_SELF_CR_PERCENT":cr_percent(geometric_mean(ratios["self"])),
        "SHARED_VS_SELF_WIN_PERCENT":100*sum(wins["self"])/len(wins["self"]),
        "SHARED_VS_SZ3_CR_PERCENT":cr_percent(geometric_mean(ratios["sz3"])),
        "SHARED_VS_QOZ_CR_PERCENT":cr_percent(geometric_mean(ratios["qoz"])),
        "SHARED_VS_BEST_CR_PERCENT":cr_percent(geometric_mean(ratios["best"])),
        "SHARED_VS_BEST_WIN_PERCENT":100*sum(wins["best"])/len(wins["best"]),
        "COMMON_PSNR_MIN":"",
        "COMMON_PSNR_MAX":""
    }
    rows.append(aggregate)
    fieldnames=list(aggregate)
    output_path=arguments.output
    if output_path is None:
        output_path=result_path.with_name(result_path.stem+"_analysis.csv")
    elif not output_path.is_absolute():
        output_path=project_root/output_path
    output_path.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=output_path.with_name(output_path.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary_path.replace(output_path)
    worst=min(rows[:-1],key=lambda row:row["SHARED_VS_SELF_CR_PERCENT"])
    print(f"time_step_count={len(rows)-1}")
    print(f"shared_vs_self_cr_percent={aggregate['SHARED_VS_SELF_CR_PERCENT']:.6f}")
    print(f"shared_vs_sz3_cr_percent={aggregate['SHARED_VS_SZ3_CR_PERCENT']:.6f}")
    print(f"shared_vs_qoz_cr_percent={aggregate['SHARED_VS_QOZ_CR_PERCENT']:.6f}")
    print(f"shared_vs_best_cr_percent={aggregate['SHARED_VS_BEST_CR_PERCENT']:.6f}")
    print(f"shared_vs_best_win_percent={aggregate['SHARED_VS_BEST_WIN_PERCENT']:.6f}")
    print(f"worst_shared_vs_self_cr_percent={worst['SHARED_VS_SELF_CR_PERCENT']:.6f},data={worst['DATA_PATH']}")
    print(f"output={output_path}")

if __name__=="__main__":
    main()
