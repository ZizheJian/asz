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
        write_json(project_root/f"configs/.final18_rd_apsu006_{index}.json",[task(apsu006,output_directory,[rel_eb],part)])
        sperr_part=f"final18_parts/apsu006_sperr_{index}.csv"
        write_json(project_root/f"configs/.final18_rd_apsu006_sperr_{index}.json",[task(apsu006,output_directory,[rel_eb],sperr_part,["sperr"],"sperr")])


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


def merge_apsu006():
    apsu006=load_manifest()[17]
    expected={(str(rel_eb),method) for rel_eb in apsu006["rel_eb_list"] for method in methods}
    rows=[]
    template_path=project_root/"results/final18/qmcpack_orbital144.csv"
    with open(template_path,newline="",encoding="utf-8") as template_file:
        fieldnames=csv.DictReader(template_file).fieldnames
    log_ids=(21592196,21592197,21592198,21592199,21592194)
    column_keys={"CR":"cr","BR":"br","PSNR":"psnr","PREPROCESSING_TIME":"preprocessing_time","GET_DEFAULT_SLOPE_TIME":"get_default_slope_time","GENERATE_CONFIG_TIME":"generate_config_time","DATA_RANGE_TIME":"data_range_time","COMPRESSION_TIME":"compression_time","DECOMPRESSION_TIME":"decompression_time"}
    for index,(rel_eb,log_id) in enumerate(zip(apsu006["rel_eb_list"],log_ids)):
        log_path=project_root/f"results/final18-rd-{log_id}.log"
        recovered={}
        with open(log_path,encoding="utf-8") as log_file:
            for line in log_file:
                if not line.startswith("result method="):
                    continue
                values=dict(item.split("=",1) for item in line.removeprefix("result ").strip().split(","))
                if values["method"] in ("asz","sz3","qoz","zfp"):
                    recovered[values["method"]]=values
        if set(recovered)!={"asz","sz3","qoz","zfp"}:
            raise ValueError(f"APSU006日志缺少结果：{log_path}")
        for method,values in recovered.items():
            if not math.isclose(float(values["rel_eb"]),rel_eb,rel_tol=1e-12,abs_tol=0):
                raise ValueError(f"APSU006日志误差界错误：{log_path}")
            row={key:"" for key in fieldnames}
            row.update({"DATA_PATH":apsu006["data_path"],"REL_EB":str(rel_eb),"METHOD":method})
            row.update({column:values.get(key,"") for column,key in column_keys.items()})
            rows.append(row)
        sperr_path=project_root/f"results/final18_parts/apsu006_sperr_{index}.csv"
        with open(sperr_path,newline="",encoding="utf-8") as sperr_file:
            sperr_rows=[row for row in csv.DictReader(sperr_file) if row["METHOD"]=="sperr"]
        if len(sperr_rows)!=1 or not math.isclose(float(sperr_rows[0]["REL_EB"]),rel_eb,rel_tol=1e-12,abs_tol=0):
            raise ValueError(f"APSU006 SPERR分片错误：{sperr_path}")
        rows.extend(sperr_rows)
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
    arguments=parser.parse_args()
    if arguments.merge_apsu006:
        merge_apsu006()
    elif arguments.prepare_throughput:
        prepare_throughput()
    else:
        prepare()


if __name__=="__main__":
    main()
