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

def run_config(document,executable_directory,dry_run):
    descriptor,path=tempfile.mkstemp(prefix="asz-coefficient-validation-",suffix=".json",dir="/tmp")
    try:
        with os.fdopen(descriptor,"w",encoding="utf-8") as output_file:
            json.dump(document,output_file,indent=2)
            output_file.write("\n")
        environment=dict(os.environ)
        environment["ASZ_EXECUTABLE_DIRECTORY"]=str(executable_directory)
        command=[sys.executable,str(project_root/"t1_start_compressors.py"),path,"--skip-build","--no-csv"]
        if dry_run:
            command.append("--dry-run")
        subprocess.run(command,cwd=project_root,env=environment,check=True)
    finally:
        Path(path).unlink(missing_ok=True)

def method(name,plan_path,**options):
    return {"name":name,"compressor":"asz","read_plan":str(plan_path),"predictor_family":"cubic",**options}

def main():
    parser=argparse.ArgumentParser(description="Compare globally fixed and block-wise adaptive 1D4R coefficients with complete ASZ compression")
    parser.add_argument("--manifest",type=Path,default=project_root/"configs/coefficient_blockwise_validation.json")
    parser.add_argument("--dataset-index",type=int,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--executables",type=Path,default=project_root/"build-coefficient-validation")
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
    summary_path=output/(dataset["slug"]+".csv")
    completed_path=output/(dataset["slug"]+"-completed.json")
    if not args.dry_run and any(path.exists() for path in (plan_path,summary_path,completed_path)):
        raise FileExistsError(f"refusing to overwrite an existing result for {dataset['name']}")
    common={"data_path_list":[dataset["data_path"]],"data_shape":dataset["data_shape"],"rel_eb_list":rel_ebs,"cleanup_after_each_test":True}
    plan_document=[{**common,"method_list":[{"name":"plan_source","compressor":"asz","predictor_family":"cubic","write_plan":str(plan_path)}]}]
    run_config(plan_document,args.executables.resolve(),args.dry_run)
    methods=[method(f"fixed_{numerator}_32",plan_path,t_policy="fixed",fixed_t=numerator/32) for numerator in range(2,13)]
    methods.extend([method("block_peaks",plan_path,t_policy="adaptive",block_t_policy="peaks",report_t_histogram=True),method("block_full",plan_path,t_policy="adaptive",block_t_policy="full",report_t_histogram=True)])
    experiment_document=[{**common,"method_list":methods,"comparison_baseline":"fixed_8_32","summary_csv":str(summary_path)}]
    run_config(experiment_document,args.executables.resolve(),args.dry_run)
    if args.dry_run:
        return
    input_path=Path(dataset["data_path"])
    provenance={"protocol":"complete ASZ compression with a frozen prediction plan and forced cubic 1D4R; compare eleven globally fixed coefficients,block-wise five-candidate H1-PSNR selection,and block-wise full-grid H1-PSNR selection","dataset":dataset,"relative_error_bounds":rel_ebs,"global_candidates":[f"{numerator}/32" for numerator in range(2,13)],"block_peaks":["2/32","8/32","9/32","10/32","11/32"],"metadata":"all reported BR values come from the complete compressed stream and include coefficient metadata","input":{"size":input_path.stat().st_size,"mtime_ns":input_path.stat().st_mtime_ns},"sha256":{"manifest":sha256(manifest),"compressor":sha256(args.executables.resolve()/"s1_compress"),"decompressor":sha256(args.executables.resolve()/"s1_decompress"),"asz_param":sha256(project_root/"c_codes/asz_core/asz_param.hpp"),"compress_source":sha256(project_root/"c_codes/asz_core/compress.tpp"),"plan":sha256(plan_path),"summary":sha256(summary_path)}}
    temporary=completed_path.with_name(completed_path.name+".tmp")
    with open(temporary,"w",encoding="utf-8") as output_file:
        json.dump(provenance,output_file,indent=2)
        output_file.write("\n")
    temporary.replace(completed_path)
    print(f"completed {dataset['name']}: {summary_path}",flush=True)

if __name__=="__main__":
    main()
