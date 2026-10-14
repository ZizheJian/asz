import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

project_root=Path(__file__).resolve().parent
rel_ebs=[1e-1,1e-2,1e-3,1e-4,1e-5]

def sha256(path):
    digest=hashlib.sha256()
    with open(path,"rb") as input_file:
        while chunk:=input_file.read(1<<20):
            digest.update(chunk)
    return digest.hexdigest()

def run_config(document,source,executables,dry_run):
    descriptor,path=tempfile.mkstemp(prefix="asz-legacy-coefficient-",suffix=".json",dir="/tmp")
    try:
        with os.fdopen(descriptor,"w",encoding="utf-8") as output_file:
            json.dump(document,output_file,indent=2)
            output_file.write("\n")
        environment=dict(os.environ)
        environment["ASZ_EXECUTABLE_DIRECTORY"]=str(executables)
        command=[sys.executable,str(source/"t1_start_compressors.py"),path,"--skip-build","--no-csv"]
        if dry_run:
            command.append("--dry-run")
        subprocess.run(command,cwd=source,env=environment,check=True)
    finally:
        Path(path).unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser(description="Reproduce legacy block-wise 1D4R coefficient selection with one frozen plan")
    parser.add_argument("--manifest",type=Path,default=project_root/"configs/coefficient_blockwise_legacy_1d4r.json")
    parser.add_argument("--dataset-index",type=int,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--executables",type=Path,required=True)
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    manifest=args.manifest.resolve()
    datasets=json.loads(manifest.read_text(encoding="utf-8"))
    if not 0<=args.dataset_index<len(datasets):
        parser.error(f"dataset-index must be in [0,{len(datasets)-1}]")
    dataset=datasets[args.dataset_index]
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    plan_path=output/"plans"/(dataset["slug"]+".json")
    plan_path.parent.mkdir(parents=True,exist_ok=True)
    summary_path=output/(dataset["slug"]+".csv")
    completed_path=output/(dataset["slug"]+"-completed.json")
    if not args.dry_run and any(path.exists() for path in (plan_path,summary_path,completed_path)):
        raise FileExistsError(f"refusing to overwrite an existing result for {dataset['name']}")
    common={"data_path_list":[dataset["data_path"]],"data_shape":dataset["data_shape"],"rel_eb_list":rel_ebs,"cleanup_after_each_test":True}
    plan_document=[{**common,"method_list":[{"name":"plan_source","compressor":"asz","predictor_family":"cubic","t_policy":"adaptive","write_plan":str(plan_path)}]}]
    run_config(plan_document,args.source.resolve(),args.executables.resolve(),args.dry_run)
    methods=[{"name":"block_adaptive","compressor":"asz","read_plan":str(plan_path),"predictor_family":"cubic","t_policy":"adaptive"}]
    methods.extend({"name":f"fixed_{numerator}_16","compressor":"asz","read_plan":str(plan_path),"predictor_family":"cubic","t_policy":f"fixed_{numerator}_16"} for numerator in range(3,7))
    experiment_document=[{**common,"method_list":methods,"comparison_baseline":"block_adaptive","summary_csv":str(summary_path)}]
    run_config(experiment_document,args.source.resolve(),args.executables.resolve(),args.dry_run)
    if args.dry_run:
        return
    input_path=Path(dataset["data_path"])
    provenance={"protocol":"ASZ commit 45c856e with one frozen prediction plan,forced cubic 1D4R,and the complete legacy adaptive grid {3,4,5,6}/16 compared with every globally fixed candidate","dataset":dataset,"relative_error_bounds":rel_ebs,"commit":"45c856e","input":{"size":input_path.stat().st_size,"mtime_ns":input_path.stat().st_mtime_ns},"sha256":{"manifest":sha256(manifest),"legacy_patch":sha256(project_root/"legacy_coefficient_fixed_grid.patch"),"compressor":sha256(args.executables.resolve()/"s1_compress"),"decompressor":sha256(args.executables.resolve()/"s1_decompress"),"plan":sha256(plan_path),"summary":sha256(summary_path)}}
    temporary=completed_path.with_name(completed_path.name+".tmp")
    with open(temporary,"w",encoding="utf-8") as output_file:
        json.dump(provenance,output_file,indent=2)
        output_file.write("\n")
    temporary.replace(completed_path)
    print(f"completed {dataset['name']}: {summary_path}",flush=True)

if __name__=="__main__":
    main()
