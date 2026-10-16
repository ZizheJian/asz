import argparse,csv,re
from pathlib import Path

from analyze_layer_eb_screen import compare_curves

project_root=Path(__file__).resolve().parent
fieldnames=["DATASET","GROUP_COUNT","PLAN_GENERATION_FRACTION","MEAN_CR_LOSS_PERCENT","MAX_CR_LOSS_PERCENT","MAX_LOSS_STEP"]


def read_curves(path,method=None):
    curves={}
    with open(path,newline="",encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            if method is not None and row.get("METHOD")!=method:
                continue
            match=re.search(r"Pf(\d+)\.bin$",row["DATA_PATH"])
            if match is None:
                raise ValueError(f"无法解析Isabel time step：{row['DATA_PATH']}")
            step=int(match.group(1))
            curves.setdefault(step,[]).append((float(row["PSNR"]),float(row["BR"])))
    return curves


def cr_loss_percent(candidate,self_curve):
    bitrate_ratio,_=compare_curves(candidate,self_curve)
    return 100*(1-1/bitrate_ratio)


def validate_curves(curves,label):
    if set(curves)!=set(range(1,49)):
        raise ValueError(f"{label}没有覆盖48个time step")
    for step,points in curves.items():
        if len(points)!=5:
            raise ValueError(f"{label}的Pf{step:02d}应有5个RD点，实际有{len(points)}个")


def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".tmp")
    with open(temporary,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main():
    parser=argparse.ArgumentParser(description="汇总分段复用plan相对self-plan的等PSNR压缩率损失")
    parser.add_argument("--legacy-result",type=Path,default=project_root/"results/isabel_plan_transfer.csv")
    parser.add_argument("--grouped-directory",type=Path,default=project_root/"results/grouped-plan-transfer")
    parser.add_argument("--output",type=Path,default=project_root/"results/isabel_grouped_plan_transfer_analysis.csv")
    arguments=parser.parse_args()

    self_curves=read_curves(arguments.legacy_result,"asz_self_plan")
    shared_curves=read_curves(arguments.legacy_result,"asz_pf24_plan")
    with open(project_root/"results/final_eighteen_refresh_isabel_pf24.csv",newline="",encoding="utf-8") as input_file:
        self_curves[24]=[(float(row["PSNR"]),float(row["BR"])) for row in csv.DictReader(input_file) if row["METHOD"]=="asz"]
    shared_curves[24]=self_curves[24]
    validate_curves(self_curves,"self-plan曲线")
    validate_curves(shared_curves,"Pf24-plan曲线")

    candidates={1:shared_curves,48:self_curves}
    for path in sorted(arguments.grouped_directory.glob("isabel_grouped_plan_transfer_k*.csv")):
        match=re.search(r"k(\d+)\.csv$",path.name)
        if match is None:
            continue
        candidates[int(match.group(1))]=read_curves(path)

    rows=[]
    for group_count,curves in sorted(candidates.items()):
        if set(curves)!=set(range(1,49)):
            print(f"skip_incomplete_group_count={group_count},steps={len(curves)}")
            continue
        validate_curves(curves,f"K={group_count}分组曲线")
        losses={step:cr_loss_percent(curves[step],self_curves[step]) for step in range(1,49)}
        max_step=max(losses,key=losses.get)
        rows.append({"DATASET":"Isabel P","GROUP_COUNT":group_count,"PLAN_GENERATION_FRACTION":group_count/48,"MEAN_CR_LOSS_PERCENT":sum(losses.values())/len(losses),"MAX_CR_LOSS_PERCENT":losses[max_step],"MAX_LOSS_STEP":max_step})
    write_csv(arguments.output,rows)
    for row in rows:
        print(f"groups={row['GROUP_COUNT']:2d},mean_cr_loss={row['MEAN_CR_LOSS_PERCENT']:.6f}%,max_cr_loss={row['MAX_CR_LOSS_PERCENT']:.6f}%@Pf{row['MAX_LOSS_STEP']:02d}")
    print(f"output={arguments.output}")


if __name__=="__main__":
    main()
