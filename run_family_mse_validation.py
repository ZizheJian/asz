import argparse,csv,hashlib,json,math,re,subprocess,tempfile
from pathlib import Path

from analyze_family_mse import save_analysis,write_csv
from t1_start_compressors import calculate_float32_metrics,parse_asz_result,parse_default_slope_statistics,parse_predictor_family,parse_predictor_family_selection,parse_predictors,validate_data_file

project_root=Path(__file__).resolve().parent
option_names={"block_pivot_ratio":"--block-pivot-ratio","block_t_policy":"--block-t-policy","max_layer_num":"--max-layer-num","full_predictor_search_layer_num":"--full-predictor-search-layer-num","generate_config_sample_stride":"--generate-config-sample-stride","h1_block_sampling_num":"--h1-block-sampling-num","stat_eb_ratio":"--stat-eb-ratio","predictor_family_sample_limit":"--predictor-family-sample-limit"}
config_keys=("predictor_vec","pivot_eb_ratio","eb_ratio","slope_ratio","block_pivot_ratio","pivot_stride","block_shape","block_num","t_precision","t_range","t_candidates","block_t_candidates","t_policy","block_t_policy")


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def load_manifest(path):
    document=json.loads(path.read_text())
    if not isinstance(document,list) or not document:
        raise ValueError("manifest must be a nonempty list")
    names=set()
    for task in document:
        name=task["name"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+",name) or name in names:
            raise ValueError("dataset names must be unique and filename-safe")
        names.add(name)
        shape=task["data_shape"]
        if len(shape)!=3 or any(type(size) is not int or size<8 for size in shape):
            raise ValueError("data_shape must contain three integers of at least 8")
        bounds=task["rel_eb_list"]
        if len(bounds)<2 or len(bounds)!=len(set(bounds)) or any(not math.isfinite(value) or value<=0 for value in bounds):
            raise ValueError("at least two distinct positive finite error bounds are required")
        unknown=task.get("asz_parameters",{}).keys()-option_names.keys()
        if unknown:
            raise ValueError(f"unsupported ASZ parameters: {unknown}")
        if task.get("asz_parameters",{}).get("block_t_policy","peaks") not in ("peaks","full"):
            raise ValueError("block_t_policy must be peaks or full")
        task["data_path"]=str(Path(task["data_path"]).resolve())
    return document


def call_logged(command,path,commands):
    command=[str(item) for item in command]
    commands.append({"log":str(path),"command":command})
    with path.open("w") as output:
        subprocess.run(command,stdout=output,stderr=subprocess.STDOUT,check=True)
    return path.read_text()


def settings_signature(output):
    settings={}
    for key in config_keys:
        matches=re.findall(r"^"+key+r"=(.*);$",output,re.MULTILINE)
        if len(matches)!=1:
            raise ValueError(f"missing or ambiguous runtime setting: {key}")
        settings[key]=matches[0]
    settings["default_slope"]=parse_default_slope_statistics(output)["default_slope"]
    return settings


def measure_variant(task,bound,compressed,reconstructed,compression_output,decompression_output):
    reported=parse_asz_result(compression_output+decompression_output)
    original=Path(task["data_path"])
    metrics=calculate_float32_metrics(original,reconstructed)
    absolute_bound=bound*metrics["value_range"]
    tolerance=max(1.0,metrics["value_range"])*1e-12
    if metrics["max_error"]>absolute_bound*1.01+tolerance:
        raise RuntimeError("ASZ reconstruction exceeds the existing 1.01 error-bound check")
    size=compressed.stat().st_size
    if size<=0 or not math.isclose(reported["cr"],original.stat().st_size/size,rel_tol=1e-5,abs_tol=1e-6):
        raise RuntimeError("compressed size and reported compression ratio disagree")
    family=parse_predictor_family(compression_output)
    return {"DATASET":task["name"],"DATA_PATH":str(original),"REL_EB":bound,"FAMILY":"adaptive_4r" if family=="cubic" else "fixed_6r","STENCIL":"1D4R" if family=="cubic" else "1D6R","CR":original.stat().st_size/size,"BR":8*size/math.prod(task["data_shape"]),"PSNR":metrics["psnr"],"COMPRESSED_BYTES":size,"MAX_ERROR":metrics["max_error"],"ABSOLUTE_EB":absolute_bound,"COMPRESSION_TIME":reported["compression_time"],"DECOMPRESSION_TIME":reported["decompression_time"]}


def run(arguments):
    tasks=load_manifest(arguments.manifest)
    for task in tasks:
        validate_data_file(Path(task["data_path"]),task["data_shape"])
    if arguments.dry_run:
        print(json.dumps({"tasks":tasks,"compression_runs":2*sum(len(task["rel_eb_list"]) for task in tasks),"strategy":"first run records raw MSE with ratio 1; second forces the opposite family with exactly the same plan and runtime settings","output":str(arguments.output)},indent=2))
        return
    compress=(arguments.executables/"s1_compress").resolve()
    decompress=(arguments.executables/"s1_decompress").resolve()
    for binary in (compress,decompress):
        if not binary.is_file():
            raise FileNotFoundError(binary)
    output=arguments.output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    logs=output/"logs"
    logs.mkdir()
    sources=[project_root/"c_codes/s1_compress.cpp",project_root/"c_codes/s1_decompress.cpp",project_root/"run_family_mse_validation.py",project_root/"analyze_family_mse.py",project_root/"t1_start_compressors.py",*sorted((project_root/"c_codes/asz_core").glob("*.hpp")),*sorted((project_root/"c_codes/asz_core").glob("*.tpp"))]
    provenance={"protocol":"paired full-compressor adaptive 4R versus fixed quintic 6R; shared plan and runtime settings; raw MSE ordering without runtime preference margin","manifest":tasks,"manifest_sha256":hashlib.sha256(arguments.manifest.read_bytes()).hexdigest(),"source_hashes":{str(path.relative_to(project_root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},"binary_hashes":{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (compress,decompress)},"inputs":{task["data_path"]:{"size":Path(task["data_path"]).stat().st_size,"mtime_ns":Path(task["data_path"]).stat().st_mtime_ns} for task in tasks}}
    (output/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
    rows=[]
    commands=[]
    for task in tasks:
        for bound in task["rel_eb_list"]:
            name=f"{task['name']}-{bound:.12g}"
            print(f"START {name}",flush=True)
            # 所有临时码流及重建文件均位于本次新建的结果目录，不写到原始数据旁边。
            with tempfile.TemporaryDirectory(prefix="pair-",dir=output) as scratch:
                scratch=Path(scratch)
                common=["-f","-i",task["data_path"],"-3",*task["data_shape"],"-M","REL",f"{bound:.17g}"]
                for key,value in task.get("asz_parameters",{}).items():
                    common.extend([option_names[key],value])
                source_path=scratch/"source.asz"
                source_reconstruction=scratch/"source.f32"
                source_output=call_logged([compress,*common,"-z",source_path,"--predictor-family-mse-ratio-threshold",1],logs/f"{name}-source-compress.log",commands)
                selection=parse_predictor_family_selection(source_output)
                if selection.get("predictor_family_fallback"):
                    raise RuntimeError("family selector had no final-layer samples")
                source_family=parse_predictor_family(source_output)
                if source_family!=selection["predictor_family"]:
                    raise RuntimeError("recorded MSE selection and actual family disagree")
                plan=parse_predictors(source_output)
                source_settings=settings_signature(source_output)
                source_decoded=call_logged([decompress,*common,"-z",source_path,"-o",source_reconstruction],logs/f"{name}-source-decompress.log",commands)
                first=measure_variant(task,bound,source_path,source_reconstruction,source_output,source_decoded)
                opposite="quintic" if source_family=="cubic" else "cubic"
                opposite_path=scratch/"opposite.asz"
                opposite_reconstruction=scratch/"opposite.f32"
                opposite_output=call_logged([compress,*common,"-z",opposite_path,"--predictor-plan",",".join(plan),"--predictor-family",opposite],logs/f"{name}-opposite-compress.log",commands)
                if parse_predictor_family(opposite_output)!=opposite or settings_signature(opposite_output)!=source_settings:
                    raise RuntimeError("paired compression did not preserve the plan/runtime controls")
                opposite_decoded=call_logged([decompress,*common,"-z",opposite_path,"-o",opposite_reconstruction],logs/f"{name}-opposite-decompress.log",commands)
                second=measure_variant(task,bound,opposite_path,opposite_reconstruction,opposite_output,opposite_decoded)
                controls={"CUBIC_MSE":selection["cubic_mse"],"QUINTIC_MSE":selection["quintic_mse"],"PREDICTOR_FAMILY_DIRECTION":selection["predictor_family_direction"],"PREDICTOR_FAMILY_SAMPLES":selection["predictor_family_samples"],"PREDICTOR_FAMILY_SELECTION_TIME":selection["predictor_family_selection_time"],"PLAN_HASH":digest(plan),"SETTINGS_HASH":digest(source_settings)}
                rows.extend([{**first,**controls},{**second,**controls}])
                (output/f"{name}-controls.json").write_text(json.dumps({"plan":plan,"settings":source_settings,"controls":controls},indent=2)+"\n")
                write_csv(output/"raw.csv",rows)
                (output/"commands.json").write_text(json.dumps(commands,indent=2)+"\n")
            print(f"DONE {name}",flush=True)
    save_analysis(rows,output/"analysis",input_paths=[output/"raw.csv"])


def cli():
    parser=argparse.ArgumentParser(description="Collect paired ASZ paths and validate raw MSE family ordering")
    parser.add_argument("--manifest",type=Path,default=project_root/"configs/family_mse_validation.json")
    parser.add_argument("--executables",type=Path,default=project_root/"install/bin")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--dry-run",action="store_true")
    run(parser.parse_args())


if __name__=="__main__":
    cli()
