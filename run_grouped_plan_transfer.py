import argparse,csv,os
from pathlib import Path

from t1_start_compressors import load_plan,run_task,validate_data_file

project_root=Path(__file__).resolve().parent
default_data_directory=Path("/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/P")
default_plan_directory=project_root/"plans/transfer/isabel_self"
shape=[100,500,500]
rel_eb_list=[0.1,0.01,0.001,0.0001,0.00001]
fieldnames=["DATA_PATH","GROUP_COUNT","GROUP_ID","GROUP_FIRST_STEP","GROUP_LAST_STEP","REPRESENTATIVE_STEP","REL_EB","CR","BR","PSNR","COMPRESSION_TIME","DECOMPRESSION_TIME"]


def split_steps(group_count,step_count=48):
    if group_count<1 or group_count>step_count:
        raise ValueError(f"group_count必须在[1,{step_count}]内")
    groups=[]
    for group_id in range(group_count):
        first=group_id*step_count//group_count+1
        last=(group_id+1)*step_count//group_count
        representative=(first+last)//2
        groups.append((group_id,first,last,representative))
    return groups


def plan_path(plan_directory,representative):
    if representative==24:
        return plan_directory.parent/"isabel_p24.json"
    return plan_directory/f"Pf{representative:02d}.json"


def read_rows(path):
    if not path.is_file():
        return []
    with open(path,newline="",encoding="utf-8") as input_file:
        rows=list(csv.DictReader(input_file))
    if rows and list(rows[0])!=fieldnames:
        raise ValueError(f"已有结果字段不匹配：{path}")
    return rows


def write_rows(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".tmp")
    with open(temporary,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary,path)


def validate_inputs(data_directory,plan_directory,group_counts):
    for step in range(1,49):
        validate_data_file(data_directory/f"Pf{step:02d}.bin",shape)
    representatives={group[3] for group_count in group_counts for group in split_steps(group_count)}
    for representative in representatives:
        plans=load_plan(plan_path(plan_directory,representative))
        available={rel_eb for rel_eb,_,_ in plans}
        for rel_eb in rel_eb_list:
            if rel_eb not in available:
                raise ValueError(f"Pf{representative:02d} plan缺少rel_eb={rel_eb:g}")
    print(f"validated_steps=48,representative_plans={len(representatives)},group_counts={','.join(str(value) for value in group_counts)}")


def run_group_count(data_directory,plan_directory,output_directory,group_count):
    output_path=output_directory/f"isabel_grouped_plan_transfer_k{group_count:02d}.csv"
    rows=read_rows(output_path)
    completed={(int(row["GROUP_COUNT"]),row["DATA_PATH"],float(row["REL_EB"])) for row in rows}
    for group_id,first,last,representative in split_steps(group_count):
        representative_plan=plan_path(plan_directory,representative)
        for step in range(first,last+1):
            data_path=data_directory/f"Pf{step:02d}.bin"
            missing=[rel_eb for rel_eb in rel_eb_list if (group_count,str(data_path),rel_eb) not in completed]
            if not missing:
                continue
            task={"data_shape":shape,"rel_eb_list":missing,"method_list":[{"name":f"asz_group_{group_count:02d}","compressor":"asz","read_plan":str(representative_plan)}],"cleanup_after_each_test":True}
            records=run_task(task,data_path,False,False)
            for record in records:
                rows.append({"DATA_PATH":record["data_path"],"GROUP_COUNT":group_count,"GROUP_ID":group_id,"GROUP_FIRST_STEP":first,"GROUP_LAST_STEP":last,"REPRESENTATIVE_STEP":representative,"REL_EB":record["rel_eb"],"CR":record["cr"],"BR":record["br"],"PSNR":record["psnr"],"COMPRESSION_TIME":record["compression_time"],"DECOMPRESSION_TIME":record["decompression_time"]})
                completed.add((group_count,record["data_path"],record["rel_eb"]))
            rows.sort(key=lambda row:(int(row["GROUP_COUNT"]),row["DATA_PATH"],-float(row["REL_EB"])))
            write_rows(output_path,rows)
    print(f"completed_group_count={group_count},rows={len(rows)},output={output_path}")


def main():
    parser=argparse.ArgumentParser(description="用连续时间段中间时刻的plan评估Isabel plan transfer")
    parser.add_argument("--group-count",type=int,action="append")
    parser.add_argument("--data-directory",type=Path,default=default_data_directory)
    parser.add_argument("--plan-directory",type=Path,default=default_plan_directory)
    parser.add_argument("--output-directory",type=Path,default=project_root/"results/grouped-plan-transfer")
    parser.add_argument("--check",action="store_true")
    arguments=parser.parse_args()
    group_counts=arguments.group_count or [2,4,8,16]
    validate_inputs(arguments.data_directory,arguments.plan_directory,group_counts)
    if arguments.check:
        return
    for group_count in group_counts:
        run_group_count(arguments.data_directory,arguments.plan_directory,arguments.output_directory,group_count)


if __name__=="__main__":
    main()
