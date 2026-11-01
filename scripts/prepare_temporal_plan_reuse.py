import argparse,json,os,sys
from pathlib import Path

project_root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(project_root))

from analyze_temporal_plan_reuse import bounds,field_paths,fields,plan_path,reuse_windows,self_csv_path,self_method,transfer_csv_path,transfer_method,transfer_pairs,uses_list


config_root=project_root/"configs/.temporal_plan_reuse"
output_root="/anvil/scratch/x-zjian1/asz-temporal-plan-reuse"


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=path.with_name(path.name+".tmp")
    with open(temporary_path,"w",encoding="utf-8") as output_file:
        json.dump(value,output_file,indent=2)
        output_file.write("\n")
    os.replace(temporary_path,path)


def task(field,data_path,method,summary_csv,output_name):
    return [{"data_path_list":[data_path],"data_shape":fields[field]["shape"],"rel_eb_list":list(bounds),"method_list":[method],"cleanup_after_each_test":True,"comparison_baseline":method["name"],"summary_csv":str(summary_csv),"output_directory":f"{output_root}/{field}/{output_name}"}]


# self阶段为每个文件生成并保存自己的plan，transfer阶段对每个(代表,目标)对只压缩一次，供所有共享该对的uses复用
def prepare(field):
    labels=fields[field]["labels"]
    paths=field_paths(field)
    directory=config_root/field
    for stale in directory.glob("*.json") if directory.is_dir() else ():
        stale.unlink()
    for label,path in zip(labels,paths):
        method={"name":self_method,"compressor":"asz","write_plan":str(plan_path(field,label))}
        write_json(directory/f"self_{label}.json",task(field,path,method,self_csv_path(field,label),f"self_{label}"))
    pairs=transfer_pairs(len(labels))
    for representative,target in pairs:
        representative_label=labels[representative]
        target_label=labels[target]
        method={"name":transfer_method(representative_label),"compressor":"asz","read_plan":str(plan_path(field,representative_label))}
        write_json(directory/f"transfer_{representative_label}_to_{target_label}.json",task(field,paths[target],method,transfer_csv_path(field,representative_label,target_label),f"transfer_{representative_label}_to_{target_label}"))
    missing=sum(not Path(path).is_file() for path in paths)
    print(f"{field}: {len(labels)} self configs,{len(pairs)} transfer configs,{missing} missing inputs")
    for uses in uses_list[1:]:
        windows=reuse_windows(len(labels),uses)
        print("  uses=%d: "%uses+" ".join(f"{labels[members[0]]}-{labels[members[-1]]}@{labels[representative]}" for representative,members in windows))


# 只列出summary CSV尚不存在的配置，便于作业中断后续跑
def pending(field,phase):
    for path in sorted((config_root/field).glob(f"{phase}_*.json")):
        with open(path,encoding="utf-8") as input_file:
            summary_csv=Path(json.load(input_file)[0]["summary_csv"])
        if not summary_csv.is_file():
            print(path)


def main():
    parser=argparse.ArgumentParser(description="Prepare launcher configurations for the temporal plan-reuse experiment")
    parser.add_argument("--field",nargs="+",choices=list(fields),default=list(fields))
    parser.add_argument("--pending",choices=("self","transfer"),help="list unfinished configurations of one phase instead of preparing")
    arguments=parser.parse_args()
    for field in arguments.field:
        pending(field,arguments.pending) if arguments.pending else prepare(field)


if __name__=="__main__":
    main()
