import argparse,csv,json,math,os
from pathlib import Path


project_root=Path(__file__).resolve().parents[1]
manifest_path=project_root/"configs/final_eighteen.json"
methods=["asz","sz3","qoz","zfp","sperr"]
groups={"small":range(0,9),"medium":range(9,14),"nyx":range(14,16),"apsu004":range(16,17)}


def task(dataset,output_directory,rel_eb_list=None,summary_csv=None,method_list=methods,comparison_baseline="asz"):
    result_path=dataset["results"]["asz"] if summary_csv is None else summary_csv
    return {"data_path_list":[dataset["data_path"]],"data_shape":dataset["shape"],"rel_eb_list":dataset["rel_eb_list"] if rel_eb_list is None else rel_eb_list,"method_list":method_list,"cleanup_after_each_test":True,"comparison_baseline":comparison_baseline,"summary_csv":f"results/{result_path}","output_directory":output_directory}


def write_json(path,value):
    with open(path,"w",encoding="utf-8") as output_file:
        json.dump(value,output_file,indent=2)
        output_file.write("\n")


def load_manifest():
    with open(manifest_path,encoding="utf-8") as input_file:
        return json.load(input_file)


def prepare():
    datasets=load_manifest()
    for group,indexes in groups.items():
        output_directory=f"/anvil/scratch/x-zjian1/asz-final18-rd/{group}"
        write_json(project_root/f"configs/.final18_rd_{group}.json",[task(datasets[index],output_directory) for index in indexes])
    apsu006=datasets[17]
    for index,rel_eb in enumerate(apsu006["rel_eb_list"]):
        part=f"final18_parts/apsu006_{index}.csv"
        output_directory=f"/anvil/scratch/x-zjian1/asz-final18-rd/apsu006_{index}"
        write_json(project_root/f"configs/.final18_rd_apsu006_{index}.json",[task(apsu006,output_directory,[rel_eb],part,["asz","sz3","qoz","zfp"])])
        sperr_part=f"final18_parts/apsu006_sperr_{index}.csv"
        write_json(project_root/f"configs/.final18_rd_apsu006_sperr_{index}.json",[task(apsu006,output_directory,[rel_eb],sperr_part,["sperr"],"sperr")])


# 只重跑部分method时，结果先写入final18_{name}，再由merge_rerun替换final18中对应的行
# asz在压缩器修改后重跑所有field的ASZ，timing在APSU上把ASZ、SZ3、QoZ放进同一作业再测一次时间
reruns={"asz":(["asz"],list(groups)),"timing":(["asz","sz3","qoz"],["apsu004"])}


def total_time(row):
    return sum(float(row.get(key) or 0) for key in ("PREPROCESSING_TIME","COMPRESSION_TIME","DECOMPRESSION_TIME"))


def rerun_part(name,dataset,index=None):
    stem=Path(dataset["results"]["asz"]).stem
    return f"final18_{name}/{stem}.csv" if index is None else f"final18_{name}/{stem}_{index}.csv"


def prepare_rerun(name):
    method_list,group_names=reruns[name]
    datasets=load_manifest()
    for group in group_names:
        output_directory=f"/anvil/scratch/x-zjian1/asz-final18-rd/{name}_{group}"
        write_json(project_root/f"configs/.final18_rd_{name}_{group}.json",[task(datasets[index],output_directory,summary_csv=rerun_part(name,datasets[index]),method_list=method_list) for index in groups[group]])
    apsu006=datasets[17]
    for index,rel_eb in enumerate(apsu006["rel_eb_list"]):
        output_directory=f"/anvil/scratch/x-zjian1/asz-final18-rd/{name}_apsu006_{index}"
        write_json(project_root/f"configs/.final18_rd_{name}_apsu006_{index}.json",[task(apsu006,output_directory,[rel_eb],rerun_part(name,apsu006,index),method_list)])


def merge_rerun(name):
    method_list,group_names=reruns[name]
    datasets=load_manifest()
    for dataset_index in [index for group in group_names for index in groups[group]]+[17]:
        dataset=datasets[dataset_index]
        data_path=dataset.get("result_data_path",dataset["data_path"])
        part_paths=[project_root/"results"/rerun_part(name,dataset,index) for index in range(len(dataset["rel_eb_list"]))] if dataset_index==17 else [project_root/"results"/rerun_part(name,dataset)]
        new_rows={}
        for part_path in part_paths:
            with open(part_path,newline="",encoding="utf-8") as part_file:
                for row in csv.DictReader(part_file):
                    if row["METHOD"] in method_list and row["DATA_PATH"]==data_path:
                        new_rows[(row["METHOD"],float(row["REL_EB"]))]=row
        target_path=project_root/"results"/dataset["results"]["asz"]
        with open(target_path,newline="",encoding="utf-8") as target_file:
            reader=csv.DictReader(target_file)
            fieldnames=reader.fieldnames
            rows=list(reader)
        replaced=0
        for position,row in enumerate(rows):
            if row["METHOD"] not in method_list or row["DATA_PATH"]!=data_path:
                continue
            matches=[key for key in new_rows if key[0]==row["METHOD"] and math.isclose(key[1],float(row["REL_EB"]),rel_tol=1e-12,abs_tol=0)]
            if len(matches)!=1:
                raise ValueError(f"{target_path}的{row['METHOD']}误差界{row['REL_EB']}没有唯一的新结果")
            new_row=new_rows[matches[0]]
            # 新launcher多写了MAX_ERROR等误差检查列，并已在运行时检查误差界，final18保持原有列
            if set(fieldnames)-set(new_row):
                raise ValueError(f"{part_paths[0]}缺少{target_path}中的列")
            # 重建数据是确定的，timing重跑只应改变时间，QoZ的压缩字节数在不同运行间会有几百字节的差异
            if name=="timing" and not (math.isclose(float(new_row["PSNR"]),float(row["PSNR"]),rel_tol=1e-9) and math.isclose(float(new_row["CR"]),float(row["CR"]),rel_tol=1e-4)):
                raise ValueError(f"{target_path}的{row['METHOD']}在误差界{row['REL_EB']}处的压缩结果与原结果不一致")
            # APSU的运行时间在不同运行间最多相差1.8倍，机器干扰只会让运行变慢，因此保留两次运行中总时间较短的一次
            if name=="timing" and total_time(row)<=total_time(new_row):
                replaced+=1
                continue
            rows[position]={key:new_row.get(key,"") for key in fieldnames}
            rows[position]["REL_EB"]=row["REL_EB"]
            replaced+=1
        expected=len(method_list)*len(dataset["rel_eb_list"])
        if replaced!=expected or len(new_rows)!=replaced:
            raise ValueError(f"{target_path}应替换{expected}行，实际替换{replaced}行")
        asz_cr={float(row["REL_EB"]):float(row["CR"]) for row in rows if row["METHOD"]=="asz" and row["DATA_PATH"]==data_path}
        for row in rows:
            if row["DATA_PATH"]==data_path:
                row["CR_DROP_PERCENT"]=100*(asz_cr[float(row["REL_EB"])]-float(row["CR"]))/asz_cr[float(row["REL_EB"])]
        temporary_path=target_path.with_name(target_path.name+".tmp")
        with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
            writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_path,target_path)
        print(f"替换{'、'.join(method_list)}结果：{target_path}")


def prepare_throughput():
    datasets=load_manifest()
    for group,indexes in groups.items():
        output_directory=f"/anvil/scratch/x-zjian1/asz-final18-throughput/{group}"
        tasks=[]
        for index in indexes:
            dataset=datasets[index]
            filename=Path(dataset["results"]["asz"]).name
            tasks.append(task(dataset,output_directory,summary_csv=f"final18_throughput/{filename}",method_list=["zfp","sperr"],comparison_baseline="zfp"))
        write_json(project_root/f"configs/.final18_throughput_{group}.json",tasks)
    apsu006=datasets[17]
    filename=Path(apsu006["results"]["asz"]).name
    output_directory="/anvil/scratch/x-zjian1/asz-final18-throughput/apsu006_zfp"
    write_json(project_root/"configs/.final18_throughput_apsu006_zfp.json",[task(apsu006,output_directory,summary_csv=f"final18_throughput/{filename}",method_list=["zfp"],comparison_baseline="zfp")])


# APSU006按误差界拆成多个作业，SPERR另开作业，合并各分片得到final18/apsu006.csv
def merge_apsu006():
    apsu006=load_manifest()[17]
    expected={(str(rel_eb),method) for rel_eb in apsu006["rel_eb_list"] for method in methods}
    rows=[]
    for index,rel_eb in enumerate(apsu006["rel_eb_list"]):
        for part,part_methods in ((f"apsu006_{index}.csv",{"asz","sz3","qoz","zfp"}),(f"apsu006_sperr_{index}.csv",{"sperr"})):
            part_path=project_root/"results/final18_parts"/part
            with open(part_path,newline="",encoding="utf-8") as part_file:
                reader=csv.DictReader(part_file)
                fieldnames=reader.fieldnames
                part_rows=[row for row in reader if row["METHOD"] in part_methods]
            if {row["METHOD"] for row in part_rows}!=part_methods or len(part_rows)!=len(part_methods) or any(not math.isclose(float(row["REL_EB"]),rel_eb,rel_tol=1e-12,abs_tol=0) for row in part_rows):
                raise ValueError(f"APSU006分片错误：{part_path}")
            for row in part_rows:
                row["REL_EB"]=str(rel_eb)
            rows.extend(part_rows)
    actual={(row["REL_EB"],row["METHOD"]) for row in rows}
    if actual!=expected or len(rows)!=len(expected):
        raise ValueError(f"APSU006分片不完整：期望{len(expected)}行，实际{len(rows)}行")
    eb_order={str(rel_eb):index for index,rel_eb in enumerate(apsu006["rel_eb_list"])}
    method_order={method:index for index,method in enumerate(methods)}
    rows.sort(key=lambda row:(eb_order[row["REL_EB"]],method_order[row["METHOD"]]))
    asz_cr={row["REL_EB"]:float(row["CR"]) for row in rows if row["METHOD"]=="asz"}
    for row in rows:
        row["CR_DROP_PERCENT"]=100*(asz_cr[row["REL_EB"]]-float(row["CR"]))/asz_cr[row["REL_EB"]]
    output_path=project_root/"results/final18/apsu006.csv"
    output_path.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=output_path.with_name(output_path.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary_path,output_path)
    print(f"写入APSU006汇总：{output_path}")


def main():
    parser=argparse.ArgumentParser(description="准备或合并最终18-field RD任务")
    parser.add_argument("--merge-apsu006",action="store_true")
    parser.add_argument("--prepare-throughput",action="store_true")
    parser.add_argument("--prepare-rerun",choices=list(reruns),help="生成只重跑部分method的配置")
    parser.add_argument("--merge-rerun",choices=list(reruns),help="用final18_{name}中的新结果替换final18中对应的行")
    arguments=parser.parse_args()
    if arguments.merge_apsu006:
        merge_apsu006()
    elif arguments.prepare_rerun:
        prepare_rerun(arguments.prepare_rerun)
    elif arguments.merge_rerun:
        merge_rerun(arguments.merge_rerun)
    elif arguments.prepare_throughput:
        prepare_throughput()
    else:
        prepare()


if __name__=="__main__":
    main()
