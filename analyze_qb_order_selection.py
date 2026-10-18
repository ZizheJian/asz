import argparse,csv,hashlib,json,math
from pathlib import Path


orders=("xx0","xx1","xx2")
axis_names="xyz"
candidate_coefficients=tuple(k/32 for k in range(2,13))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def coefficient_key(value):
    return round(value,12)


def read_manifest(directory):
    path=directory/"provenance.json"
    manifest=json.loads(path.read_text())
    if "1d4r" not in manifest["families"]:
        raise ValueError(f"input has no 1D4R sweep: {directory}")
    return manifest


def load_dataset(directory,key,manifest):
    if key not in manifest["datasets"]:
        raise ValueError(f"dataset {key} is absent from {directory}")
    bounds=sorted((float(value) for value in manifest["error_bounds"].split(",")),reverse=True)
    if len(bounds)<2 or len(bounds)!=len(set(bounds)) or any(not math.isfinite(value) or value<=0 for value in bounds):
        raise ValueError("at least two distinct positive finite error bounds are required")
    data={}
    hashes={}
    baseline_grid=None
    reference_samples={}
    for axis in range(3):
        for order in orders:
            path=directory/f"{key}_1d4r{axis}_{order}.csv"
            before=file_hash(path)
            with path.open(newline="") as source:
                reader=csv.DictReader(source)
                if reader.fieldnames is None or not {"rel_eb","t1","BR","PSNR","SAMPLES"}.issubset(reader.fieldnames):
                    raise ValueError(f"missing required columns: {path}")
                raw=list(reader)
            if file_hash(path)!=before:
                raise ValueError(f"input changed while reading: {path}")
            hashes[str(path.resolve())]=before
            records={}
            for item in raw:
                bound,t,rate,quality=(float(item[name]) for name in ("rel_eb","t1","BR","PSNR"))
                samples=int(item["SAMPLES"])
                if not all(math.isfinite(value) for value in (bound,t,rate,quality)) or bound<=0 or rate<=0 or samples<=0:
                    raise ValueError(f"invalid observation: {path}")
                record_key=(bound,coefficient_key(t))
                if record_key[1] not in {coefficient_key(value) for value in candidate_coefficients}:
                    continue
                if record_key in records:
                    raise ValueError(f"duplicate coefficient/error-bound observation: {path}")
                records[record_key]={"dataset":key,"rel_eb":bound,"t":t,"axis":axis_names[axis],"qb_order":order,"BR":rate,"PSNR":quality,"SAMPLES":samples,"source_csv":str(path.resolve())}
            grid=set(records)
            if baseline_grid is None:
                baseline_grid=grid
            if not grid or grid!=baseline_grid:
                raise ValueError(f"incomplete or mismatched coefficient/error-bound grid: {path}")
            for record_key,row in records.items():
                sample_key=(axis,record_key)
                if sample_key in reference_samples and reference_samples[sample_key]!=row["SAMPLES"]:
                    raise ValueError(f"target count differs across QB orders: {path}")
                reference_samples[sample_key]=row["SAMPLES"]
                data.setdefault(record_key,[]).append(row)
    expected=set((bound,t) for bound in bounds for t in {value for _,value in baseline_grid})
    if set(data)!=expected or any(len(candidates)!=9 for candidates in data.values()):
        raise ValueError(f"incomplete 3-axis by 3-order measurements for {key}")
    for candidates in data.values():
        for axis in axis_names:
            same_axis=[row for row in candidates if row["axis"]==axis]
            reference=same_axis[0]
            if any(not math.isclose(row["PSNR"],reference["PSNR"],rel_tol=1e-11,abs_tol=1e-11) for row in same_axis[1:]):
                raise ValueError(f"QB order changes PSNR for {key}, axis {axis}")
            common_psnr=math.fsum(row["PSNR"] for row in same_axis)/len(same_axis)
            for row in same_axis:
                row["PSNR"]=common_psnr
    return data,bounds,sorted({value for _,value in baseline_grid}),hashes


def reference_weights(data,bounds):
    averages={}
    for bound in bounds:
        rows=[row for (value,_),candidates in data.items() if value==bound for row in candidates]
        averages[bound]=tuple(math.fsum(row[metric] for row in rows)/len(rows) for metric in ("BR","PSNR"))
    references={}
    for index,bound in enumerate(bounds):
        left=bounds[max(0,index-1)]
        right=bounds[min(len(bounds)-1,index+1)]
        delta_rate=averages[right][0]-averages[left][0]
        delta_quality=averages[right][1]-averages[left][1]
        length=math.hypot(delta_rate,delta_quality)
        current=[row for (value,_),candidates in data.items() if value==bound for row in candidates]
        equal_rates=len({row["BR"] for row in current})==1
        if not math.isfinite(length) or delta_rate<0 or delta_quality<0:
            raise ValueError(f"nonfinite or nonmonotone RD reference at {bound}")
        if delta_rate==0 and equal_rates:
            rate_weight,quality_weight,kind,slope=0.0,1.0,"equal_rate_psnr",None
        elif length==0:
            raise ValueError(f"undefined RD reference with unequal candidate rates at {bound}")
        else:
            rate_weight,quality_weight=-delta_quality/length,delta_rate/length
            kind="vertical" if delta_rate==0 else "tangent"
            slope=delta_quality/delta_rate if delta_rate else None
        references[bound]={"reference_BR":averages[bound][0],"reference_PSNR":averages[bound][1],"slope_left_eb":left,"slope_right_eb":right,"slope":slope,"score_kind":kind,"rate_weight":rate_weight,"quality_weight":quality_weight}
    return references


def selection_key(row):
    return (row["score"],row["PSNR"],-row["BR"],-axis_names.index(row["axis"]),-row["t"])


def select_orders(data,bounds,coefficients):
    references=reference_weights(data,bounds)
    selected=[]
    best=[]
    for bound in bounds:
        reference=references[bound]
        current=[]
        for order in orders:
            candidates=[]
            for coefficient in coefficients:
                for row in data[bound,coefficient]:
                    if row["qb_order"]==order:
                        candidates.append({**row,**reference,"score":reference["rate_weight"]*row["BR"]+reference["quality_weight"]*row["PSNR"]})
            if len(candidates)!=3*len(coefficients):
                raise ValueError(f"incomplete candidates for {order} at {bound}")
            winner=dict(max(candidates,key=selection_key))
            current.append(winner)
            selected.append(winner)
        optimum=max(current,key=selection_key)
        tied=[row for row in current if math.isclose(row["score"],optimum["score"],rel_tol=1e-11,abs_tol=1e-12)]
        winner=dict(optimum)
        winner["best_order_set"]="|".join(row["qb_order"] for row in tied)
        best.append(winner)
        for row in current:
            row["score_loss_to_best_order"]=optimum["score"]-row["score"]
            row["best_order_at_bound"]=row in tied
            row["best_order_set"]="|".join(item["qb_order"] for item in tied)
    return selected,best


def write_csv(path,rows):
    with path.open("x",newline="") as output:
        writer=csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def render(selected,labels,output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import LogLocator,MaxNLocator,NullLocator

    styles={"xx0":{"color":"#2166ac","marker":"o"},"xx1":{"color":"#b2182b","marker":"s"},"xx2":{"color":"#1b7837","marker":"^"}}
    with plt.rc_context({"font.family":"STIXGeneral","mathtext.fontset":"stix","font.size":7,"axes.labelsize":7,"xtick.labelsize":6.5,"ytick.labelsize":6.5,"legend.fontsize":7,"pdf.fonttype":42,"ps.fonttype":42}):
        figure,axes=plt.subplots(1,len(labels),figsize=(3.5,1.55),squeeze=False)
        figure.subplots_adjust(left=0.12,right=0.99,bottom=0.29,top=0.77,wspace=0.28)
        for index,(axis,(key,label)) in enumerate(zip(axes.flat,labels.items())):
            rows=[row for row in selected if row["dataset"]==key]
            bounds=sorted({row["rel_eb"] for row in rows},reverse=True)
            for order in orders:
                points=[next(row for row in rows if row["rel_eb"]==bound and row["qb_order"]==order) for bound in bounds]
                axis.plot([row["BR"] for row in points],[row["PSNR"] for row in points],linewidth=0.8,markersize=2.3,markeredgewidth=0.45,markerfacecolor="white",**styles[order])
            axis.set_xscale("log")
            axis.xaxis.set_major_locator(LogLocator(base=10,numticks=4))
            axis.xaxis.set_minor_locator(NullLocator())
            axis.yaxis.set_major_locator(MaxNLocator(nbins=4))
            axis.tick_params(direction="in",length=2,width=0.45,pad=1)
            axis.grid(alpha=0.2,linewidth=0.3)
            axis.set_title(f"({chr(97+index)}) {label}",pad=2)
            for spine in axis.spines.values():
                spine.set_linewidth(0.5)
        axes[0,0].set_ylabel("PSNR (dB)",labelpad=1)
        figure.supxlabel("Bit rate (bits/QB)",x=0.555,y=0.04,fontsize=7)
        handles=[Line2D([],[],label=f"Dimension {index} fastest",linewidth=0.8,markersize=2.3,markeredgewidth=0.45,markerfacecolor="white",**styles[order]) for index,order in enumerate(orders)]
        figure.legend(handles=handles,loc="upper center",bbox_to_anchor=(0.555,0.99),ncol=3,frameon=False,handlelength=1.25,handletextpad=0.3,columnspacing=0.65,borderaxespad=0)
        figure.savefig(output,bbox_inches="tight",pad_inches=0.01)
        plt.close(figure)


def analyze(input_directory,output_directory,keys):
    if output_directory.exists():
        raise ValueError(f"output already exists: {output_directory}")
    manifest=read_manifest(input_directory)
    selected=[]
    best=[]
    sources={}
    hashes={str((input_directory/"provenance.json").resolve()):file_hash(input_directory/"provenance.json")}
    labels={}
    for key in keys:
        data,bounds,coefficients,raw_hashes=load_dataset(input_directory,key,manifest)
        rows,winners=select_orders(data,bounds,coefficients)
        selected.extend(rows)
        best.extend(winners)
        hashes.update(raw_hashes)
        labels[key]={"isabel":"Isabel","cldice":"CLDICE","aramco":"Aramco"}.get(key,manifest["datasets"][key]["label"])
        sources[key]={"dataset":manifest["datasets"][key],"error_bounds":bounds,"coefficient_count":len(coefficients),"candidate_count_per_order_and_bound":3*len(coefficients)}
    if any(file_hash(Path(path))!=digest for path,digest in hashes.items()):
        raise ValueError("input changed during analysis")
    output_directory.mkdir(parents=True,exist_ok=False)
    write_csv(output_directory/"selected-by-order.csv",selected)
    write_csv(output_directory/"best-orders.csv",best)
    figure_path=output_directory/"qb-order-rd.pdf"
    render(selected,labels,figure_path)
    best_sets=[row["best_order_set"].split("|") for row in best]
    unique_wins={order:sum(values==[order] for values in best_sets) for order in orders}
    inclusive_wins={order:sum(order in values for values in best_sets) for order in orders}
    report={"protocol":"for each dataset, relative error bound, and QB serialization order, select the measured 1D4R prediction axis and coefficient with the largest shared tangent score","candidate_coefficients":[f"{k}/32" for k in range(2,13)],"rd_reference":"one shared tangent per dataset and error bound, estimated from neighboring averages over all candidate coefficients, prediction axes, and QB orders; one-sided endpoint differences","scope":manifest["protocol"],"datasets":sources,"unique_wins_across_dataset_error_bound_cases":unique_wins,"inclusive_wins_across_dataset_error_bound_cases":inclusive_wins,"tied_cases":sum(len(values)>1 for values in best_sets),"input_sha256":hashes,"analysis_sha256":file_hash(Path(__file__)),"products":[str((output_directory/"selected-by-order.csv").resolve()),str((output_directory/"best-orders.csv").resolve()),str(figure_path.resolve())]}
    (output_directory/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report


def cli():
    parser=argparse.ArgumentParser(description="Compare QB serialization orders after independently optimizing the 1D4R axis and coefficient")
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--datasets",nargs="+",default=("isabel","cldice","aramco"))
    arguments=parser.parse_args()
    report=analyze(arguments.input,arguments.output,arguments.datasets)
    print(json.dumps({"unique_wins":report["unique_wins_across_dataset_error_bound_cases"],"tied_cases":report["tied_cases"]},indent=2))


if __name__=="__main__":
    cli()
