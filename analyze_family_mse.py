import argparse,csv,hashlib,json,math
from collections import defaultdict
from pathlib import Path

families=("adaptive_4r","fixed_6r")
legacy_methods={"asz_threshold_0":"adaptive_4r","asz_threshold_1e6":"fixed_6r"}


def numeric(row,key,default=math.nan):
    value=row.get(key)
    return float(value) if value not in (None,"") else default


def rank_sign(left,right,rtol):
    if math.isclose(left,right,rel_tol=rtol,abs_tol=0):
        return 0
    return 1 if left>right else -1


def collect_pairs(records,allow_unverified_plans=False):
    groups=defaultdict(dict)
    for record in records:
        row=dict(record)
        family=row.get("FAMILY") or legacy_methods.get(row.get("METHOD"))
        if family not in families:
            raise ValueError(f"unknown family: {family or row.get('METHOD')}")
        path=row.get("DATA_PATH","")
        if not path:
            raise ValueError("DATA_PATH is required")
        bound=numeric(row,"REL_EB")
        if not math.isfinite(bound) or bound<=0:
            raise ValueError("REL_EB must be positive and finite")
        key=(row.get("DATASET") or Path(path).stem,path,bound)
        if family in groups[key]:
            raise ValueError(f"duplicate family observation: {key} {family}")
        groups[key][family]=row
    pairs={}
    for key,group in groups.items():
        if set(group)!=set(families):
            raise ValueError(f"missing paired family: {key}")
        four,six=(group[family] for family in families)
        verified=True
        for control in ("PLAN_HASH","SETTINGS_HASH"):
            left,right=four.get(control),six.get(control)
            if left and right:
                if left!=right:
                    raise ValueError(f"different {control} within pair: {key}")
            elif not left and not right and allow_unverified_plans:
                verified=False
            else:
                raise ValueError(f"missing paired {control}; historical audit requires --allow-unverified-plans")
        mse=[]
        for metric in ("CUBIC_MSE","QUINTIC_MSE"):
            observations=[numeric(row,metric) for row in (four,six) if row.get(metric) not in (None,"")]
            if len(observations)==2 and all(math.isfinite(value) for value in observations) and not math.isclose(*observations,rel_tol=1e-10,abs_tol=0):
                raise ValueError(f"different {metric} within pair: {key}")
            mse.append(observations[0] if observations and all(math.isfinite(value) for value in observations) else math.nan)
        if any(value<0 for value in mse):
            raise ValueError(f"negative prediction MSE: {key}")
        pairs[key]={"dataset":key[0],"data_path":key[1],"rel_eb":key[2],"four_br":numeric(four,"BR"),"six_br":numeric(six,"BR"),"four_psnr":numeric(four,"PSNR"),"six_psnr":numeric(six,"PSNR"),"cubic_mse":mse[0],"quintic_mse":mse[1],"plan_verified":verified,"four_compression_seconds":numeric(four,"COMPRESSION_TIME"),"six_compression_seconds":numeric(six,"COMPRESSION_TIME")}
    if not pairs:
        raise ValueError("no paired observations")
    return pairs


def finite_rd(pair):
    return all(math.isfinite(pair[key]) for key in ("four_br","six_br","four_psnr","six_psnr")) and min(pair["four_br"],pair["six_br"])>0


def summarize(cases,label,path):
    valid=[case for case in cases if case["status"]=="comparable"]
    concordant=sum(case["pair_tau"]==1 for case in valid)
    discordant=len(valid)-concordant
    losses=[case["score_regret"] for case in valid]
    return {"dataset":label,"data_path":path,"total_cases":len(cases),"scored_cases":sum(case["four_score"] is not None for case in cases),"comparable_cases":len(valid),"concordant":concordant,"discordant":discordant,"mse_ties":sum(case["mse_tie"] for case in cases),"rd_ties":sum(case["rd_tie"] for case in cases),"excluded_cases":sum(case["status"] not in ("comparable","mse_tie","rd_tie","both_tied") for case in cases),"mean_pair_tau":(concordant-discordant)/len(valid) if valid else None,"ranking_accuracy":concordant/len(valid) if valid else None,"mean_score_regret":sum(losses)/len(losses) if losses else None,"max_score_regret":max(losses) if losses else None,"verified_cases":sum(case["plan_verified"] for case in cases)}


def analyze(records,allow_unverified_plans=False,mse_rtol=1e-12,score_rtol=1e-12):
    if not math.isfinite(mse_rtol) or not math.isfinite(score_rtol) or min(mse_rtol,score_rtol)<0:
        raise ValueError("tie tolerances must be nonnegative and finite")
    pairs=collect_pairs(records,allow_unverified_plans)
    files=defaultdict(list)
    for key,pair in pairs.items():
        files[key[:2]].append(pair)
    cases=[]
    summaries=[]
    for (label,path),observations in sorted(files.items()):
        observations.sort(key=lambda pair:pair["rel_eb"],reverse=True)
        current=[]
        for index,pair in enumerate(observations):
            case={**pair,"status":"comparable","mse_choice":None,"rd_choice":None,"mse_tie":False,"rd_tie":False,"slope":None,"slope_kind":None,"four_score":None,"six_score":None,"six_score_gain":None,"pair_tau":None,"correct":None,"score_regret":None,"slope_left_eb":None,"slope_right_eb":None}
            current.append(case)
            if all(math.isfinite(pair[key]) for key in ("cubic_mse","quintic_mse")):
                mse_order=rank_sign(pair["cubic_mse"],pair["quintic_mse"],mse_rtol)
                case["mse_tie"]=mse_order==0
                case["mse_choice"]="fixed_6r" if mse_order==1 else "adaptive_4r" if mse_order==-1 else "tie"
            else:
                case["status"]="nonfinite_mse"
                continue
            if not finite_rd(pair):
                case["status"]="nonfinite_or_nonpositive_rd"
                continue
            if len(observations)<2:
                case["status"]="insufficient_rd_points"
                continue
            left=observations[max(0,index-1)]
            right=observations[min(len(observations)-1,index+1)]
            case["slope_left_eb"],case["slope_right_eb"]=left["rel_eb"],right["rel_eb"]
            if not finite_rd(left) or not finite_rd(right):
                case["status"]="nonfinite_slope_neighbor"
                continue
            delta_rate=((right["four_br"]-left["four_br"])+(right["six_br"]-left["six_br"]))/2
            delta_quality=((right["four_psnr"]-left["four_psnr"])+(right["six_psnr"]-left["six_psnr"]))/2
            length=math.hypot(delta_rate,delta_quality)
            if not math.isfinite(length):
                case["status"]="nonfinite_reference"
                continue
            if length==0:
                case["status"]="degenerate_reference"
                continue
            if delta_rate<0 or delta_quality<0:
                case["status"]="nonmonotone_reference"
                continue
            # 单位法向量形式与(PSNR-m*BR)/sqrt(1+m*m)等价，并支持竖直切线。
            rate_weight,quality_weight=-delta_quality/length,delta_rate/length
            four_score=rate_weight*pair["four_br"]+quality_weight*pair["four_psnr"]
            six_score=rate_weight*pair["six_br"]+quality_weight*pair["six_psnr"]
            gain=rate_weight*(pair["six_br"]-pair["four_br"])+quality_weight*(pair["six_psnr"]-pair["four_psnr"])
            rd_order=0 if gain==0 or math.isclose(four_score,six_score,rel_tol=score_rtol,abs_tol=0) else 1 if gain>0 else -1
            case.update({"slope":delta_quality/delta_rate if delta_rate else None,"slope_kind":"finite" if delta_rate else "vertical","four_score":four_score,"six_score":six_score,"six_score_gain":gain,"rd_choice":"fixed_6r" if rd_order==1 else "adaptive_4r" if rd_order==-1 else "tie","rd_tie":rd_order==0})
            if mse_order==0 or rd_order==0:
                case["status"]="both_tied" if mse_order==rd_order==0 else "mse_tie" if mse_order==0 else "rd_tie"
                continue
            tau=mse_order*rd_order
            case.update({"pair_tau":tau,"correct":int(tau==1),"score_regret":0.0 if tau==1 else abs(gain)})
        cases.extend(current)
        summaries.append(summarize(current,label,path))
    pooled=summarize(cases,"ALL","within-file pairs only; no cross-file ranking")
    return cases,summaries,pooled


def write_csv(path,rows):
    with path.open("w",newline="",encoding="utf-8") as output:
        writer=csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def clean_json(value):
    if isinstance(value,float) and not math.isfinite(value):
        return None
    if isinstance(value,dict):
        return {key:clean_json(item) for key,item in value.items()}
    if isinstance(value,list):
        return [clean_json(item) for item in value]
    return value


def save_analysis(records,output,allow_unverified_plans=False,mse_rtol=1e-12,score_rtol=1e-12,input_paths=()):
    cases,summaries,pooled=analyze(records,allow_unverified_plans,mse_rtol,score_rtol)
    output.mkdir(parents=True,exist_ok=False)
    write_csv(output/"cases.csv",cases)
    write_csv(output/"summary.csv",[*summaries,pooled])
    report={"protocol":"raw fixed-cubic/quintic prediction-MSE ordering versus actual adaptive-4R/fixed-6R full-compressor RD ordering","runtime_preference_margin_used":False,"rd_reference":"shared tangent from adjacent error bounds of the two-family averaged actual BR/PSNR curve; one-sided endpoints; vertical tangents use the limiting score -BR","ties":"pair tau undefined; excluded from ranking accuracy and tau; counts reported separately","mse_tie_rtol":mse_rtol,"score_tie_rtol":score_rtol,"tie_atol":0,"regret":"difference between the better RD score and the MSE-selected score, on comparable cases only; not a bitrate percentage","allow_unverified_plans":allow_unverified_plans,"inputs":{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in input_paths},"analysis_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"per_file":summaries,"pooled":pooled}
    (output/"report.json").write_text(json.dumps(clean_json(report),indent=2,allow_nan=False)+"\n")
    print(json.dumps(clean_json(pooled),indent=2,allow_nan=False))
    return report


def cli():
    parser=argparse.ArgumentParser(description="Validate unpenalized MSE-based predictor-family ranking")
    parser.add_argument("--input",type=Path,nargs="+",required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--allow-unverified-plans",action="store_true",help="historical audit only; missing plan/settings hashes are reported as unverified")
    parser.add_argument("--mse-tie-rtol",type=float,default=1e-12)
    parser.add_argument("--score-tie-rtol",type=float,default=1e-12)
    arguments=parser.parse_args()
    records=[]
    for path in arguments.input:
        with path.open(newline="",encoding="utf-8") as source:
            records.extend(csv.DictReader(source))
    save_analysis(records,arguments.output,arguments.allow_unverified_plans,arguments.mse_tie_rtol,arguments.score_tie_rtol,arguments.input)


if __name__=="__main__":
    cli()
