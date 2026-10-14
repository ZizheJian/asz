import argparse,csv,hashlib,json,math,re,subprocess,time
from pathlib import Path

project_root=Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_csv(path):
    with path.open(newline="",encoding="utf-8") as source:
        return list(csv.DictReader(source))


def write_csv(path,rows):
    with path.open("w",newline="",encoding="utf-8") as output:
        writer=csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def parse_values(line):
    return {key:float(value) if re.fullmatch(r"[-+0-9.eE]+",value) else value for key,value in (item.split("=",1) for item in line.split(": ",1)[1].split(", "))}


def parse_output(output):
    slope_matches=re.findall(r"^Default slope statistics:.* slope=([-+0-9.eE]+)$",output,re.MULTILINE)
    family_lines=re.findall(r"^Family sample: .*$",output,re.MULTILINE)
    comparison_lines=re.findall(r"^Family comparison: .*$",output,re.MULTILINE)
    if len(slope_matches)!=1 or len(family_lines)!=2 or len(comparison_lines)!=1:
        raise ValueError("missing or ambiguous sample output")
    families={values["family"]:values for values in map(parse_values,family_lines)}
    if set(families)!={"cubic","quintic"}:
        raise ValueError("sample output does not contain both families")
    return float(slope_matches[0]),families["cubic"],families["quintic"],parse_values(comparison_lines[0])


def choice_from_gain(gain):
    if math.isclose(gain,0,rel_tol=1e-12,abs_tol=1e-15):
        return "tie"
    return "fixed_6r" if gain>0 else "adaptive_4r"


def choice_from_error(four,six):
    if math.isclose(four,six,rel_tol=1e-12,abs_tol=0):
        return "tie"
    return "fixed_6r" if six<four else "adaptive_4r"


def metric_summary(rows,choice_key):
    scored=[row for row in rows if row[choice_key]!="tie" and row["rd_choice"]!="tie"]
    correct=sum(row[choice_key]==row["rd_choice"] for row in scored)
    regrets=[0 if row[choice_key]==row["rd_choice"] else abs(float(row["full_six_score_gain"])) for row in scored]
    return {"metric":choice_key,"cases":len(rows),"scored_cases":len(scored),"correct":correct,"incorrect":len(scored)-correct,"ranking_accuracy":correct/len(scored) if scored else None,"mean_pair_tau":(2*correct-len(scored))/len(scored) if scored else None,"mean_score_regret":sum(regrets)/len(regrets) if regrets else None,"max_score_regret":max(regrets) if regrets else None}


def run(arguments):
    tasks=json.loads(arguments.manifest.read_text())
    if arguments.max_datasets is not None:
        if arguments.max_datasets<1:
            raise ValueError("max datasets must be positive")
        tasks=tasks[:arguments.max_datasets]
    ground_truth_rows=load_csv(arguments.ground_truth)
    ground_truth={(row["dataset"],float(row["rel_eb"])):row for row in ground_truth_rows}
    binary=arguments.binary.resolve()
    if not binary.is_file():
        raise FileNotFoundError(binary)
    output=arguments.output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    logs=output/"logs"
    logs.mkdir()
    provenance={"protocol":"paired reconstructed-reference block sampling for adaptive cubic 1D4R versus fixed-quintic 1D6R","suffix_layers":arguments.suffix_layers,"sample_blocks":arguments.sample_blocks,"seed_mode":arguments.seed_mode,"sample_slope":arguments.sample_slope,"sample_slope_protocol":"same target plan and sample blocks; cubic path at one adjacent decade; looser bound except tighter at the upper endpoint" if arguments.sample_slope else None,"manifest":str(arguments.manifest.resolve()),"manifest_sha256":sha256(arguments.manifest),"controls":str(arguments.controls.resolve()),"ground_truth":str(arguments.ground_truth.resolve()),"ground_truth_sha256":sha256(arguments.ground_truth),"binary":str(binary),"binary_sha256":sha256(binary),"source_sha256":sha256(project_root/"c_codes/s10_predictor_family_block_sample.cpp"),"inputs":{task["data_path"]:{"size":Path(task["data_path"]).stat().st_size,"mtime_ns":Path(task["data_path"]).stat().st_mtime_ns} for task in tasks}}
    (output/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
    rows=[]
    commands=[]
    for task in tasks:
        for bound in task["rel_eb_list"]:
            case_name=f"{task['name']}-{bound:.12g}"
            control_path=arguments.controls/f"{case_name}-controls.json"
            control=json.loads(control_path.read_text())
            plan=control["plan"]
            if len(plan)<arguments.suffix_layers:
                raise ValueError(f"{case_name} has fewer than {arguments.suffix_layers} layers")
            command=[str(binary),task["data_path"],*(str(value) for value in task["data_shape"]),f"{bound:.17g}",",".join(plan),str(arguments.suffix_layers),"sample",str(arguments.sample_blocks),arguments.seed_mode]
            commands.append(command)
            print(f"START {case_name}",flush=True)
            wall_begin=time.perf_counter()
            completed=subprocess.run(command,capture_output=True,text=True,check=True)
            wall_seconds=time.perf_counter()-wall_begin
            log=completed.stdout+completed.stderr
            (logs/f"{case_name}.log").write_text(log)
            runtime_slope,four,six,comparison=parse_output(log)
            truth=ground_truth[(task["name"],bound)]
            reference_slope=float(truth["slope"])
            psnr_gain=six["reconstruction_psnr"]-four["reconstruction_psnr"]
            h1_delta=six["h1"]-four["h1"]
            zstd_delta=six["zstd_bps"]-four["zstd_bps"]
            huffman_delta=six["huffman_bps"]-four["huffman_bps"]
            sample_slope=math.nan
            neighbor_seconds=0
            if arguments.sample_slope:
                neighbor_bound=bound/10 if bound==max(task["rel_eb_list"]) else bound*10
                neighbor_command=[str(binary),task["data_path"],*(str(value) for value in task["data_shape"]),f"{neighbor_bound:.17g}",",".join(plan),str(arguments.suffix_layers),"sample",str(arguments.sample_blocks),arguments.seed_mode]
                commands.append(neighbor_command)
                neighbor_begin=time.perf_counter()
                neighbor_completed=subprocess.run(neighbor_command,capture_output=True,text=True,check=True)
                neighbor_seconds=time.perf_counter()-neighbor_begin
                neighbor_log=neighbor_completed.stdout+neighbor_completed.stderr
                (logs/f"{case_name}-slope-neighbor.log").write_text(neighbor_log)
                _,neighbor_four,_,_=parse_output(neighbor_log)
                coarse,fine=(neighbor_four,four) if neighbor_bound>bound else (four,neighbor_four)
                rate_difference=fine["zstd_bps"]-coarse["zstd_bps"]
                quality_difference=fine["reconstruction_psnr"]-coarse["reconstruction_psnr"]
                if not rate_difference>0 or not quality_difference>0:
                    raise RuntimeError(f"nonmonotone sampled slope for {case_name}")
                sample_slope=quality_difference/rate_difference
            row={"dataset":task["name"],"data_path":task["data_path"],"rel_eb":bound,"suffix_layers":arguments.suffix_layers,"sample_blocks":arguments.sample_blocks,"sample_points":int(four["points"]),"runtime_slope":runtime_slope,"sample_slope":sample_slope,"reference_slope":reference_slope,"four_prediction_mse":four["prediction_mse"],"six_prediction_mse":six["prediction_mse"],"four_reconstruction_mse":four["reconstruction_mse"],"six_reconstruction_mse":six["reconstruction_mse"],"four_reconstruction_psnr":four["reconstruction_psnr"],"six_reconstruction_psnr":six["reconstruction_psnr"],"psnr_gain_6r_minus_4r":psnr_gain,"four_h1":four["h1"],"six_h1":six["h1"],"h1_delta_6r_minus_4r":h1_delta,"four_huffman_bps":four["huffman_bps"],"six_huffman_bps":six["huffman_bps"],"huffman_bps_delta_6r_minus_4r":huffman_delta,"four_zstd_bps":four["zstd_bps"],"six_zstd_bps":six["zstd_bps"],"zstd_bps_delta_6r_minus_4r":zstd_delta,"prediction_mse_choice":choice_from_error(four["prediction_mse"],six["prediction_mse"]),"reconstruction_mse_choice":choice_from_error(four["reconstruction_mse"],six["reconstruction_mse"]),"h1_runtime_gain":psnr_gain-runtime_slope*h1_delta,"h1_runtime_choice":choice_from_gain(psnr_gain-runtime_slope*h1_delta),"zstd_runtime_gain":psnr_gain-runtime_slope*zstd_delta,"zstd_runtime_choice":choice_from_gain(psnr_gain-runtime_slope*zstd_delta),"zstd_sample_slope_gain":psnr_gain-sample_slope*zstd_delta if math.isfinite(sample_slope) else math.nan,"zstd_sample_slope_choice":choice_from_gain(psnr_gain-sample_slope*zstd_delta) if math.isfinite(sample_slope) else "not_run","h1_reference_gain":psnr_gain-reference_slope*h1_delta,"h1_reference_choice":choice_from_gain(psnr_gain-reference_slope*h1_delta),"zstd_reference_gain":psnr_gain-reference_slope*zstd_delta,"zstd_reference_choice":choice_from_gain(psnr_gain-reference_slope*zstd_delta),"rd_choice":truth["rd_choice"],"full_six_score_gain":truth["six_score_gain"],"four_simulation_seconds":four["simulation_seconds"],"six_simulation_seconds":six["simulation_seconds"],"statistics_seconds":four["statistics_seconds"]+six["statistics_seconds"],"lossless_seconds":four["lossless_seconds"]+six["lossless_seconds"],"selector_seconds_without_initialization":four["simulation_seconds"]+six["simulation_seconds"]+four["statistics_seconds"]+six["statistics_seconds"],"initialization_seconds":four["initialization_seconds"]+six["initialization_seconds"],"measured_total_seconds":comparison["measured_total_seconds"],"neighbor_process_seconds":neighbor_seconds,"process_wall_seconds":wall_seconds+neighbor_seconds}
            rows.append(row)
            write_csv(output/"cases.csv",rows)
            (output/"commands.json").write_text(json.dumps(commands,indent=2)+"\n")
            print(f"DONE {case_name} h1={row['h1_runtime_choice']} zstd={row['zstd_runtime_choice']} sample_slope={row['zstd_sample_slope_choice']} truth={row['rd_choice']}",flush=True)
    choice_keys=("prediction_mse_choice","reconstruction_mse_choice","h1_runtime_choice","zstd_runtime_choice",*(("zstd_sample_slope_choice",) if arguments.sample_slope else ()),"h1_reference_choice","zstd_reference_choice")
    summaries=[metric_summary(rows,key) for key in choice_keys]
    per_dataset={task["name"]:[metric_summary([row for row in rows if row["dataset"]==task["name"]],key) for key in choice_keys] for task in tasks}
    report={"pooled":summaries,"per_dataset":per_dataset,"timing":{"mean_selector_seconds_without_initialization":sum(row["selector_seconds_without_initialization"] for row in rows)/len(rows),"max_selector_seconds_without_initialization":max(row["selector_seconds_without_initialization"] for row in rows),"mean_lossless_seconds":sum(row["lossless_seconds"] for row in rows)/len(rows),"max_lossless_seconds":max(row["lossless_seconds"] for row in rows),"mean_initialization_seconds":sum(row["initialization_seconds"] for row in rows)/len(rows),"mean_neighbor_process_seconds":sum(row["neighbor_process_seconds"] for row in rows)/len(rows),"mean_process_wall_seconds":sum(row["process_wall_seconds"] for row in rows)/len(rows)}}
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report["pooled"],indent=2),flush=True)


def cli():
    parser=argparse.ArgumentParser(description="Validate final-layer block-sampled predictor-family criteria against paired full compression")
    parser.add_argument("--manifest",type=Path,default=project_root/"configs/family_mse_validation.json")
    parser.add_argument("--controls",type=Path,default=project_root/"results/family-mse-six-21285600")
    parser.add_argument("--ground-truth",type=Path,default=project_root/"results/family-mse-six-21285600/analysis/cases.csv")
    parser.add_argument("--binary",type=Path,default=project_root/"build-block-sample/s10_predictor_family_block_sample")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--suffix-layers",type=int,default=8)
    parser.add_argument("--sample-blocks",type=int,default=16)
    parser.add_argument("--max-datasets",type=int)
    parser.add_argument("--seed-mode",choices=("pivot","first-layer"),default="pivot")
    parser.add_argument("--sample-slope",action="store_true")
    run(parser.parse_args())


if __name__=="__main__":
    cli()
