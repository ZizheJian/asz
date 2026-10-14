import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

project_root=Path(__file__).resolve().parent
dataset_files=(("Isabel_Pf24","Isabel","isabel.csv"),("CESM_T_t31","CESM T","cesmt.csv"),("LETKF_QV_log10","LETKF QV","letkf_qv.csv"),("Aramco_1800","Aramco","aramco.csv"),("LETKF_PRES","LETKF PRES","letkf_pres.csv"),("QMCPACK_orbital0","QMCPACK","qmcpack.csv"))
rel_ebs=[1e-1,1e-2,1e-3,1e-4,1e-5]
fixed_methods=[f"fixed_{numerator}_32" for numerator in range(2,13)]
selection_order=["fixed_8_32",*[method for method in fixed_methods if method!="fixed_8_32"]]

def close(a,b):
    return math.isclose(a,b,rel_tol=1e-12,abs_tol=0.0)

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
    if close(target,points[0][0]):
        return math.log(points[0][1])
    if close(target,points[-1][0]):
        return math.log(points[-1][1])
    raise ValueError(f"PSNR {target} is outside [{points[0][0]},{points[-1][0]}]")

def envelope_log_br(curves,target):
    values=[interpolate_log_br(curve,target) for curve in curves if curve[0][0]<=target<=curve[-1][0]]
    if not values:
        raise ValueError(f"global fixed-coefficient envelope is undefined at PSNR {target}")
    return min(values)

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
        difference=interpolate_log_br(candidate,target)-envelope_log_br(global_curves,target)
        differences.append(difference)
        wins+=difference<0
    integral=sum((differences[index]+differences[index+1])/2 for index in range(samples-1))/(samples-1)
    return math.exp(integral),wins/samples,left,right

def load_results(input_directory):
    results={}
    hashes={}
    for dataset,_,filename in dataset_files:
        path=input_directory/filename
        completed=input_directory/(path.stem+"-completed.json")
        if not path.is_file() or not completed.is_file():
            raise FileNotFoundError(f"incomplete dataset result: {path}")
        hashes[str(path.relative_to(project_root))]=sha256(path)
        rows=list(csv.DictReader(open(path,newline="",encoding="utf-8")))
        expected={(rel_eb,method) for rel_eb in rel_ebs for method in (*fixed_methods,"block_peaks","block_full")}
        observed={(float(row["REL_EB"]),row["METHOD"]) for row in rows}
        if observed!=expected or len(rows)!=len(expected):
            raise ValueError(f"{path} has {len(rows)} rows but expected {len(expected)} unique cases")
        results[dataset]={(float(row["REL_EB"]),row["METHOD"]):{"br":float(row["BR"]),"psnr":float(row["PSNR"]),"compression_time":float(row["COMPRESSION_TIME"]),"decompression_time":float(row["DECOMPRESSION_TIME"])} for row in rows}
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
        raise ValueError(f"nonmonotone global reference at {rel_eb:g}: delta_br={delta_br},delta_psnr={delta_psnr}")
    return delta_psnr/delta_br,left,right

def score(point,slope):
    return (point["psnr"]-slope*point["br"])/math.sqrt(1+slope*slope)

def choose_global(rows,rel_eb,slope):
    scores={method:score(rows[(rel_eb,method)],slope) for method in fixed_methods}
    best=max(scores.values())
    tied={method for method,value in scores.items() if close(value,best)}
    selected=next(method for method in selection_order if method in tied)
    return selected,best,tied

def analyze(results):
    cases=[]
    summaries=[]
    ratios={"block_peaks":[],"block_full":[]}
    for dataset,label,_ in dataset_files:
        rows=results[dataset]
        global_curves=[]
        for method in fixed_methods:
            global_curves.append([(rows[(rel_eb,method)]["psnr"],rows[(rel_eb,method)]["br"]) for rel_eb in rel_ebs])
        dataset_values={}
        for block_method in ("block_peaks","block_full"):
            candidate=[(rows[(rel_eb,block_method)]["psnr"],rows[(rel_eb,block_method)]["br"]) for rel_eb in rel_ebs]
            ratio,win_fraction,left,right=compare_to_envelope(candidate,global_curves)
            ratios[block_method].append(ratio)
            dataset_values[block_method]=(ratio,win_fraction,left,right)
        score_gains={"block_peaks":[],"block_full":[]}
        for rel_eb in rel_ebs:
            slope,left,right=local_slope(rows,rel_eb)
            selected,best,tied=choose_global(rows,rel_eb,slope)
            case={"dataset":dataset,"rel_eb":rel_eb,"slope":slope,"slope_left_eb":left,"slope_right_eb":right,"best_global_method":selected,"best_global_t":int(selected.split("_")[1])/32,"best_global_tied":len(tied)>1,"best_global_br":rows[(rel_eb,selected)]["br"],"best_global_psnr":rows[(rel_eb,selected)]["psnr"]}
            for block_method in ("block_peaks","block_full"):
                gain=score(rows[(rel_eb,block_method)],slope)-best
                score_gains[block_method].append(gain)
                case[block_method+"_br"]=rows[(rel_eb,block_method)]["br"]
                case[block_method+"_psnr"]=rows[(rel_eb,block_method)]["psnr"]
                case[block_method+"_score_gain"]=gain
            cases.append(case)
        peaks=dataset_values["block_peaks"]
        full=dataset_values["block_full"]
        summaries.append({"dataset":dataset,"label":label,"peaks_equal_psnr_bitrate_reduction_percent":100*(1-peaks[0]),"full_equal_psnr_bitrate_reduction_percent":100*(1-full[0]),"peaks_winning_psnr_fraction_percent":100*peaks[1],"full_winning_psnr_fraction_percent":100*full[1],"peaks_mean_score_gain":sum(score_gains["block_peaks"])/len(rel_ebs),"peaks_min_score_gain":min(score_gains["block_peaks"]),"peaks_max_score_gain":max(score_gains["block_peaks"]),"full_mean_score_gain":sum(score_gains["block_full"])/len(rel_ebs),"full_min_score_gain":min(score_gains["block_full"]),"full_max_score_gain":max(score_gains["block_full"]),"common_psnr_left":peaks[2],"common_psnr_right":peaks[3]})
    def aggregate(dataset,label,selected):
        return {"dataset":dataset,"label":label,"peaks_equal_psnr_bitrate_reduction_percent":100*(1-geometric_mean([1-row["peaks_equal_psnr_bitrate_reduction_percent"]/100 for row in selected])),"full_equal_psnr_bitrate_reduction_percent":100*(1-geometric_mean([1-row["full_equal_psnr_bitrate_reduction_percent"]/100 for row in selected])),"peaks_winning_psnr_fraction_percent":sum(row["peaks_winning_psnr_fraction_percent"] for row in selected)/len(selected),"full_winning_psnr_fraction_percent":sum(row["full_winning_psnr_fraction_percent"] for row in selected)/len(selected),"peaks_mean_score_gain":sum(row["peaks_mean_score_gain"] for row in selected)/len(selected),"peaks_min_score_gain":min(row["peaks_min_score_gain"] for row in selected),"peaks_max_score_gain":max(row["peaks_max_score_gain"] for row in selected),"full_mean_score_gain":sum(row["full_mean_score_gain"] for row in selected)/len(selected),"full_min_score_gain":min(row["full_min_score_gain"] for row in selected),"full_max_score_gain":max(row["full_max_score_gain"] for row in selected),"common_psnr_left":"","common_psnr_right":""}
    summaries.extend([aggregate("Retained_1D4R","Retained 1D4R",summaries[:3]),aggregate("Pruned_1D4R","Pruned 1D4R",summaries[3:]),aggregate("Overall","All six",summaries)])
    return cases,summaries

def write_csv(path,rows):
    temporary=path.with_name(path.name+".tmp")
    with open(temporary,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=rows[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)

def plot_gain(summaries,output):
    rows=summaries[:len(dataset_files)]
    values=[value for row in rows for value in (row["peaks_equal_psnr_bitrate_reduction_percent"],row["full_equal_psnr_bitrate_reduction_percent"])]
    y_min=10*math.floor(min(0,min(values))/10)
    y_max=10*math.ceil(max(0,max(values))/10)
    scale=2.45/(y_max-y_min)
    lines=[r"\documentclass[tikz,border=2pt]{standalone}",r"\usepackage{newtxtext,newtxmath}",r"\begin{document}",r"\begin{tikzpicture}[font=\scriptsize]",rf"\draw[->] (0,{(0-y_min)*scale:.4f}) -- (7.05,{(0-y_min)*scale:.4f});",r"\draw[->] (0,0) -- (0,2.72);"]
    tick_step=20 if y_max-y_min>=60 else 10
    for value in range(int(y_min),int(y_max)+1,tick_step):
        y=(value-y_min)*scale
        lines.append(rf"\draw (-0.05,{y:.4f}) -- (0,{y:.4f}); \node[anchor=east] at (-0.08,{y:.4f}) {{{value}}};")
    for index,row in enumerate(rows):
        center=0.65+index*1.02
        for offset,key,color in ((-0.16,"peaks_equal_psnr_bitrate_reduction_percent","blue!65"),(0.16,"full_equal_psnr_bitrate_reduction_percent","orange!85!black")):
            value=row[key]
            zero=(0-y_min)*scale
            top=(value-y_min)*scale
            lines.append(rf"\fill[{color}] ({center+offset-0.13:.4f},{min(zero,top):.4f}) rectangle ({center+offset+0.13:.4f},{max(zero,top):.4f});")
        lines.append(rf"\node[rotate=30,anchor=north east] at ({center+0.25:.4f},-0.05) {{{row['label']}}};")
    lines.extend([r"\node[rotate=90] at (-0.68,1.25) {Equal-PSNR bitrate reduction (\%)};",r"\fill[blue!65] (2.00,2.57) rectangle (2.22,2.69); \node[anchor=west] at (2.27,2.63) {Five candidates};",r"\fill[orange!85!black] (4.20,2.57) rectangle (4.42,2.69); \node[anchor=west] at (4.47,2.63) {Full grid};",r"\end{tikzpicture}",r"\end{document}"])
    tex_path=output/"blockwise-coefficient-selection-gain.tex"
    with open(tex_path,"w",encoding="utf-8") as output_file:
        output_file.write("\n".join(lines)+"\n")
    pdflatex=shutil.which("pdflatex")
    if pdflatex is None:
        raise RuntimeError(f"pdflatex is unavailable; generated {tex_path}")
    subprocess.run([pdflatex,"-interaction=nonstopmode","-halt-on-error",tex_path.name],cwd=output,check=True,stdout=subprocess.DEVNULL)

def self_test():
    curve=[(10,1),(20,2),(30,4)]
    assert close(interpolate_log_br(curve,20),math.log(2))
    ratio,win,_,_=compare_to_envelope([(10,0.9),(20,1.8),(30,3.6)],[curve],1001)
    assert close(ratio,0.9) and win==1

def main():
    parser=argparse.ArgumentParser(description="Analyze complete-compression global versus block-wise coefficient selection")
    parser.add_argument("--input",type=Path,default=project_root/"results/coefficient-blockwise-20261012")
    parser.add_argument("--output",type=Path)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    self_test()
    if args.self_test:
        print("self-test passed")
        return
    input_directory=args.input.resolve()
    output=(args.output or input_directory/"analysis").resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    results,input_hashes=load_results(input_directory)
    cases,summaries=analyze(results)
    write_csv(output/"cases.csv",cases)
    write_csv(output/"dataset-summary.csv",summaries)
    plot_gain(summaries,output)
    report={"protocol":"complete-compression comparison of the five-candidate and full-grid block-wise selectors against the lower envelope of eleven globally fixed-coefficient RD curves","equal_psnr_analysis":"Pareto filtering and log-bitrate interpolation; block curve compared with the minimum interpolated bitrate among all fixed-coefficient curves at each of 20,001 uniformly spaced PSNR samples","score_analysis":"best global coefficient and block-wise points use the same tangent estimated from neighboring coefficient-averaged global curves","input_sha256":input_hashes}
    temporary=output/"report.json.tmp"
    with open(temporary,"w",encoding="utf-8") as output_file:
        json.dump(report,output_file,indent=2)
        output_file.write("\n")
    temporary.replace(output/"report.json")
    for row in summaries:
        print(f"{row['label']}: peaks={row['peaks_equal_psnr_bitrate_reduction_percent']:+.3f}%,full={row['full_equal_psnr_bitrate_reduction_percent']:+.3f}%,peaks_mean_score_gain={row['peaks_mean_score_gain']:+.6g}")
    print(f"wrote {output}")

if __name__=="__main__":
    main()
