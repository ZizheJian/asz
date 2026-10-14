import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

project_root=Path(__file__).resolve().parent
datasets=(("APS_Kaz","aps_kaz.csv"),("Isabel_Pf01","isabel_pf01.csv"),("VideoLLaVA","videollava.csv"))
rel_ebs=[1e-1,1e-2,1e-3,1e-4,1e-5]
fixed_methods=[f"fixed_{numerator}_16" for numerator in range(3,7)]

def sha256(path):
    digest=hashlib.sha256()
    with open(path,"rb") as input_file:
        while chunk:=input_file.read(1<<20):
            digest.update(chunk)
    return digest.hexdigest()

def geometric_mean(values):
    return math.exp(sum(math.log(value) for value in values)/len(values))

def pareto_curve(points):
    best_by_psnr={}
    for psnr,br in points:
        if not math.isfinite(psnr) or not math.isfinite(br) or br<=0:
            raise ValueError(f"invalid RD point: psnr={psnr},br={br}")
        best_by_psnr[psnr]=min(br,best_by_psnr.get(psnr,math.inf))
    frontier=[]
    best_br=math.inf
    for psnr in sorted(best_by_psnr,reverse=True):
        br=best_by_psnr[psnr]
        if br<best_br:
            frontier.append((psnr,br))
            best_br=br
    frontier.sort()
    if len(frontier)<2:
        raise ValueError("an RD curve needs at least two Pareto points")
    return frontier

def interpolate_log_br(points,target):
    for left,right in zip(points,points[1:]):
        if left[0]<=target<=right[0]:
            weight=(target-left[0])/(right[0]-left[0])
            return math.log(left[1])+weight*(math.log(right[1])-math.log(left[1]))
    raise ValueError(f"PSNR {target} is outside [{points[0][0]},{points[-1][0]}]")

def compare_to_envelope(candidate,global_curves,samples=20001):
    candidate=pareto_curve(candidate)
    global_curves=[pareto_curve(curve) for curve in global_curves]
    left=max(candidate[0][0],min(curve[0][0] for curve in global_curves))
    right=min(candidate[-1][0],max(curve[-1][0] for curve in global_curves))
    if left>=right:
        raise ValueError("candidate and global envelope have no common PSNR interval")
    differences=[]
    wins=0
    for index in range(samples):
        target=left+(right-left)*index/(samples-1)
        available=[interpolate_log_br(curve,target) for curve in global_curves if curve[0][0]<=target<=curve[-1][0]]
        if not available:
            raise ValueError(f"global envelope is undefined at PSNR {target}")
        difference=interpolate_log_br(candidate,target)-min(available)
        differences.append(difference)
        wins+=difference<0
    integral=sum((differences[index]+differences[index+1])/2 for index in range(samples-1))/(samples-1)
    return math.exp(integral),wins/samples,left,right

def load_results(input_directory):
    results={}
    hashes={}
    expected={(rel_eb,method) for rel_eb in rel_ebs for method in ("block_adaptive",*fixed_methods)}
    for dataset,filename in datasets:
        path=input_directory/filename
        completed=input_directory/(path.stem+"-completed.json")
        if not path.is_file() or not completed.is_file():
            raise FileNotFoundError(f"incomplete dataset result: {path}")
        rows=list(csv.DictReader(open(path,newline="",encoding="utf-8")))
        observed={(float(row["REL_EB"]),row["METHOD"]) for row in rows}
        if observed!=expected or len(rows)!=len(expected):
            raise ValueError(f"{path} has {len(rows)} rows but expected {len(expected)} unique cases")
        results[dataset]={(float(row["REL_EB"]),row["METHOD"]):{"br":float(row["BR"]),"psnr":float(row["PSNR"]),"cr":float(row["CR"])} for row in rows}
        hashes[str(path.relative_to(project_root))]=sha256(path)
        hashes[str(completed.relative_to(project_root))]=sha256(completed)
    return results,hashes

def local_slope(rows,rel_eb):
    index=rel_ebs.index(rel_eb)
    left=rel_ebs[index-1] if index else rel_eb
    right=rel_ebs[index+1] if index+1<len(rel_ebs) else rel_eb
    averages={}
    for bound in (left,right):
        averages[bound]=(sum(rows[(bound,method)]["br"] for method in fixed_methods)/len(fixed_methods),sum(rows[(bound,method)]["psnr"] for method in fixed_methods)/len(fixed_methods))
    delta_br=averages[right][0]-averages[left][0]
    delta_psnr=averages[right][1]-averages[left][1]
    if delta_br<=0 or delta_psnr<=0:
        raise ValueError(f"nonmonotone reference at {rel_eb:g}: delta_br={delta_br},delta_psnr={delta_psnr}")
    return delta_psnr/delta_br

def score(point,slope):
    return (point["psnr"]-slope*point["br"])/math.sqrt(1+slope*slope)

def analyze(results):
    cases=[]
    summaries=[]
    ratios=[]
    for dataset,_ in datasets:
        rows=results[dataset]
        global_curves=[[(rows[(rel_eb,method)]["psnr"],rows[(rel_eb,method)]["br"]) for rel_eb in rel_ebs] for method in fixed_methods]
        adaptive_curve=[(rows[(rel_eb,"block_adaptive")]["psnr"],rows[(rel_eb,"block_adaptive")]["br"]) for rel_eb in rel_ebs]
        ratio,win_fraction,left,right=compare_to_envelope(adaptive_curve,global_curves)
        ratios.append(ratio)
        score_gains=[]
        bitrate_reductions=[]
        undefined_score_cases=0
        for rel_eb in rel_ebs:
            adaptive=rows[(rel_eb,"block_adaptive")]
            try:
                slope=local_slope(rows,rel_eb)
            except ValueError:
                undefined_score_cases+=1
                cases.append({"dataset":dataset,"rel_eb":rel_eb,"best_global_method":"","best_global_br":"","best_global_psnr":"","adaptive_br":adaptive["br"],"adaptive_psnr":adaptive["psnr"],"same_bound_bitrate_reduction_percent":"","psnr_delta":"","rd_score_gain":"","rd_score_defined":False})
                continue
            fixed_scores={method:score(rows[(rel_eb,method)],slope) for method in fixed_methods}
            best_method=max(fixed_methods,key=lambda method:fixed_scores[method])
            best=rows[(rel_eb,best_method)]
            score_gain=score(adaptive,slope)-fixed_scores[best_method]
            bitrate_reduction=100*(best["br"]-adaptive["br"])/best["br"]
            score_gains.append(score_gain)
            bitrate_reductions.append(bitrate_reduction)
            cases.append({"dataset":dataset,"rel_eb":rel_eb,"best_global_method":best_method,"best_global_br":best["br"],"best_global_psnr":best["psnr"],"adaptive_br":adaptive["br"],"adaptive_psnr":adaptive["psnr"],"same_bound_bitrate_reduction_percent":bitrate_reduction,"psnr_delta":adaptive["psnr"]-best["psnr"],"rd_score_gain":score_gain,"rd_score_defined":True})
        summaries.append({"dataset":dataset,"equal_psnr_bitrate_reduction_percent":100*(1-ratio),"winning_psnr_fraction_percent":100*win_fraction,"mean_same_bound_bitrate_reduction_percent":sum(bitrate_reductions)/len(bitrate_reductions),"mean_rd_score_gain":sum(score_gains)/len(score_gains),"min_rd_score_gain":min(score_gains),"max_rd_score_gain":max(score_gains),"undefined_score_cases":undefined_score_cases,"common_psnr_left":left,"common_psnr_right":right})
    summaries.append({"dataset":"Overall","equal_psnr_bitrate_reduction_percent":100*(1-geometric_mean(ratios)),"winning_psnr_fraction_percent":sum(row["winning_psnr_fraction_percent"] for row in summaries)/len(summaries),"mean_same_bound_bitrate_reduction_percent":sum(row["mean_same_bound_bitrate_reduction_percent"] for row in summaries)/len(summaries),"mean_rd_score_gain":sum(row["mean_rd_score_gain"] for row in summaries)/len(summaries),"min_rd_score_gain":min(row["min_rd_score_gain"] for row in summaries),"max_rd_score_gain":max(row["max_rd_score_gain"] for row in summaries),"undefined_score_cases":sum(row["undefined_score_cases"] for row in summaries),"common_psnr_left":"","common_psnr_right":""})
    return cases,summaries

def write_csv(path,rows):
    temporary=path.with_name(path.name+".tmp")
    with open(temporary,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=rows[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)

def main():
    parser=argparse.ArgumentParser(description="Analyze the controlled legacy 1D4R coefficient reproduction")
    parser.add_argument("--input",type=Path,default=project_root/"results/coefficient-blockwise-legacy-1d4r-20261012")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    input_directory=args.input.resolve()
    output=(args.output or input_directory/"analysis").resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    results,input_hashes=load_results(input_directory)
    cases,summaries=analyze(results)
    output.mkdir(parents=True)
    write_csv(output/"cases.csv",cases)
    write_csv(output/"dataset-summary.csv",summaries)
    report={"protocol":"commit 45c856e; naturally 1D4R datasets only; one frozen plan; block-wise adaptive coefficients compared against the equal-PSNR lower envelope of all four globally fixed legacy candidates","input_sha256":input_hashes}
    with open(output/"report.json","w",encoding="utf-8") as output_file:
        json.dump(report,output_file,indent=2)
        output_file.write("\n")
    for row in summaries:
        print(f"{row['dataset']}: equal-PSNR bitrate reduction={row['equal_psnr_bitrate_reduction_percent']:+.3f}%,mean RD score gain={row['mean_rd_score_gain']:+.6g}")

if __name__=="__main__":
    main()
