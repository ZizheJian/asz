import argparse,csv,hashlib,json,math,re,subprocess,tempfile
from pathlib import Path

from t1_start_compressors import parse_predictor_family,parse_predictors,validate_data_file

project_root=Path(__file__).resolve().parent


def load_spec(path):
    spec=json.loads(path.read_text())
    manifest_path=path.parent/spec["base_manifest"]
    tasks=json.loads(manifest_path.read_text())
    skipped=set(spec.get("skip_datasets",[]))
    tasks=[task for task in tasks if task["name"] not in skipped]
    variants=spec["variants"]
    names=[variant["name"] for variant in variants]
    if not tasks or not variants or len(names)!=len(set(names)):
        raise ValueError("validation spec must contain tasks and uniquely named variants")
    return spec,manifest_path,tasks,variants


def call_logged(command,path):
    command=[str(item) for item in command]
    with path.open("w") as output:
        subprocess.run(command,stdout=output,stderr=subprocess.STDOUT,check=True)
    return command,path.read_text()


def one_match(pattern,text,label,cast=float):
    matches=re.findall(pattern,text,re.MULTILINE)
    if len(matches)!=1:
        raise RuntimeError(f"expected one {label},found {len(matches)}")
    return cast(matches[0])


def parse_result(output,compressed_path,point_count):
    cr,br,psnr=one_match(r"^CR: ([0-9.eE+-]+), BR: ([0-9.eE+-]+), PSNR: ([0-9.eE+-]+)\r?$",output,"RD result",lambda match:tuple(map(float,match)))
    compressed_bytes=compressed_path.stat().st_size
    exact_cr=4*point_count/compressed_bytes
    if not math.isclose(cr,exact_cr,rel_tol=2e-5,abs_tol=1e-6):
        raise RuntimeError("reported compression ratio disagrees with compressed size")
    return {"CR":exact_cr,"BR":8*compressed_bytes/point_count,"PSNR":psnr,"COMPRESSED_BYTES":compressed_bytes,"DATA_RANGE_TIME":one_match(r"^Data range time: ([0-9.eE+-]+) s\r?$",output,"data range time"),"CORE_COMPRESSION_TIME":one_match(r"^Core compression time: ([0-9.eE+-]+) s\r?$",output,"core compression time"),"COMPRESSION_TIME":one_match(r"^Compression time: ([0-9.eE+-]+) s\r?$",output,"compression time"),"MAX_ERROR":one_match(r"^max_err= ([0-9.eE+-]+)",output,"maximum error"),"T_VALUE_COUNT":one_match(r"^t_int_vec.size\(\)=([0-9]+)\r?$",output,"t value count",int),"T_FALLBACK_COUNT":one_match(r"^T fallback count:([0-9]+)\r?$",output,"t fallback count",int)}


def write_rows(path,rows):
    temporary=path.with_suffix(path.suffix+".tmp")
    with temporary.open("w",newline="") as output:
        writer=csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def source_hashes():
    paths=[project_root/"c_codes/s1_compress.cpp",project_root/"run_t_fallback_validation.py",*sorted((project_root/"c_codes/asz_core").glob("*.hpp")),*sorted((project_root/"c_codes/asz_core").glob("*.tpp"))]
    return {str(path.relative_to(project_root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def run_task(task,variants,compress,output):
    validate_data_file(Path(task["data_path"]),task["data_shape"])
    task_output=output/task["name"]
    task_output.mkdir(parents=True,exist_ok=False)
    logs=task_output/"logs"
    logs.mkdir()
    rows=[]
    commands=[]
    point_count=math.prod(task["data_shape"])
    for bound in task["rel_eb_list"]:
        case=f"{task['name']}-{bound:.12g}"
        print(f"START {case}",flush=True)
        with tempfile.TemporaryDirectory(prefix="asz-fallback-") as temporary:
            temporary=Path(temporary)
            common=["-f","-i",task["data_path"],"-3",*task["data_shape"],"-M","REL",f"{bound:.17g}","--report-t-histogram"]
            baseline=variants[0]
            baseline_path=temporary/f"{baseline['name']}.asz"
            baseline_command=[compress,*common,"--insufficient-sample-t",baseline["insufficient_sample_t"],"--quintic-fallback-t-policy",baseline["quintic_fallback_t_policy"],"--quintic-fallback-t",baseline["quintic_fallback_t"],"-z",baseline_path]
            command,baseline_output=call_logged(baseline_command,logs/f"{bound:.12g}-{baseline['name']}.log")
            commands.append(command)
            plan=parse_predictors(baseline_output)
            family=parse_predictor_family(baseline_output)
            result=parse_result(baseline_output,baseline_path,point_count)
            rows.append({"DATASET":task["name"],"DATA_PATH":task["data_path"],"REL_EB":bound,"FAMILY":family,"VARIANT":baseline["name"],"INSUFFICIENT_SAMPLE_T":baseline["insufficient_sample_t"],"QUINTIC_FALLBACK_T_POLICY":baseline["quintic_fallback_t_policy"],"QUINTIC_FALLBACK_T":baseline["quintic_fallback_t"],**result})
            for variant in variants[1:]:
                if variant.get("quintic_only",False) and family!="quintic":
                    continue
                compressed_path=temporary/f"{variant['name']}.asz"
                command=[compress,*common,"--predictor-plan",",".join(plan),"--predictor-family",family,"--insufficient-sample-t",variant["insufficient_sample_t"],"--quintic-fallback-t-policy",variant["quintic_fallback_t_policy"],"--quintic-fallback-t",variant["quintic_fallback_t"],"-z",compressed_path]
                command,variant_output=call_logged(command,logs/f"{bound:.12g}-{variant['name']}.log")
                commands.append(command)
                if parse_predictors(variant_output)!=plan or parse_predictor_family(variant_output)!=family:
                    raise RuntimeError("paired variant changed the predictor plan or family")
                result=parse_result(variant_output,compressed_path,point_count)
                rows.append({"DATASET":task["name"],"DATA_PATH":task["data_path"],"REL_EB":bound,"FAMILY":family,"VARIANT":variant["name"],"INSUFFICIENT_SAMPLE_T":variant["insufficient_sample_t"],"QUINTIC_FALLBACK_T_POLICY":variant["quintic_fallback_t_policy"],"QUINTIC_FALLBACK_T":variant["quintic_fallback_t"],**result})
            write_rows(task_output/"raw.csv",rows)
            (task_output/"commands.json").write_text(json.dumps(commands,indent=2)+"\n")
        print(f"DONE {case}",flush=True)
    return rows


def main():
    parser=argparse.ArgumentParser(description="Validate insufficient-sample and 1D6R-to-1D4R t fallback policies")
    parser.add_argument("--spec",type=Path,default=project_root/"configs/t_fallback_validation.json")
    parser.add_argument("--executables",type=Path,default=project_root/"build")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--task-index",type=int)
    parser.add_argument("--dry-run",action="store_true")
    arguments=parser.parse_args()
    spec,manifest_path,tasks,variants=load_spec(arguments.spec.resolve())
    if arguments.task_index is not None:
        if arguments.task_index<0 or arguments.task_index>=len(tasks):
            raise ValueError("task index is out of range")
        tasks=[tasks[arguments.task_index]]
    if arguments.dry_run:
        print(json.dumps({"tasks":[task["name"] for task in tasks],"variants":variants,"maximum_compression_runs":sum(len(task["rel_eb_list"])*len(variants) for task in tasks)},indent=2))
        return
    compress=(arguments.executables/"s1_compress").resolve()
    if not compress.is_file():
        raise FileNotFoundError(compress)
    output=arguments.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    provenance={"protocol":"one generated plan and dataset-wide predictor family per dataset/error-bound case; paired fallback policies reuse both","spec":spec,"base_manifest":str(manifest_path),"spec_sha256":hashlib.sha256(arguments.spec.read_bytes()).hexdigest(),"manifest_sha256":hashlib.sha256(manifest_path.read_bytes()).hexdigest(),"source_hashes":source_hashes(),"binary_sha256":hashlib.sha256(compress.read_bytes()).hexdigest()}
    for task in tasks:
        task_output=output/task["name"]
        rows=run_task(task,variants,compress,output)
        (task_output/"provenance.json").write_text(json.dumps({**provenance,"task":task,"completed_rows":len(rows)},indent=2)+"\n")


if __name__=="__main__":
    main()
