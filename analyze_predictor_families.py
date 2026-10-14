import argparse,csv,hashlib,json,math,subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import kendalltau

project_root=Path(__file__).resolve().parent
data_root=Path("/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data")
datasets={
    "isabel":("Isabel Pf01",data_root/"ISABEL/P/Pf01.bin",(100,500,500)),
    "aramco":("Aramco 1800",data_root/"aramco/aramco-snapshot-1800.f32",(449,449,235)),
    "cldice":("CESM CLDICE t00",data_root/"cesm-atm-1.5TB/00/CLDICE_26x1800x3600.dat",(26,1800,3600)),
    "letkf":("LETKF PRES",data_root/"SCALE_LETKF/PRES-98x1200x1200.dat",(98,1200,1200)),
}
quintic_weights=(3/256,-25/256)


def read_csv(path):
    with path.open(newline="",encoding="utf-8") as source:
        return list(csv.DictReader(source))


def write_csv(path,rows):
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w",newline="",encoding="utf-8") as output:
        writer=csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_sweep(path):
    rows=read_csv(path)
    for row in rows:
        for key in row:
            if key not in ("family","orientation"):
                row[key]=float(row[key])
    return rows


def is_quintic(row):
    return row["family"]=="1D6R" and abs(row["a"]-quintic_weights[0])<1e-14 and abs(row["b"]-quintic_weights[1])<1e-14


def frontier(rows):
    best_by_rate={}
    for row in rows:
        if math.isfinite(row["PSNR"]) and row["BR"]>0:
            best_by_rate[row["BR"]]=max(row["PSNR"],best_by_rate.get(row["BR"],-math.inf))
    points=sorted(best_by_rate.items())
    result=[]
    best=-math.inf
    for bitrate,psnr in points:
        if psnr>best:
            result.append((bitrate,psnr))
            best=psnr
    return np.asarray(result,dtype=float).reshape(-1,2)


def matched_rate(curve,quality):
    if len(curve)<2 or quality<curve[0,1] or quality>curve[-1,1]:
        return None
    return float(np.exp(np.interp(quality,curve[:,1],np.log(curve[:,0]))))


def coefficient_curves(rows):
    groups={}
    for row in rows:
        key=(row["t"],row["a"],row["b"])
        groups.setdefault(key,[]).append(row)
    return [frontier(group) for group in groups.values() if len(frontier(group))>=2]


def best_rate(curves,quality):
    # 已达到更高质量的实际点也满足当前质量要求，不应因其没有更低质量点而排除。
    rates=[float(curve[0,0]) if quality<curve[0,1] else matched_rate(curve,quality) for curve in curves]
    return min((rate for rate in rates if rate is not None),default=None)


def coefficient_envelope(rows):
    curves=coefficient_curves(rows)
    if not curves:
        return np.empty((0,2))
    qualities=sorted({float(quality) for curve in curves for quality in curve[:,1]}|set(np.linspace(min(c[0,1] for c in curves),max(c[-1,1] for c in curves),401)))
    points=[(best_rate(curves,quality),quality) for quality in qualities]
    return frontier([{"BR":rate,"PSNR":quality} for rate,quality in points if rate is not None])


def setup_axis(axis,title):
    axis.set_title(title,fontsize=10)
    axis.set_xlabel("Bit rate (bits/value)")
    axis.set_ylabel("PSNR (dB)")
    axis.set_xscale("log")
    axis.grid(alpha=0.2)


def save_figure(figure,directory,name):
    figure.tight_layout()
    figure.savefig(directory/f"{name}.pdf",bbox_inches="tight")
    figure.savefig(directory/f"{name}.png",dpi=180,bbox_inches="tight")
    plt.close(figure)


def draw_family_comparison(sweeps,keys,families,directory,name):
    figure,axes=plt.subplots(1,3,figsize=(10.2,2.8))
    colors=("#2166ac","#b2182b")
    line_styles=("-","--",":")
    for axis,key in zip(axes,keys):
        rows=sweeps[key]
        for family,color in zip(families,colors):
            orientations=sorted({r["orientation"] for r in rows if r["family"]==family})
            for index,orientation in enumerate(orientations):
                curve=coefficient_envelope([r for r in rows if r["family"]==family and r["orientation"]==orientation])
                if len(curve):
                    axis.plot(curve[:,0],curve[:,1],color=color,linestyle=line_styles[index],linewidth=1.2,label=f"{family} {'plane' if family=='2D4R' else 'axis'} {orientation}")
        setup_axis(axis,datasets[key][0])
        axis.legend(fontsize=6,loc="best")
    save_figure(figure,directory,name)


def draw_fixed_comparison(sweeps,directory,summary_path):
    figure,axes=plt.subplots(1,3,figsize=(10.2,2.8))
    summary=[]
    for axis,key in zip(axes,("aramco","cldice","letkf")):
        rows=sweeps[key]
        fixed_rows=[r for r in rows if is_quintic(r)]
        orientation=min({r["orientation"] for r in fixed_rows},key=lambda direction:np.mean([r["PRED_MSE"] for r in fixed_rows if r["orientation"]==direction]))
        six_rows=[r for r in rows if r["family"]=="1D6R" and r["orientation"]==orientation]
        for a,b in sorted({(r["a"],r["b"]) for r in six_rows}):
            curve=frontier([r for r in six_rows if r["a"]==a and r["b"]==b])
            if len(curve):
                axis.plot(curve[:,0],curve[:,1],color="0.65",alpha=0.12,linewidth=0.5)
        tuned=coefficient_envelope(six_rows)
        fixed=frontier([r for r in six_rows if is_quintic(r)])
        four=coefficient_envelope([r for r in rows if r["family"]=="1D4R" and r["orientation"]==orientation])
        for curve,color,label in ((four,"#2166ac","Grid-tuned 1D4R"),(tuned,"black","Grid-tuned 1D6R"),(fixed,"#b2182b","Fixed quintic")):
            if len(curve):
                axis.plot(curve[:,0],curve[:,1],color=color,linewidth=1.6,label=label)
        setup_axis(axis,f"{datasets[key][0]} (axis {orientation})")
        axis.legend(fontsize=7,loc="best")
        quality_min=max(fixed[0,1],tuned[0,1])
        quality_max=min(fixed[-1,1],tuned[-1,1])
        gaps=[]
        curves=coefficient_curves(six_rows)
        if quality_max>quality_min:
            for quality in np.linspace(quality_min,quality_max,101):
                gaps.append(math.log(matched_rate(fixed,quality)/best_rate(curves,quality)))
        summary.append({"dataset":key,"orientation":orientation,"samples":int(rows[0]["SAMPLES"]),"quintic_outer_weight":quintic_weights[0],"quintic_middle_weight":quintic_weights[1],"fixed_vs_grid_bitrate_penalty_percent":100*math.expm1(float(np.mean(gaps))) if gaps else math.nan,"quality_min":quality_min,"quality_max":quality_max,"protocol":"frozen-original-reference sampled single-round prediction"})
    save_figure(figure,directory,"iv-fixed-quintic-pilot")
    write_csv(summary_path,summary)


def summarize_mse(sweeps,directory):
    summary=[]
    for key,rows in sweeps.items():
        for orientation in ("0","1","2"):
            candidates=[r for r in rows if r["family"]=="1D6R" and r["orientation"]==orientation]
            best=min(candidates,key=lambda row:row["PRED_MSE"])
            fixed=next(r for r in candidates if is_quintic(r))
            summary.append({"dataset":key,"orientation":orientation,"best_a":best["a"],"best_b":best["b"],"best_t1":best["t1"],"best_t2":best["t2"],"best_mse":best["PRED_MSE"],"quintic_mse":fixed["PRED_MSE"],"quintic_vs_best_mse_ratio":fixed["PRED_MSE"]/best["PRED_MSE"] if best["PRED_MSE"] else math.nan})
    write_csv(directory/"quintic-mse-summary.csv",summary)


def historical_selector_validation(directory):
    outcomes=[]
    summary=[]
    for path in sorted((project_root/"results").glob("predictor_family_rd_extremes_*.csv")):
        raw=read_csv(path)
        by_method={method:sorted((float(r["BR"]),float(r["PSNR"])) for r in raw if r["METHOD"]==method) for method in ("asz_threshold_0","asz_threshold_1e6")}
        if not all(len(points)>=2 for points in by_method.values()):
            continue
        curves=[frontier([{"BR":br,"PSNR":psnr} for br,psnr in by_method[method]]) for method in by_method]
        field_outcomes=[]
        for row in raw:
            if row["METHOD"]!="asz_threshold_0":
                continue
            companion=next(r for r in raw if r["METHOD"]=="asz_threshold_1e6" and float(r["REL_EB"])==float(row["REL_EB"]))
            quality=(float(row["PSNR"])+float(companion["PSNR"]))/2
            rates=[matched_rate(curve,quality) for curve in curves]
            if any(rate is None for rate in rates):
                continue
            mse_cubic,mse_quintic=float(row["CUBIC_MSE"]),float(row["QUINTIC_MSE"])
            mse_ratio=mse_quintic/mse_cubic if mse_cubic else math.nan
            selected=int(mse_quintic<mse_cubic)
            preferred=int(rates[1]<rates[0])
            tau=float(kendalltau([-mse_cubic,-mse_quintic],[-math.log(rates[0]),-math.log(rates[1])]).statistic)
            outcome={"dataset":path.stem.removeprefix("predictor_family_rd_extremes_"),"rel_eb":float(row["REL_EB"]),"matched_psnr":quality,"cubic_br":rates[0],"quintic_br":rates[1],"mse_ratio":mse_ratio,"mse_choice_unpenalized":"quintic" if selected else "cubic","rd_choice":"quintic" if preferred else "cubic","correct":int(selected==preferred),"pair_tau":tau,"regret_percent":100*(rates[selected]/min(rates)-1),"scope":"historical matched-PSNR audit; raw MSE without runtime preference margin; shared plans/settings unverified"}
            outcomes.append(outcome)
            field_outcomes.append(outcome)
        if field_outcomes:
            valid_tau=[r["pair_tau"] for r in field_outcomes if math.isfinite(r["pair_tau"])]
            summary.append({"dataset":field_outcomes[0]["dataset"],"total_error_bound_cases":len(raw)//2,"cases":len(field_outcomes),"excluded_outside_common_quality":len(raw)//2-len(field_outcomes),"valid_tau_cases":len(valid_tau),"mse_ties":sum(r["mse_ratio"]==1 for r in field_outcomes),"accuracy":np.mean([r["correct"] for r in field_outcomes]),"mean_within_case_tau":np.mean(valid_tau) if valid_tau else math.nan,"mean_regret_percent":np.mean([r["regret_percent"] for r in field_outcomes]),"max_regret_percent":max(r["regret_percent"] for r in field_outcomes)})
    write_csv(directory/"historical-selector-cases.csv",outcomes)
    write_csv(directory/"historical-selector-summary.csv",summary)
    print("Historical selector:",json.dumps(summary,ensure_ascii=False),flush=True)


def self_test():
    curve=frontier([{"BR":1,"PSNR":10},{"BR":2,"PSNR":20},{"BR":3,"PSNR":19}])
    assert len(curve)==2
    duplicate=frontier([{"BR":1,"PSNR":10},{"BR":1,"PSNR":20}])
    assert len(duplicate)==1 and duplicate[0,1]==20
    assert math.isclose(matched_rate(curve,15),math.sqrt(2))
    assert matched_rate(curve,21) is None
    assert kendalltau([1,2],[3,4]).statistic==1
    assert kendalltau([1,2],[4,3]).statistic==-1
    rows=[{"BR":1,"PSNR":10,"t":0,"a":0,"b":0},{"BR":4,"PSNR":20,"t":0,"a":0,"b":0},{"BR":2.9,"PSNR":19,"t":1,"a":0,"b":0},{"BR":5,"PSNR":21,"t":1,"a":0,"b":0}]
    assert best_rate(coefficient_curves(rows),19)<=matched_rate(frontier(rows[:2]),19)
    print("PASS: Pareto frontier, common-quality interpolation, and within-case tau")


def cli():
    parser=argparse.ArgumentParser(description="Controlled predictor-family pilot and historical selector audit")
    parser.add_argument("--executable",type=Path)
    parser.add_argument("--output",type=Path,default=project_root/"results/predictor-family-paper-pilot")
    parser.add_argument("--figures",type=Path,default=project_root/"新论文/revised-fig/predictor-family-pilot")
    parser.add_argument("--blocks",type=int,default=64)
    parser.add_argument("--edge",type=int,default=8)
    parser.add_argument("--skip-run",action="store_true")
    parser.add_argument("--self-test",action="store_true")
    arguments=parser.parse_args()
    if arguments.self_test:
        self_test()
        return
    arguments.output.mkdir(parents=True,exist_ok=True)
    arguments.figures.mkdir(parents=True,exist_ok=True)
    sweeps={}
    provenance={"protocol":"controlled sampled single-round prediction, frozen original references, common targets and fixed row-major symbol serialization; not full-compressor RD","sampling_seed":20261010,"blocks":arguments.blocks,"edge":arguments.edge,"error_bound_grid":"10^(-1-k/4), k=0,...,16","quantization":"round(residual/(2*absolute_eb))","lossless":"repository Huffman + repository Zstd level 3","one_d_four_t_grid":"0:1/32:3/8","two_d_four_t_grid":"-3/8:1/32:3/8","one_d_six_ab_grid":"a=-1/16:1/64:1/16; b=-1/4:1/32:1/4; plus exact quintic and dense neighborhood; contains every 1D4R grid candidate","quintic_a":quintic_weights[0],"quintic_b":quintic_weights[1],"source_sha256":hashlib.sha256((project_root/"c_codes/s9_predictor_family_sweep.cpp").read_bytes()).hexdigest(),"datasets":{}}
    for key,(title,path,shape) in datasets.items():
        output_path=arguments.output/f"{key}.csv"
        if not arguments.skip_run:
            if not arguments.executable:
                parser.error("--executable is required unless --skip-run is specified")
            subprocess.run([str(arguments.executable),str(path),*(str(n) for n in shape),str(output_path),str(arguments.blocks),str(arguments.edge)],check=True)
        sweeps[key]=load_sweep(output_path)
        stat=path.stat()
        provenance["datasets"][key]={"path":str(path),"shape":shape,"size":stat.st_size,"mtime_ns":stat.st_mtime_ns,"samples":int(sweeps[key][0]["SAMPLES"])}
    provenance["analysis_source_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    provenance["rate_distortion_envelope"]="minimum rate across per-coefficient log-BR interpolants satisfying the requested PSNR or better, with dominated points removed"
    (arguments.output/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n",encoding="utf-8")
    draw_family_comparison(sweeps,("isabel","cldice","aramco"),("1D4R","2D4R"),arguments.figures,"iv-1d4r-vs-2d4r-pilot")
    draw_family_comparison(sweeps,("isabel","aramco","letkf"),("1D4R","1D6R"),arguments.figures,"iv-1d4r-vs-1d6r-pilot")
    draw_fixed_comparison(sweeps,arguments.figures,arguments.output/"fixed-quintic-summary.csv")
    summarize_mse(sweeps,arguments.output)
    historical_selector_validation(arguments.output)
    print("Figures:",arguments.figures)
    print("Fixed quintic:",json.dumps(read_csv(arguments.output/"fixed-quintic-summary.csv"),ensure_ascii=False))


if __name__=="__main__":
    cli()
