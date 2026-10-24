import argparse,csv,json,math,os,sys
from pathlib import Path

project_root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(project_root))

from analyze_final_evaluation import compare_curves


config_directory=project_root/"configs"
result_directory=project_root/"results/isabel_precip_transfer_parts"
output_directory="/anvil/scratch/x-zjian1/asz-isabel-precip-transfer"
plan_directory=f"{output_directory}/plans"
budgets=(1,2,4,8,16,48)
bounds=(.1,.01,.001,.0001,.00001)
paths=tuple(f"/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/PRECIP/PRECIPf{index:02d}.bin" for index in range(1,49))
shape=(100,500,500)


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".tmp")
    with open(temporary,"w",encoding="utf-8") as output_file:
        json.dump(value,output_file,indent=2)
        output_file.write("\n")
    os.replace(temporary,path)


def segment_bounds(count,budget):
    quotient,remainder=divmod(count,budget)
    begin=0
    segments=[]
    for segment_id in range(budget):
        size=quotient+(segment_id<remainder)
        end=begin+size
        representative=begin+(size-1)//2
        segments.append((begin,end,representative))
        begin=end
    if begin!=count:
        raise AssertionError("segment partition is incomplete")
    return segments


def prepare():
    self_task={"data_path_list":list(paths),"data_shape":list(shape),"rel_eb_list":list(bounds),"method_list":[{"name":"asz_self","compressor":"asz","write_plan":f"{plan_directory}/{{stem}}.json"}],"cleanup_after_each_test":True,"comparison_baseline":"asz_self","summary_csv":"results/isabel_precip_transfer_parts/self.csv","output_directory":f"{output_directory}/self"}
    write_json(config_directory/".isabel_precip_self.json",[self_task])
    metadata={"budgets":list(budgets),"bounds":list(bounds),"paths":list(paths),"segments":{}}
    for budget in budgets:
        tasks=[]
        metadata["segments"][str(budget)]=[]
        for segment_id,(begin,end,representative) in enumerate(segment_bounds(len(paths),budget)):
            representative_path=Path(paths[representative])
            summary=f"results/isabel_precip_transfer_parts/k{budget}_segment{segment_id:02d}.csv"
            tasks.append({"data_path_list":list(paths[begin:end]),"data_shape":list(shape),"rel_eb_list":list(bounds),"method_list":[{"name":f"asz_k{budget}","compressor":"asz","read_plan":f"{plan_directory}/{representative_path.stem}.json"}],"cleanup_after_each_test":True,"comparison_baseline":f"asz_k{budget}","summary_csv":summary,"output_directory":f"{output_directory}/k{budget}"})
            metadata["segments"][str(budget)].append({"segment":segment_id,"begin":begin+1,"end":end,"representative":representative+1,"representative_path":paths[representative],"summary_csv":summary})
        write_json(config_directory/f".isabel_precip_k{budget}.json",tasks)
    write_json(result_directory/"metadata.json",metadata)
    print(f"prepared self plan and {len(budgets)} transfer configurations")


def load_method_rows(path,method):
    with open(path,newline="",encoding="utf-8") as input_file:
        rows=[row for row in csv.DictReader(input_file) if row["METHOD"]==method]
    return rows


def curves_by_path(rows):
    grouped={}
    for row in rows:
        grouped.setdefault(row["DATA_PATH"],[]).append(row)
    for data_path,path_rows in grouped.items():
        if len(path_rows)!=len(bounds) or {float(row["REL_EB"]) for row in path_rows}!={float(bound) for bound in bounds}:
            raise ValueError(f"incomplete error-bound grid for {data_path}")
    return grouped


def psnr_bitrate(rows):
    return [(float(row["PSNR"]),float(row["BR"])) for row in rows]


def finalize():
    metadata_path=result_directory/"metadata.json"
    with open(metadata_path,encoding="utf-8") as input_file:
        metadata=json.load(input_file)
    self_rows=curves_by_path(load_method_rows(result_directory/"self.csv","asz_self"))
    if set(self_rows)!=set(paths):
        raise ValueError(f"self-plan results cover {len(self_rows)}/48 inputs")
    detail=[]
    summary=[]
    for budget in budgets:
        transfer_rows={}
        representative_by_path={}
        for segment in metadata["segments"][str(budget)]:
            part=project_root/segment["summary_csv"]
            grouped=curves_by_path(load_method_rows(part,f"asz_k{budget}"))
            overlap=set(grouped)&set(transfer_rows)
            if overlap:
                raise ValueError(f"duplicate K={budget} targets: {sorted(overlap)}")
            transfer_rows.update(grouped)
            for data_path in grouped:
                representative_by_path[data_path]=segment["representative_path"]
        if set(transfer_rows)!=set(paths):
            raise ValueError(f"K={budget} results cover {len(transfer_rows)}/48 inputs")
        losses=[]
        for data_path in paths:
            bit_rate_ratio=compare_curves(psnr_bitrate(transfer_rows[data_path]),psnr_bitrate(self_rows[data_path]))
            loss=100*(1-1/bit_rate_ratio)
            losses.append(loss)
            detail.append({"K":budget,"DATA_PATH":data_path,"REPRESENTATIVE_PATH":representative_by_path[data_path],"BIT_RATE_RATIO":bit_rate_ratio,"CR_LOSS_PERCENT":loss})
        summary.append({"K":budget,"MEAN_CR_LOSS_PERCENT":sum(losses)/len(losses),"MAX_CR_LOSS_PERCENT":max(losses),"MIN_CR_LOSS_PERCENT":min(losses)})
    result_directory.mkdir(parents=True,exist_ok=True)
    detail_path=result_directory/"detail.csv"
    summary_path=result_directory/"summary.csv"
    with open(detail_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=("K","DATA_PATH","REPRESENTATIVE_PATH","BIT_RATE_RATIO","CR_LOSS_PERCENT"),lineterminator="\n")
        writer.writeheader()
        writer.writerows(detail)
    with open(summary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=("K","MEAN_CR_LOSS_PERCENT","MAX_CR_LOSS_PERCENT","MIN_CR_LOSS_PERCENT"),lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)
    for row in summary:
        print(f"K={row['K']},mean_loss={row['MEAN_CR_LOSS_PERCENT']:.6f}%,max_loss={row['MAX_CR_LOSS_PERCENT']:.6f}%,min_loss={row['MIN_CR_LOSS_PERCENT']:.6f}%")


def main():
    parser=argparse.ArgumentParser(description="Prepare or summarize the Isabel PRECIP temporal plan-transfer experiment")
    parser.add_argument("--finalize",action="store_true")
    arguments=parser.parse_args()
    finalize() if arguments.finalize else prepare()


if __name__=="__main__":
    main()
