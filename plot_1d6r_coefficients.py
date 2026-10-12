import argparse,csv,json,math
from pathlib import Path

from analyze_1d6r_coefficients import file_hash,parameter_key
from rd_plot_layout import layout_rd_panels


other_style={"color":"0.72","linewidth":0.45,"linestyle":"-"}
styles={kind:dict(other_style) for kind in ("equal_weight","embedded_1d4r","transition")}
styles["quintic"]={"color":"#b2182b","linewidth":1.1,"linestyle":"-"}


def load_selected(directory,keys=None):
    paths=(directory/"selected.csv",directory/"report.json")
    hashes={str(path.resolve()):file_hash(path) for path in paths}
    report=json.loads(paths[1].read_text())
    keys=list(report["datasets"]) if keys is None else list(keys)
    if not keys or len(set(keys))!=len(keys):
        raise ValueError("dataset names must be nonempty and distinct")
    with paths[0].open(newline="") as source:
        reader=csv.DictReader(source)
        required={"dataset","rel_eb","t1","t2","BR","PSNR","score","axis","qb_order","coefficient_kind"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("missing required columns in selected.csv")
        raw=list(reader)
    datasets={}
    for key in keys:
        if key not in report["datasets"]:
            raise ValueError(f"dataset {key} is absent from the analysis report")
        definition=report["datasets"][key]
        bounds=sorted(definition["error_bounds"],reverse=True)
        if len(bounds)<2 or len(bounds)!=len(set(bounds)) or any(not math.isfinite(value) or value<=0 for value in bounds):
            raise ValueError(f"invalid error-bound grid for {key}")
        curves={}
        for item in raw:
            if item["dataset"]!=key:
                continue
            row={**item,**{name:float(item[name]) for name in ("rel_eb","t1","t2","BR","PSNR","score")}}
            if any(not math.isfinite(row[name]) for name in ("rel_eb","t1","t2","BR","PSNR","score")) or row["BR"]<=0 or row["coefficient_kind"] not in styles or row["axis"] not in ("x","y","z") or row["qb_order"] not in ("xx0","xx1","xx2"):
                raise ValueError(f"invalid selected observation for {key}")
            parameter=parameter_key((row["t1"],row["t2"]))
            curve=curves.setdefault(parameter,{})
            if row["rel_eb"] in curve:
                raise ValueError(f"duplicate coefficient/error-bound observation for {key}")
            curve[row["rel_eb"]]=row
        if len(curves)!=definition["coefficient_count"] or any(set(curve)!=set(bounds) for curve in curves.values()):
            raise ValueError(f"incomplete coefficient/error-bound curves for {key}")
        if parameter_key((119/768,203/768)) not in curves:
            raise ValueError(f"missing exact quintic coefficient pair for {key}")
        if any(len({row["coefficient_kind"] for row in curve.values()})!=1 for curve in curves.values()):
            raise ValueError(f"coefficient category changes within a curve for {key}")
        datasets[key]={"label":definition["dataset"]["label"],"bounds":bounds,"curves":curves}
    if any(file_hash(Path(path))!=digest for path,digest in hashes.items()):
        raise ValueError("analysis inputs changed while reading")
    return datasets,report,hashes


def render(datasets,zoom=False,width=3.5,placeholder=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import LogFormatterSciNotation,LogLocator,MaxNLocator,NullLocator

    height=2.05 if width==3.5 else 2.8
    # 使用具名字体，避免figure离开rc_context后在savefig阶段将泛型serif重新解析为DejaVu Serif。
    with plt.rc_context({"font.family":"STIXGeneral","mathtext.fontset":"stix","font.size":8,"axes.labelsize":8,"xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":8,"pdf.fonttype":42,"ps.fonttype":42}):
        figure,axes=plt.subplots(1,len(datasets)+int(placeholder),figsize=(width,height),squeeze=False)
        figure.subplots_adjust(left=0.12,right=0.99,bottom=0.29,top=0.75,wspace=0.3)
        for index,(axis,(key,dataset)) in enumerate(zip(axes.flat,datasets.items())):
            bounds,curves=dataset["bounds"],dataset["curves"]
            for kind in ("equal_weight","embedded_1d4r","transition","quintic"):
                for parameter,curve in sorted(curves.items()):
                    points=[curve[bound] for bound in bounds]
                    if points[0]["coefficient_kind"]!=kind:
                        continue
                    line,=axis.plot([row["BR"] for row in points],[row["PSNR"] for row in points],marker="None",zorder=4 if kind=="quintic" else 1,**styles[kind])
                    line.set_gid(f"coefficient-{key}-{parameter[0]}-{parameter[1]}")
            best=[max((curve[bound] for curve in curves.values()),key=lambda row:(row["score"],row["PSNR"],-row["BR"])) for bound in bounds]
            line,=axis.plot([row["BR"] for row in best],[row["PSNR"] for row in best],color="0.1",linewidth=0.85,linestyle=(0,(2.5,2.5)),dash_capstyle="butt",zorder=5)
            line.set_gid(f"best-per-bound-{key}")
            if zoom:
                quintic=curves[parameter_key((119/768,203/768))]
                focus=[row for bound in bounds[-2:] for row in (quintic[bound],best[bounds.index(bound)])]
                rates=[row["BR"] for row in focus]
                qualities=[row["PSNR"] for row in focus]
                low,high=math.log10(min(rates)),math.log10(max(rates))
                padding=max(0.15,(high-low)*0.12)
                axis.set_xlim(10**(low-padding),10**(high+padding))
                padding=max(0.8,(max(qualities)-min(qualities))*0.12)
                axis.set_ylim(min(qualities)-padding,max(qualities)+padding)
            axis.set_xscale("log")
            axis.xaxis.set_major_locator(LogLocator(base=10,numticks=3))
            if not any(axis.get_xlim()[0]<=value<=axis.get_xlim()[1] for value in axis.get_xticks()):
                axis.xaxis.set_major_locator(LogLocator(base=10,subs=(1,2,5),numticks=6))
                axis.xaxis.set_major_formatter(LogFormatterSciNotation(labelOnlyBase=False,minor_thresholds=(math.inf,math.inf)))
                if not any(axis.get_xlim()[0]<=value<=axis.get_xlim()[1] for value in axis.get_xticks()):
                    midpoint=math.sqrt(math.prod(axis.get_xlim()))
                    axis.set_xticks([midpoint],labels=[f"{midpoint:.2g}"])
            axis.xaxis.set_minor_locator(NullLocator())
            axis.yaxis.set_major_locator(MaxNLocator(nbins=4))
            axis.tick_params(direction="in",length=2,width=0.45,pad=1)
            axis.grid(alpha=0.2,linewidth=0.3)
            for spine in axis.spines.values():
                spine.set_linewidth(0.5)
        if placeholder:
            axis=axes[0,-1]
            axis.set_xticks([])
            axis.set_yticks([])
            axis.text(0.5,0.5,"Pending\ndataset",transform=axis.transAxes,ha="center",va="center",color="0.5",fontsize=8,gid="pending-dataset")
            for spine in axis.spines.values():
                spine.set_linewidth(0.5)
        handles=[Line2D([],[],label="Fixed quintic",**styles["quintic"]),Line2D([],[],label="Best per error bound",color="0.1",linewidth=0.85,linestyle=(0,(2.5,2.5))),Line2D([],[],label="Other coefficients",**other_style)]
        legend=figure.legend(handles=handles,loc="upper center",bbox_to_anchor=(0.5,0.99),ncol=3,frameon=False,handlelength=1,handletextpad=0.3,columnspacing=0.4,labelspacing=0.1,borderaxespad=0,borderpad=0)
        labels=[f"({chr(97+index)}) {'QMCPACK' if key=='qmcpack' else dataset['label']}" for index,(key,dataset) in enumerate(datasets.items())]
        if placeholder:
            labels.append(f"({chr(97+len(datasets))}) Dataset C")
        layout_rd_panels(figure,list(axes.flat),legend,labels,len(axes.flat),legend_x=0.5,label_x=0.555)
    return figure


def plot(directory,output,keys=None,paper_placeholder=False):
    import matplotlib.pyplot as plt

    datasets,report,hashes=load_selected(directory,keys)
    output.mkdir(parents=True,exist_ok=True)
    products=[]
    dimensions={}
    variants=[(False,"",False),(True,"-detail",False)]
    if paper_placeholder:
        variants.append((False,"-paper",True))
    for zoom,suffix,placeholder in variants:
        figure=render(datasets,zoom,placeholder=placeholder)
        dimensions[suffix or "main"]=[float(value) for value in figure.get_size_inches()]
        for extension in ("pdf","png"):
            path=output/f"iv-1d6r-coefficients{suffix}.{extension}"
            figure.savefig(path,dpi=400)
            products.append(str(path.resolve()))
        plt.close(figure)
    if any(file_hash(Path(path))!=digest for path,digest in hashes.items()):
        raise ValueError("analysis inputs changed during plotting")
    metadata={"input_directory":str(directory.resolve()),"input_sha256":hashes,"plot_source_sha256":file_hash(Path(__file__)),"layout_source_sha256":file_hash(Path(__file__).with_name("rd_plot_layout.py")),"datasets":{key:{"coefficient_curves":len(dataset["curves"]),"points_per_curve":len(dataset["bounds"])} for key,dataset in datasets.items()},"selection":report["protocol"],"flat_reference_policy":report.get("flat_reference_policy"),"expanded_references":report.get("expanded_references",[]),"dimensions_inches":dimensions["main"],"variant_dimensions_inches":dimensions,"panel_width_height_ratio":1.618,"font_size_pt":8,"curves":"one fixed coefficient pair per curve; exact selected measured coordinates, connected in error-bound order; no smoothing, markers, coordinate jitter or synthesized endpoints","best_per_error_bound":"dashed curve may change coefficient pair; it is not another fixed-coefficient setting or an interpolated envelope","detail":"the same complete curves, clipped to a view containing the last two quintic and best-per-bound observations; no new measurement or reselection","products":products}
    metadata["paper_placeholder"]=paper_placeholder
    metadata["style_encoding"]="fixed quintic: red solid; best per error bound: black dashed; all other coefficient pairs: identical light-gray thin solid"
    metadata["legend_labels"]=["Fixed quintic","Best per error bound","Other coefficients"]
    metadata["shared_xlabel_position"]="below the subfigure captions"
    (output/"plot-report.json").write_text(json.dumps(metadata,indent=2,allow_nan=False)+"\n")
    return metadata


def cli():
    parser=argparse.ArgumentParser(description="Plot fixed-pair 1D6R coefficient RD curves from a completed direction/QB-order selection")
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--datasets",nargs="+")
    parser.add_argument("--paper-placeholder",action="store_true",help="Also export a single-column paper figure with a clearly unmeasured third panel")
    arguments=parser.parse_args()
    report=plot(arguments.input,arguments.output,arguments.datasets,arguments.paper_placeholder)
    for key,dataset in report["datasets"].items():
        print(f"{key}: {dataset['coefficient_curves']} fixed-coefficient RD curves, {dataset['points_per_curve']} observations per curve")


if __name__=="__main__":
    cli()
