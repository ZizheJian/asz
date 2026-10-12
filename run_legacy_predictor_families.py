import argparse,csv,hashlib,json,re,subprocess
from concurrent.futures import ThreadPoolExecutor,as_completed
from fractions import Fraction
from pathlib import Path

import numpy as np
from rd_plot_layout import layout_rd_panels

project_root=Path(__file__).resolve().parent
data_root=Path("/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data")
datasets={
    "isabel":("Isabel Pf24",data_root/"ISABEL/P/Pf24.bin",(100,500,500)),
    "cldice":("CESM CLDICE t31",data_root/"cesm-atm-1.5TB/31/CLDICE_26x1800x3600.dat",(26,1800,3600)),
    "cesmt":("CESM T t31",data_root/"cesm-atm-1.5TB/31/T_26x1800x3600.dat",(26,1800,3600)),
    "aramco":("Aramco 1800",data_root/"aramco/aramco-snapshot-1800.f32",(449,449,235)),
    "letkf":("LETKF PRES",data_root/"SCALE_LETKF/PRES-98x1200x1200.dat",(98,1200,1200)),
    "letkf_qv":("LETKF QV (log10)",data_root/"SCALE_LETKF/log10/QV-98x1200x1200.log10.f32",(98,1200,1200)),
    "qmcpack":("QMCPACK orbital 0",data_root/"QMCPACK/asz_qmcpack_orbital0.f32",(115,69,69)),
}
default_datasets=("isabel","cldice","aramco")
families=("1d4r","2d4r")
bounds="0.1,0.01,0.001,0.0001,0.00001"


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def six_grid_metadata(mode):
    if mode=="transition":
        equal=(Fraction(0),Fraction(0))
        quintic=(Fraction(119,768),Fraction(203,768))
        four=[(Fraction(1,6),Fraction(k,32)-Fraction(1,12)) for k in range(13)]
        pairs=[(equal,quintic),*((equal,point) for point in four),*((quintic,point) for point in four)]
        candidates=[equal,quintic,*four,*(tuple((a+b)/2 for a,b in zip(left,right)) for left,right in pairs)]
        return {"mode":mode,"candidate_count":len(candidates),"definition":"six-point equal weights, exact quintic, all 13 embedded 1D4R candidates, and midpoints between different anchor categories","parameters":[[str(value) for value in point] for point in candidates]}
    return {"legacy_t1_numerators":[0,11,22,31,41],"legacy_t1_denominator":186,"legacy_t2_numerators":[0,113,248,341,453,567,680,793],"legacy_t2_denominator":1488,"mode":mode,"candidate_count":52 if mode=="augmented" else 40,"additional_candidates":"exact quintic (119/768,203/768) and embedded 1D4R (1/6,t-1/12); approximate duplicates replaced by exact values" if mode=="augmented" else None}


def metadata(selected_families=families,six_grid="legacy",targets="legacy",selected_datasets=default_datasets):
    return {
        "protocol":"legacy single-round prediction with frozen original references, exhaustive coefficients and three serialization orders, two-stage tangent scoring; not full-compressor RD",
        "error_bounds":bounds,
        "stride":1,
        "families":selected_families,
        "coefficient_grids":{"1d4r":"0:1/32:12/32","2d4r":"-6/24:1/24:6/24","1d6r":six_grid_metadata(six_grid)},
        "traversal_orders":["xx0","xx1","xx2"],
        "equal_rate_coefficient_fallback":"When neighboring coefficient-averaged points have zero bitrate span and all current coefficient candidates have equal bitrate, rank by PSNR and explicitly report an undefined slope. Other zero-span cases are rejected.",
        "equal_rate_traversal_fallback":"When neighboring selected averages have zero bitrate span and all current traversal candidates have equal bitrate, rank by PSNR and explicitly report an undefined slope. Other zero-span cases are rejected.",
        "rate":"Huffman plus Zstd level 3 quantization-symbol bytes only",
        "target_mode":targets,
        "target_sets":"shared 1D4R/1D6R targets per axis: odd coordinates starting at 5 and ending before dimension-5; all transverse coordinates retained; identical across serialization orders" if targets=="shared1d" else "legacy stencil-specific target sets; identical across traversal orders of a given stencil at stride=1",
        "datasets":{key:{"label":datasets[key][0],"path":str(datasets[key][1]),"shape":datasets[key][2],"bytes":datasets[key][1].stat().st_size,"mtime_ns":datasets[key][1].stat().st_mtime_ns} for key in selected_datasets},
        "source_hashes":{name:file_hash(project_root/name) for name in ("c_codes/s2_many_prediction.cpp","c_codes/s3_conclude_sp_result.cpp","run_legacy_predictor_families.py")},
    }


def call_logged(command,path):
    with path.open("w") as output:
        subprocess.run([str(value) for value in command],stdout=output,stderr=subprocess.STDOUT,check=True)


def timed_run_seconds(path):
    match=re.search(r"total_seconds=([0-9.]+)",path.read_text())
    if match is None:
        raise ValueError(f"missing internal timing in {path}")
    return float(match[1])


def raw_paths(prefix,family):
    suffixes=("01","02","12") if family=="2d4r" else ("0","1","2")
    return [prefix.parent/f"{prefix.name}_{family}{suffix}_{order}.csv" for suffix in suffixes for order in ("xx0","xx1","xx2")]


def read_bound_rows(path,family,wanted):
    parameters=("t1",)
    grid={round(k/32,12) for k in range(13)} if family=="1d4r" else {round(float(np.float32(k)/np.float32(24)),12) for k in range(-6,7)}
    with path.open(newline="") as source:
        reader=csv.DictReader(source)
        header=reader.fieldnames
        if header is None or not {"rel_eb",*parameters,"BR","PSNR","SAMPLES"}.issubset(header):
            raise ValueError(f"invalid raw CSV header: {path}")
        rows=[row for row in reader if float(row["rel_eb"]) in wanted]
    records={(float(row["rel_eb"]),round(float(row["t1"]),12)) for row in rows}
    expected={(bound,parameter) for bound in wanted for parameter in grid}
    if len(records)!=len(rows) or records!=expected:
        raise ValueError(f"incomplete or duplicate coefficient grid: {path}")
    return header,rows


def reuse_plan(source,provenance,selected_families,selected_datasets):
    # 仅复用旧4R实验；新6R网格和共享目标实验必须重新测量。
    if provenance["target_mode"]!="legacy" or set(selected_families)!={"1d4r","2d4r"}:
        raise ValueError("reuse requires legacy 1d4r/2d4r target sets")
    previous_path=source/"provenance.json"
    previous=json.loads(previous_path.read_text())
    for key in ("protocol","stride","traversal_orders","rate","target_sets"):
        if previous.get(key)!=provenance[key]:
            raise ValueError(f"reuse protocol mismatch: {key}")
    for family in selected_families:
        if previous["coefficient_grids"].get(family)!=provenance["coefficient_grids"][family]:
            raise ValueError(f"reuse coefficient grid mismatch: {family}")
    desired={float(value) for value in bounds.split(",")}
    available={float(value) for value in previous["error_bounds"].split(",")}
    reused=desired&available
    missing=desired-available
    if not reused:
        raise ValueError("no matching bounds to reuse")
    hashes={}
    for key in selected_datasets:
        old=previous["datasets"].get(key)
        current=json.loads(json.dumps(provenance["datasets"][key]))
        if old!=current:
            raise ValueError(f"reuse dataset mismatch: {key}")
        for family in selected_families:
            for path in raw_paths(source/key,family):
                read_bound_rows(path,family,reused)
                hashes[path.name]=file_hash(path)
    return {"directory":str(source.resolve()),"provenance_sha256":file_hash(previous_path),"raw_sha256":hashes,"reused_bounds":sorted(reused,reverse=True),"computed_bounds":sorted(missing,reverse=True),"note":"Reuse raw legacy 4R measurements only; rerun coefficient/order selection across the complete new range. Source and binary hashes for both runs remain recorded separately."}


def merge_bound_sweeps(source_prefix,supplement_prefix,destination_prefix,family,plan):
    reused=set(plan["reused_bounds"])
    computed=set(plan["computed_bounds"])
    sources=raw_paths(source_prefix,family)
    supplements=raw_paths(supplement_prefix,family)
    destinations=raw_paths(destination_prefix,family)
    for source,supplement,destination in zip(sources,supplements,destinations):
        if file_hash(source)!=plan["raw_sha256"][source.name]:
            raise ValueError(f"reuse source changed after validation: {source}")
        header,rows=read_bound_rows(source,family,reused)
        if computed:
            other_header,other_rows=read_bound_rows(supplement,family,computed)
            if other_header!=header:
                raise ValueError(f"supplement CSV header mismatch: {supplement}")
            rows.extend(other_rows)
        with destination.open("x",newline="") as output:
            writer=csv.DictWriter(output,fieldnames=header)
            writer.writeheader()
            writer.writerows(sorted(rows,key=lambda row:(float(row["rel_eb"]),float(row["t1"])),reverse=True))


def benchmark(arguments):
    output=arguments.output
    output.mkdir(parents=True,exist_ok=False)
    measurements=[]
    for key in arguments.datasets:
        _,path,shape=datasets[key]
        original=np.memmap(path,dtype=np.float32,mode="r",shape=shape)
        small_shape=tuple(min(size,64) for size in shape)
        coordinates=[np.linspace(0,size-1,small,dtype=int) for size,small in zip(shape,small_shape)]
        # 仅用于计时：均匀取样产生小型输入，不把该数据的RD结果当作实验结论。
        small=np.asarray(original[np.ix_(*coordinates)],dtype=np.float32)
        small_path=output/f"{key}-timing.f32"
        small.tofile(small_path)
        for family in arguments.families:
            prefix=output/f"{key}-{family}"
            log=output/f"{key}-{family}.log"
            call_logged([arguments.sweep,small_path,*small_shape,prefix,family,"0.001,0.00001",arguments.six_grid,arguments.targets],log)
            seconds=timed_run_seconds(log)
            ratio=np.prod(shape)/np.prod(small_shape)
            estimate=seconds*ratio*len(bounds.split(","))/2
            measurements.append({"dataset":key,"family":family,"timing_shape":small_shape,"internally_measured_seconds":seconds,"bound_count":len(bounds.split(",")),"volume_scaled_seconds":float(estimate)})
            print(json.dumps(measurements[-1]),flush=True)
    (output/"timing.json").write_text(json.dumps({"note":"small spatially downsampled inputs for runtime estimation only; full runs retain original grids and target sets","measurements":measurements},indent=2)+"\n")


def run(arguments):
    output=arguments.output
    provenance=metadata(arguments.families,arguments.six_grid,arguments.targets,arguments.datasets)
    reuse=getattr(arguments,"reuse_output",None)
    plan=reuse_plan(reuse,provenance,arguments.families,arguments.datasets) if reuse is not None else None
    output.mkdir(parents=True,exist_ok=False)
    (output/"logs").mkdir()
    if plan is not None:
        (output/"supplement").mkdir()
        provenance["reuse"]=plan
    provenance["binary_hashes"]={"sweep":file_hash(arguments.sweep),"conclude":file_hash(arguments.conclude)}
    (output/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")

    def task(key,family):
        _,path,shape=datasets[key]
        prefix=output/key
        log=output/"logs"/f"{key}-{family}.log"
        print(f"START {key} {family}",flush=True)
        fresh_bounds=bounds if plan is None else ",".join(str(value) for value in plan["computed_bounds"])
        sweep_prefix=prefix if plan is None else output/"supplement"/key
        seconds=0.0
        if fresh_bounds:
            call_logged([arguments.sweep,path,*shape,sweep_prefix,family,fresh_bounds,arguments.six_grid,arguments.targets],log)
            seconds=timed_run_seconds(log)
        if plan is not None:
            merge_bound_sweeps(reuse/key,sweep_prefix,prefix,family,plan)
        summary=output/f"{key}-{family}-best.csv"
        call_logged([arguments.conclude,prefix,family,summary],output/"logs"/f"{key}-{family}-selection.log")
        print(f"DONE {key} {family} internal_seconds={seconds}",flush=True)
        return {"dataset":key,"family":family,"internally_measured_seconds":seconds,"timing_scope":"freshly computed bounds only" if plan is not None else "full sweep","summary":str(summary)}

    with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
        futures=[executor.submit(task,key,family) for key in arguments.datasets for family in arguments.families]
        completed=[future.result() for future in as_completed(futures)]
    (output/"completed.json").write_text(json.dumps(completed,indent=2)+"\n")
    plot(output,arguments.families,arguments.datasets)


def plot(output,selected_families=families,selected_datasets=None,figure_directory=None,additional_outputs=(),allow_missing=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import LogLocator,MaxNLocator,NullLocator

    if selected_datasets is None:
        provenance=output/"provenance.json"
        selected_datasets=tuple(json.loads(provenance.read_text())["datasets"]) if provenance.exists() else default_datasets
    # 按最终单栏宽度直接绘制，导出时不裁剪画布，避免论文缩放后字号变小。
    plt.rcParams.update({"font.family":"serif","font.serif":["STIXGeneral"],"mathtext.fontset":"stix","font.size":8,"axes.labelsize":8,"axes.titlesize":8,"xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":8,"pdf.fonttype":42,"ps.fonttype":42})
    if not selected_datasets:
        raise ValueError("at least one dataset is required")
    columns=min(3,len(selected_datasets))
    rows_count=(len(selected_datasets)+columns-1)//columns
    figure,axes=plt.subplots(rows_count,columns,figsize=(3.5,1.65*rows_count),sharey=True,squeeze=False)
    figure.subplots_adjust(left=0.12,right=0.98,bottom=0.31/rows_count,top=0.81,wspace=0.16,hspace=0.5)
    panel_axes=list(axes.flat)[:len(selected_datasets)]
    for axis in list(axes.flat)[len(selected_datasets):]:
        axis.set_visible(False)
    for panel,(axis,key) in enumerate(zip(panel_axes,selected_datasets)):
        summaries={}
        for family in selected_families:
            paths=[directory/f"{key}-{family}-best.csv" for directory in (output,*additional_outputs) if (directory/f"{key}-{family}-best.csv").is_file()]
            if len(paths)>1:
                raise ValueError(f"ambiguous summary sources for {key} {family}")
            if paths:
                with paths[0].open(newline="") as source:
                    reader=csv.DictReader(source)
                    rows=list(reader)
                    stencils=[family+suffix for suffix in (("01","02","12") if family=="2d4r" else ("0","1","2"))]
                    required={"rel_eb",*(stencil+"_"+metric for stencil in stencils for metric in ("BR","PSNR"))}
                    if reader.fieldnames is None or not required.issubset(reader.fieldnames) or len(rows)<2:
                        continue
                bounds=[float(row["rel_eb"]) for row in rows]
                provenance=paths[0].parent/"provenance.json"
                if len(set(bounds))!=len(bounds):
                    raise ValueError(f"duplicate error bounds in {paths[0]}")
                if provenance.exists() and set(bounds)!={float(value) for value in json.loads(provenance.read_text())["error_bounds"].split(",")}:
                    continue
                if any(row.get(name) in (None,"") for row in rows for name in required):
                    continue
                summaries[family]=rows
        pending=len(summaries)!=len(selected_families) or len({tuple(sorted(float(row["rel_eb"]) for row in rows)) for rows in summaries.values()})!=1
        if pending and not allow_missing:
            raise FileNotFoundError(f"missing complete predictor-family summaries for {key}")
        for family,color in zip(selected_families,("#2166ac","#b2182b")):
            if pending:
                continue
            rows=summaries[family]
            stencils=[family+suffix for suffix in (("01","02","12") if family=="2d4r" else ("0","1","2"))]
            directions=("xy","xz","yz") if family=="2d4r" else ("x","y","z")
            # 三个方向均用非实线，保持相同线宽和60%的着墨比例，不用重叠的点形区分方向。
            styles=((0,(3,2)),(0,(1.5,1)),(0,(3,1.5,0.75,1)))
            for stencil,style,direction in zip(stencils,styles,directions):
                # 蓝线错开半个虚线周期，让重合的红蓝曲线均可见；只改相位，不偏移RD坐标。
                style=(sum(style[1])/2 if family==selected_families[0] else 0,style[1])
                points=sorted((float(row[stencil+"_BR"]),float(row[stencil+"_PSNR"])) for row in rows)
                if not all(np.isfinite(rate) and rate>0 and np.isfinite(quality) for rate,quality in points):
                    raise ValueError(f"invalid selected RD point for {key} {stencil}")
                axis.plot(*zip(*points),color=color,linestyle=style,marker="None",linewidth=0.8,dash_capstyle="butt",label=f"{family.upper()} {direction}")
        axis.set_xscale("log")
        axis.xaxis.set_major_locator(LogLocator(base=10,numticks=3))
        axis.xaxis.set_minor_locator(NullLocator())
        axis.yaxis.set_major_locator(MaxNLocator(nbins=4))
        axis.tick_params(direction="in",length=1.8,width=0.45,pad=1)
        for spine in axis.spines.values():
            spine.set_linewidth(0.5)
        axis.grid(alpha=0.2,linewidth=0.3)
        if pending:
            axis.set_xticks([])
            axis.text(0.5,0.5,"Pending\nmeasurement",transform=axis.transAxes,ha="center",va="center",fontsize=8,color="0.45",gid=f"pending-{key}")
    measured_axes=[axis for axis in panel_axes if axis.lines]
    if not measured_axes:
        raise ValueError("at least one completed dataset is required for a comparison plot")
    handles,labels=measured_axes[0].get_legend_handles_labels()
    order=(0,3,1,4,2,5)
    legend=figure.legend([handles[index] for index in order],[labels[index] for index in order],loc="upper center",bbox_to_anchor=(0.5575,1-2/72/figure.get_size_inches()[1]),ncol=3,frameon=False,handlelength=1.3,handletextpad=0.35,columnspacing=0.8,labelspacing=0.12,borderaxespad=0,borderpad=0)
    names={"isabel":"Isabel","cldice":"CLDICE","cesmt":"CESM T","aramco":"Aramco","letkf":"LETKF PRES","letkf_qv":"LETKF QV","qmcpack":"QMCPACK"}
    labels=[f"({chr(97+index)}) {names[key]}" for index,key in enumerate(selected_datasets)]
    layout_rd_panels(figure,panel_axes,legend,labels,columns)
    figure_directory=output if figure_directory is None else figure_directory
    figure_directory.mkdir(parents=True,exist_ok=True)
    for extension in ("pdf","png"):
        figure.savefig(figure_directory/f"iv-{'-vs-'.join(selected_families)}-legacy-middle.{extension}",dpi=400)
    plt.close(figure)
    return figure


def cli():
    parser=argparse.ArgumentParser(description="Run the legacy predictor-family experiment on middle time steps")
    parser.add_argument("mode",choices=("benchmark","run","plot"))
    parser.add_argument("--sweep",type=Path)
    parser.add_argument("--conclude",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--workers",type=int,default=6)
    parser.add_argument("--families",nargs=2,choices=("1d4r","2d4r","1d6r"),default=list(families))
    parser.add_argument("--six-grid",choices=("legacy","augmented","transition"),default="legacy")
    parser.add_argument("--targets",choices=("legacy","shared1d"),default="legacy")
    parser.add_argument("--datasets",nargs="+",choices=tuple(datasets))
    parser.add_argument("--reuse-output",type=Path,help="Reuse compatible raw legacy 1d4r/2d4r measurements and compute only missing bounds")
    parser.add_argument("--figure-directory",type=Path,help="Write redrawn figures separately without changing experiment outputs")
    parser.add_argument("--additional-output",type=Path,nargs="+",default=[],help="Additional summary directories for plot mode")
    parser.add_argument("--allow-missing",action="store_true",help="Show explicitly labeled placeholders for datasets without both summaries in plot mode")
    arguments=parser.parse_args()
    if arguments.workers<1:
        parser.error("workers must be positive")
    if len(set(arguments.families))!=2:
        parser.error("choose two distinct predictor families")
    if arguments.targets=="shared1d" and set(arguments.families)!={"1d4r","1d6r"}:
        parser.error("shared1d requires the 1d4r and 1d6r families")
    if arguments.datasets is not None and len(set(arguments.datasets))!=len(arguments.datasets):
        parser.error("dataset names must be distinct")
    if arguments.mode!="plot" and arguments.datasets is None:
        arguments.datasets=default_datasets
    if arguments.mode!="plot" and arguments.sweep is None:
        parser.error("--sweep is required")
    if arguments.mode=="run" and arguments.conclude is None:
        parser.error("--conclude is required")
    if arguments.reuse_output is not None and arguments.mode!="run":
        parser.error("--reuse-output requires run mode")
    if arguments.figure_directory is not None and arguments.mode!="plot":
        parser.error("--figure-directory requires plot mode")
    if (arguments.additional_output or arguments.allow_missing) and arguments.mode!="plot":
        parser.error("--additional-output and --allow-missing require plot mode")
    if arguments.mode=="benchmark":
        benchmark(arguments)
    elif arguments.mode=="run":
        run(arguments)
    else:
        plot(arguments.output,arguments.families,arguments.datasets,arguments.figure_directory,arguments.additional_output,arguments.allow_missing)


if __name__=="__main__":
    cli()
