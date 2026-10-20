import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

from paper_plot_layout import add_panel_captions,style_plot_axis


project_root=Path(__file__).resolve().parent
candidate_t=[i/32 for i in range(2,13)]
selection_order=[1/4,*[value for value in candidate_t if value!=1/4]]
rel_ebs=[1e-1,1e-2,1e-3,1e-4,1e-5]
criteria=("h1_psnr","h1_only","psnr_only","prediction_mse","prediction_mae")
criterion_labels={"h1_psnr":r"$H_1$--PSNR","h1_only":r"$H_1$","psnr_only":"PSNR","prediction_mse":"Prediction MSE","prediction_mae":"Prediction MAE"}
datasets=(
    ("Isabel_Pf24","Isabel","results/predictor-family-4r6r-middle-21250842","isabel"),
    ("CESM_T_t31","CESM T","results/predictor-family-4r6r-middle-21250842","cesmt"),
    ("LETKF_QV_log10","LETKF QV","results/predictor-family-4r6r-supplement-21274865","letkf_qv"),
    ("Aramco_1800","Aramco","results/predictor-family-4r6r-middle-21250842","aramco"),
    ("LETKF_PRES","LETKF PRES","results/predictor-family-4r6r-supplement-21274865","letkf"),
    ("QMCPACK_orbital0","QMCPACK","results/predictor-family-4r6r-qmcpack-orbital0-20261011","qmcpack"),
)

def close(a,b):
    return math.isclose(a,b,rel_tol=1e-12,abs_tol=0.0)

def sha256(path):
    digest=hashlib.sha256()
    with open(path,"rb") as input_file:
        while chunk:=input_file.read(1<<20):
            digest.update(chunk)
    return digest.hexdigest()

def candidate_index(value):
    for index,candidate in enumerate(candidate_t):
        if close(value,candidate):
            return index
    return None

def read_measurements():
    measurements={}
    input_hashes={}
    for dataset,_,directory,prefix in datasets:
        for direction in range(3):
            for order in range(3):
                path=project_root/directory/f"{prefix}_1d4r{direction}_xx{order}.csv"
                input_hashes[str(path.relative_to(project_root))]=sha256(path)
                grouped=defaultdict(dict)
                with open(path,newline="",encoding="utf-8") as input_file:
                    for row in csv.DictReader(input_file):
                        rel_eb=float(row["rel_eb"])
                        t=float(row["t1"])
                        index=candidate_index(t)
                        if index is None:
                            continue
                        grouped[rel_eb][candidate_t[index]]={key:float(row[key]) for key in ("BR","H1","MAE","PSNR","RMSE")}
                if set(grouped)!=set(rel_ebs):
                    raise ValueError(f"{path} error-bound grid is incomplete")
                for rel_eb in rel_ebs:
                    if set(grouped[rel_eb])!=set(candidate_t):
                        raise ValueError(f"{path} coefficient grid is incomplete at {rel_eb:g}")
                measurements[(dataset,direction,order)]=grouped
    return measurements,input_hashes

def local_slope(grouped,metric,rel_eb):
    index=rel_ebs.index(rel_eb)
    left=rel_ebs[index-1] if index else rel_eb
    right=rel_ebs[index+1] if index+1<len(rel_ebs) else rel_eb
    mean_metric={bound:sum(grouped[bound][t][metric] for t in candidate_t)/len(candidate_t) for bound in (left,right)}
    mean_psnr={bound:sum(grouped[bound][t]["PSNR"] for t in candidate_t)/len(candidate_t) for bound in (left,right)}
    delta_metric=mean_metric[right]-mean_metric[left]
    delta_psnr=mean_psnr[right]-mean_psnr[left]
    scale=max(1.0,abs(mean_metric[left]),abs(mean_metric[right]))
    if abs(delta_metric)<=64*math.ulp(scale):
        values=[grouped[rel_eb][t][metric] for t in candidate_t]
        if all(close(value,values[0]) for value in values[1:]):
            return None,"equal_rate_psnr",left,right
        return None,"undefined",left,right
    slope=delta_psnr/delta_metric
    if not math.isfinite(slope) or slope<=0:
        return None,"undefined",left,right
    return slope,"tangent",left,right

def score_values(grouped,rel_eb,metric):
    slope,kind,left,right=local_slope(grouped,metric,rel_eb)
    if kind=="undefined":
        return None,slope,kind,left,right
    if kind=="equal_rate_psnr":
        return {t:grouped[rel_eb][t]["PSNR"] for t in candidate_t},slope,kind,left,right
    denominator=math.sqrt(1+slope*slope)
    scores={t:(grouped[rel_eb][t]["PSNR"]-slope*grouped[rel_eb][t][metric])/denominator for t in candidate_t}
    return scores,slope,kind,left,right

def optimum_set(values):
    best=max(values.values())
    return {t for t,value in values.items() if close(value,best)}

def select(values):
    best=max(values.values())
    tied={t for t,value in values.items() if close(value,best)}
    return next(t for t in selection_order if t in tied),tied

def analyze(measurements):
    rows=[]
    for dataset,_,_,_ in datasets:
        for direction in range(3):
            for order in range(3):
                grouped=measurements[(dataset,direction,order)]
                for rel_eb in rel_ebs:
                    ground_scores,br_slope,br_kind,left,right=score_values(grouped,rel_eb,"BR")
                    proxy_scores,h1_slope,h1_kind,_,_=score_values(grouped,rel_eb,"H1")
                    if ground_scores is None:
                        continue
                    ground_optima=optimum_set(ground_scores)
                    ground_best=max(ground_scores.values())
                    value_maps={
                        "h1_psnr":proxy_scores,
                        "h1_only":{t:-grouped[rel_eb][t]["H1"] for t in candidate_t},
                        "psnr_only":{t:grouped[rel_eb][t]["PSNR"] for t in candidate_t},
                        "prediction_mse":{t:-grouped[rel_eb][t]["RMSE"]**2 for t in candidate_t},
                        "prediction_mae":{t:-grouped[rel_eb][t]["MAE"] for t in candidate_t},
                    }
                    for criterion,values in value_maps.items():
                        if values is None:
                            continue
                        selected,tied=select(values)
                        rows.append({"dataset":dataset,"rel_eb":rel_eb,"direction":direction,"order":order,"criterion":criterion,"selected_t":selected,"selected_tied":len(tied)>1,"ground_t":"|".join(f"{t:.5f}" for t in sorted(ground_optima)),"ground_tied":len(ground_optima)>1,"agreement":selected in ground_optima,"score_loss":max(0.0,ground_best-ground_scores[selected]),"ground_score":ground_best,"selected_ground_score":ground_scores[selected],"br_slope":br_slope,"br_score_kind":br_kind,"h1_slope":h1_slope,"h1_score_kind":h1_kind,"slope_left_eb":left,"slope_right_eb":right})
    return rows

def summarize(rows):
    summary=[]
    for criterion in criteria:
        criterion_rows=[row for row in rows if row["criterion"]==criterion]
        non_tied=[row for row in criterion_rows if not row["ground_tied"]]
        losses=[row["score_loss"] for row in non_tied]
        summary.append({"criterion":criterion,"cases":len(criterion_rows),"ground_tied_cases":len(criterion_rows)-len(non_tied),"non_tied_cases":len(non_tied),"agreement_percent":100*sum(row["agreement"] for row in non_tied)/len(non_tied),"mean_score_loss":sum(losses)/len(losses),"max_score_loss":max(losses)})
    return summary

def write_csv(path,rows,fieldnames):
    temporary=path.with_name(path.name+".tmp")
    with open(temporary,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)

def plot_heatmap(rows,output):
    proxy=[row for row in rows if row["criterion"]=="h1_psnr" and not row["ground_tied"]]
    agreements=[[0 for _ in rel_ebs] for _ in datasets]
    totals=[[0 for _ in rel_ebs] for _ in datasets]
    for dataset_index,(dataset,_,_,_) in enumerate(datasets):
        for eb_index,rel_eb in enumerate(rel_ebs):
            cell=[row for row in proxy if row["dataset"]==dataset and row["rel_eb"]==rel_eb]
            agreements[dataset_index][eb_index]=sum(row["agreement"] for row in cell)
            totals[dataset_index][eb_index]=len(cell)
    lines=[r"\documentclass[tikz,border=2pt]{standalone}",r"\usepackage{newtxtext,newtxmath}",r"\begin{document}",r"\begin{tikzpicture}[font=\scriptsize]",r"\def\cw{0.73}",r"\def\ch{0.43}"]
    for row_index,(_,label,_,_) in enumerate(datasets):
        y=-row_index*0.43
        lines.append(rf"\node[anchor=east] at (-0.08,{y-0.215:.4f}) {{{label}}};")
        for column_index in range(len(rel_ebs)):
            intensity=round(100*agreements[row_index][column_index]/totals[row_index][column_index])
            text_color="white" if intensity>=60 else "black"
            x=column_index*0.73
            lines.append(rf"\filldraw[fill=blue!{intensity}!white,draw=white,line width=0.25pt] ({x:.4f},{y:.4f}) rectangle ({x+0.73:.4f},{y-0.43:.4f});")
            lines.append(rf"\node[text={text_color}] at ({x+0.365:.4f},{y-0.215:.4f}) {{{agreements[row_index][column_index]}/{totals[row_index][column_index]}}};")
    bottom=-len(datasets)*0.43
    for column_index,power in enumerate(range(1,6)):
        lines.append(rf"\node[anchor=north] at ({column_index*0.73+0.365:.4f},{bottom-0.03:.4f}) {{$10^{{-{power}}}$}};")
    lines.append(rf"\node[anchor=north] at ({5*0.73/2:.4f},{bottom-0.43:.4f}) {{Relative error bound}};")
    bar_x=5*0.73+0.20
    for index in range(50):
        intensity=round(100*index/49)
        y=bottom+index*(len(datasets)*0.43/50)
        lines.append(rf"\fill[blue!{intensity}!white] ({bar_x:.4f},{y:.4f}) rectangle ({bar_x+0.16:.4f},{y+len(datasets)*0.43/50+0.001:.4f});")
    lines.extend([rf"\node[anchor=west] at ({bar_x+0.20:.4f},{bottom:.4f}) {{0\%}};",rf"\node[anchor=west] at ({bar_x+0.20:.4f},0) {{100\%}};",rf"\node[rotate=90] at ({bar_x+0.72:.4f},{bottom/2:.4f}) {{Agreement}};",r"\end{tikzpicture}",r"\end{document}"])
    tex_path=output/"global-coefficient-selection-heatmap.tex"
    with open(tex_path,"w",encoding="utf-8") as output_file:
        output_file.write("\n".join(lines)+"\n")
    pdflatex=shutil.which("pdflatex")
    if pdflatex is None:
        raise RuntimeError(f"pdflatex is unavailable; generated {tex_path}")
    subprocess.run([pdflatex,"-interaction=nonstopmode","-halt-on-error",tex_path.name],cwd=output,check=True,stdout=subprocess.DEVNULL)

def plot_validation_triptych(measurements,rows,output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.ticker import MaxNLocator,NullLocator
    summary={row["criterion"]:row for row in summarize(rows)}
    plt.rcParams.update({"font.family":"Nimbus Roman","mathtext.fontset":"stix","font.size":8,"axes.labelsize":8,"axes.titlesize":8,"xtick.labelsize":8,"ytick.labelsize":8,"pdf.fonttype":42})
    figure,axes=plt.subplots(1,3,figsize=(3.5,104/72))
    values=[summary[criterion]["agreement_percent"] for criterion in criteria]
    labels=[r"$H_1$--PSNR",r"$H_1$","PSNR","MSE","MAE"]
    axes[0].bar(range(len(criteria)),values,color=["#3b4cc0",*["#b8b8b8"]*4],width=0.72)
    axes[0].set_ylim(0,118)
    axes[0].set_yticks([0,50,100])
    axes[0].set_ylabel("Agreement (%)",labelpad=1)
    axes[0].set_xticks(range(len(criteria)),labels,rotation=45,ha="right",rotation_mode="anchor")
    axes[0].text(.15,values[0]+6,"95.93",ha="center",va="bottom",fontsize=6,color="#243391")
    grouped=measurements[("Isabel_Pf24",0,0)]
    normalizer=Normalize(min(candidate_t),max(candidate_t))
    color_map=plt.get_cmap("viridis")
    for t in candidate_t:
        psnr=[grouped[rel_eb][t]["PSNR"] for rel_eb in rel_ebs]
        color=color_map(normalizer(t))
        axes[1].plot([grouped[rel_eb][t]["BR"] for rel_eb in rel_ebs],psnr,"-o",color=color,linewidth=.8,markersize=1.4)
        axes[2].plot([grouped[rel_eb][t]["H1"] for rel_eb in rel_ebs],psnr,"-o",color=color,linewidth=.8,markersize=1.4)
    for axis,xlabel in zip(axes[1:],["BR (bits/value)",r"$H_1$ (bits/value)"]):
        axis.set_xscale("log")
        axis.xaxis.set_minor_locator(NullLocator())
        axis.set_xlabel(xlabel,labelpad=1)
        axis.margins(y=.08)
        axis.yaxis.set_major_locator(MaxNLocator(nbins=4,min_n_ticks=3))
    axes[1].set_ylabel("PSNR (dB)",labelpad=0)
    axes[2].set_ylabel("PSNR (dB)",labelpad=0)
    titles=["(a) Overall selection","(b) BR–PSNR",r"(c) $H_1$–PSNR"]
    for index,axis in enumerate(axes):
        axis.set_box_aspect(1)
        style_plot_axis(axis,grid_axis="y" if index==0 else "both")
    figure.subplots_adjust(left=.105,right=.995,bottom=.38,top=.95,wspace=.4)
    captions=add_panel_captions(figure,axes,titles,8,gap_pt=-4)
    caption_y=min(caption.get_position()[1] for caption in captions)
    for caption in captions:
        caption.set_y(caption_y)
    figure.savefig(output/"coefficient-proxy-validation.pdf")
    plt.close(figure)

def self_test():
    values={t:-(t-0.25)**2 for t in candidate_t}
    selected,tied=select(values)
    assert selected==0.25 and tied=={0.25}
    tied_values={t:0.0 for t in candidate_t}
    selected,tied=select(tied_values)
    assert selected==0.25 and len(tied)==len(candidate_t)
    assert candidate_index(0.25000000000001)==6

def main():
    parser=argparse.ArgumentParser(description="Validate global 1D4R coefficient-selection criteria from complete legacy sweeps")
    parser.add_argument("--output",type=Path,default=project_root/"results/coefficient-proxy-global-20261012")
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    self_test()
    if args.self_test:
        print("self-test passed")
        return
    output=args.output.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    measurements,input_hashes=read_measurements()
    rows=analyze(measurements)
    summary=summarize(rows)
    write_csv(output/"cases.csv",rows,list(rows[0]))
    write_csv(output/"summary.csv",summary,list(summary[0]))
    plot_heatmap(rows,output)
    plot_validation_triptych(measurements,rows,output)
    report={"protocol":"global 1D4R coefficient selection on fixed dataset/direction/QB-order cases; actual Huffman-Zstd QB-stream BR-PSNR is ground truth","datasets":[dataset for dataset,_,_,_ in datasets],"relative_error_bounds":rel_ebs,"directions":[0,1,2],"qb_orders":[0,1,2],"candidate_t":[f"{round(t*32)}/32" for t in candidate_t],"tie_break":"ASZ order: initialize at 1/4,then scan candidates in ascending order; ground-score ties count as agreement","slope":"neighboring coefficient-averaged points; centered differences internally and one-sided differences at endpoints","rate_scope":"Huffman plus Zstd level-3 quantization-symbol bytes only; legacy single-round prediction with frozen original references,not full-compressor RD","input_sha256":input_hashes}
    temporary=output/"report.json.tmp"
    with open(temporary,"w",encoding="utf-8") as output_file:
        json.dump(report,output_file,indent=2)
        output_file.write("\n")
    temporary.replace(output/"report.json")
    for row in summary:
        print(f"{row['criterion']}: agreement={row['agreement_percent']:.3f}%,mean_loss={row['mean_score_loss']:.9g},max_loss={row['max_score_loss']:.9g},N={row['non_tied_cases']},ground_ties={row['ground_tied_cases']}")
    print(f"wrote {output}")

if __name__=="__main__":
    main()
