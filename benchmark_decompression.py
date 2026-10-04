import argparse,csv,re,subprocess
from pathlib import Path
from statistics import median

cases=(
    ("APS_Kaz",Path("/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/APS_Kaz/xpcs-998x128x128.bin.f32"),(998,128,128),0.01),
    ("Aramco",Path("/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/aramco/aramco-snapshot-1800.f32"),(449,449,235),0.01),
    ("E017",Path("/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/APS_DYS/xpcs_datasets/E017_CeramicGlass_L2Mq0_060C_att00_001/E017_CeramicGlass_L2Mq0_060C_att00_001_001.h5.f32"),(1024,1813,1558),0.001),
)
number_pattern=r"([0-9.eE+-]+)"

def execute(command):
    result=subprocess.run([str(item) for item in command],check=True,text=True,capture_output=True)
    return result.stdout+result.stderr

def parse_time(output,pattern):
    matches=re.findall(pattern,output,re.MULTILINE)
    if not matches:
        raise RuntimeError(f"未找到计时输出：{pattern}")
    return float(matches[-1])

def main():
    parser=argparse.ArgumentParser(description="在同一节点比较优化前后ASZ及基线解压时间")
    parser.add_argument("--old-asz-directory",type=Path,required=True)
    parser.add_argument("--new-asz-directory",type=Path,required=True)
    parser.add_argument("--work-directory",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--repeat",type=int,default=3)
    parser.add_argument("--dataset",choices=[case[0] for case in cases],action="append")
    arguments=parser.parse_args()
    if arguments.repeat<=0:
        raise ValueError("repeat必须为正数")
    arguments.work_directory.mkdir(parents=True,exist_ok=True)
    arguments.output.parent.mkdir(parents=True,exist_ok=True)
    sz3=Path("install/sz3_install/bin/sz3").resolve()
    qoz=Path("install/qoz_install/bin/qoz").resolve()
    rows=[]

    selected_cases=[case for case in cases if arguments.dataset is None or case[0] in arguments.dataset]
    for dataset,data_path,shape,rel_eb in selected_cases:
        if data_path.stat().st_size!=shape[0]*shape[1]*shape[2]*4:
            raise RuntimeError(f"{dataset}文件大小与shape不符")
        prefix=arguments.work_directory/dataset.lower()
        asz_stream=prefix.with_suffix(".asz")
        sz3_stream=prefix.with_suffix(".sz3")
        qoz_stream=prefix.with_suffix(".qoz")
        asz_common=["-f","-i",data_path,"-z",asz_stream,"-o","/dev/null","-3",*shape,"-M","REL",f"{rel_eb:.17g}","--block-pivot-ratio","3"]
        print(f"生成{dataset}的ASZ压缩流",flush=True)
        execute([arguments.new_asz_directory/"s1_compress",*asz_common])
        reverse_shape=tuple(reversed(shape))
        print(f"生成{dataset}的SZ3/QoZ压缩流",flush=True)
        execute([sz3,"-f","-i",data_path,"-z",sz3_stream,"-3",*reverse_shape,"-M","REL",f"{rel_eb:.17g}"])
        execute([qoz,"-f","-i",data_path,"-z",qoz_stream,"-3",*reverse_shape,"-M","REL",f"{rel_eb:.17g}","-q","4"])
        commands={
            "asz_old":([arguments.old_asz_directory/"s1_decompress",*asz_common],rf"^Decompression time: {number_pattern}"),
            "asz_new":([arguments.new_asz_directory/"s1_decompress",*asz_common],rf"^Decompression time: {number_pattern}"),
            "sz3":([sz3,"-f","-s",sz3_stream,"-o","/dev/null","-3",*reverse_shape],rf"^decompression time = {number_pattern}"),
            "qoz":([qoz,"-f","-s",qoz_stream,"-o","/dev/null","-3",*reverse_shape],rf"^decompression time = {number_pattern}"),
        }
        for method,(command,pattern) in commands.items():
            print(f"预热：dataset={dataset},method={method}",flush=True)
            parse_time(execute(command),pattern)
        methods=tuple(commands)
        for repeat in range(arguments.repeat):
            rotated=methods[repeat%len(methods):]+methods[:repeat%len(methods)]
            for method in rotated:
                command,pattern=commands[method]
                elapsed=parse_time(execute(command),pattern)
                print(f"计时：dataset={dataset},method={method},repeat={repeat},seconds={elapsed}",flush=True)
                rows.append({"DATASET":dataset,"METHOD":method,"REPEAT":repeat,"DECOMPRESSION_TIME":elapsed})

    temporary=arguments.output.with_name(arguments.output.name+".tmp")
    with open(temporary,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=rows[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(arguments.output)
    print("中位数汇总",flush=True)
    for dataset,_,_,_ in selected_cases:
        values={method:median([row["DECOMPRESSION_TIME"] for row in rows if row["DATASET"]==dataset and row["METHOD"]==method]) for method in ("asz_old","asz_new","sz3","qoz")}
        print(f"{dataset}: old={values['asz_old']:.6f}s,new={values['asz_new']:.6f}s,speedup={values['asz_old']/values['asz_new']:.3f}x,vs_sz3={values['sz3']/values['asz_new']:.3f}x,vs_qoz={values['qoz']/values['asz_new']:.3f}x",flush=True)
    print(f"写入：{arguments.output}",flush=True)

if __name__=="__main__":
    main()
