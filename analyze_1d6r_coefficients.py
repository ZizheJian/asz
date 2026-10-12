import argparse,csv,hashlib,itertools,json,math
from fractions import Fraction
from pathlib import Path

orders=("xx0","xx1","xx2")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parameter_key(values):
    return tuple(round(value,12) for value in values)


def read_manifest(directory):
    path=directory/"provenance.json"
    manifest=json.loads(path.read_text())
    if "1d6r" not in manifest["families"]:
        raise ValueError(f"input has no 1D6R sweep: {directory}")
    return manifest


def load_dataset(directory,key,manifest):
    if key not in manifest["datasets"]:
        raise ValueError(f"dataset {key} is absent from {directory}")
    bounds=[float(value) for value in manifest["error_bounds"].split(",")]
    if len(bounds)<2 or len(set(bounds))!=len(bounds) or any(not math.isfinite(value) or value<=0 for value in bounds):
        raise ValueError("at least two distinct positive finite error bounds are required")
    bounds=sorted(bounds,reverse=True)
    definition=manifest["coefficient_grids"]["1d6r"]
    expected_parameters=None
    if "parameters" in definition:
        expected_parameters={parameter_key(tuple(float(Fraction(value)) for value in pair)) for pair in definition["parameters"]}
        if len(expected_parameters)!=definition["candidate_count"]:
            raise ValueError("invalid coefficient grid in provenance")
    data={}
    hashes={}
    baseline_grid=None
    for axis,order in itertools.product(range(3),orders):
        path=directory/f"{key}_1d6r{axis}_{order}.csv"
        before=file_hash(path)
        with path.open(newline="") as source:
            reader=csv.DictReader(source)
            if reader.fieldnames is None or not {"rel_eb","t1","t2","BR","PSNR","SAMPLES"}.issubset(reader.fieldnames):
                raise ValueError(f"missing required columns: {path}")
            rows=list(reader)
        if file_hash(path)!=before:
            raise ValueError(f"input changed while reading: {path}")
        hashes[str(path.resolve())]=before
        records={}
        samples=None
        for raw in rows:
            bound,t1,t2,rate,quality=(float(raw[name]) for name in ("rel_eb","t1","t2","BR","PSNR"))
            count=int(raw["SAMPLES"])
            if not all(math.isfinite(value) for value in (bound,t1,t2,rate,quality)) or bound<=0 or rate<=0 or count<=0:
                raise ValueError(f"nonfinite or nonpositive observation: {path}")
            record_key=(bound,parameter_key((t1,t2)))
            if record_key in records:
                raise ValueError(f"duplicate coefficient/error-bound observation: {path}")
            if samples is not None and count!=samples:
                raise ValueError(f"target count varies within a stencil: {path}")
            samples=count
            records[record_key]={"dataset":key,"rel_eb":bound,"t1":t1,"t2":t2,"axis":"xyz"[axis],"qb_order":order,"BR":rate,"PSNR":quality,"SAMPLES":count,"source_csv":str(path.resolve())}
        parameters={parameters for _,parameters in records}
        if expected_parameters is not None and parameters!=expected_parameters:
            raise ValueError(f"incomplete coefficient grid: {path}")
        if "candidate_count" in definition and len(parameters)!=definition["candidate_count"]:
            raise ValueError(f"wrong coefficient count: {path}")
        grid=set(itertools.product(bounds,parameters))
        if not parameters or set(records)!=grid or (baseline_grid is not None and grid!=baseline_grid):
            raise ValueError(f"incomplete or mismatched coefficient/error-bound grid: {path}")
        baseline_grid=grid
        shape=manifest["datasets"][key]["shape"]
        if manifest.get("target_mode")=="shared1d":
            expected_samples=len(range(5,shape[axis]-5,2))*math.prod(size for index,size in enumerate(shape) if index!=axis)
            if samples!=expected_samples:
                raise ValueError(f"incorrect shared target count: {path}")
        for record_key,row in records.items():
            candidates=data.setdefault(record_key,[])
            if candidates and candidates[-1]["axis"]==row["axis"] and candidates[-1]["SAMPLES"]!=samples:
                raise ValueError(f"target count differs across QB orders: {path}")
            candidates.append(row)
    return data,bounds,sorted(parameters),hashes


def reference_weights(data,bounds,expand_flat_reference=False):
    # 每个误差界共享一个参考：所有系数、方向和QB顺序的平均实测RD点。
    averages={}
    for bound in bounds:
        rows=[row for (value,_),candidates in data.items() if value==bound for row in candidates]
        averages[bound]=tuple(math.fsum(row[metric] for row in rows)/len(rows) for metric in ("BR","PSNR"))
    references={}
    for index,bound in enumerate(bounds):
        left,right=bounds[max(0,index-1)],bounds[min(len(bounds)-1,index+1)]
        delta_rate=averages[right][0]-averages[left][0]
        delta_quality=averages[right][1]-averages[left][1]
        expanded=False
        current=[row for (value,_),candidates in data.items() if value==bound for row in candidates]
        equal_rates=len({row["BR"] for row in current})==1
        # 仅在原局部参考完全重合且候选码率不等时扩展；不改变已有可定义的评分。
        if expand_flat_reference and delta_rate==delta_quality==0 and not equal_rates:
            for radius in range(2,len(bounds)):
                left,right=bounds[max(0,index-radius)],bounds[min(len(bounds)-1,index+radius)]
                delta_rate=averages[right][0]-averages[left][0]
                delta_quality=averages[right][1]-averages[left][1]
                expanded=True
                if delta_rate!=0 or delta_quality!=0:
                    break
        length=math.hypot(delta_rate,delta_quality)
        if not math.isfinite(length) or delta_rate<0 or delta_quality<0:
            raise ValueError(f"nonfinite or nonmonotone RD reference at {bound}")
        if delta_rate==0 and equal_rates:
            # 等码率时直接比较PSNR；不抖动数据，也不伪造有限斜率。
            rate_weight,quality_weight,kind,slope=0.0,1.0,"equal_rate_psnr",None
        elif length==0:
            raise ValueError(f"undefined RD reference with unequal candidate rates at {bound}")
        else:
            rate_weight,quality_weight=-delta_quality/length,delta_rate/length
            kind="vertical" if delta_rate==0 else "tangent"
            slope=delta_quality/delta_rate if delta_rate else None
            if slope is not None and not math.isfinite(slope):
                slope=None
        references[bound]={"reference_BR":averages[bound][0],"reference_PSNR":averages[bound][1],"slope_left_eb":left,"slope_right_eb":right,"slope":slope,"score_kind":kind,"flat_reference_expanded":expanded,"rate_weight":rate_weight,"quality_weight":quality_weight}
    return references


def selection_key(row):
    # 精确同分时依次选高PSNR、低码率、较小方向和QB序号；不改变主评分。
    return (row["score"],row["PSNR"],-row["BR"],-"xyz".index(row["axis"]),-orders.index(row["qb_order"]))


def select_coefficients(data,bounds,parameters,expand_flat_reference=False):
    references=reference_weights(data,bounds,expand_flat_reference)
    selected=[]
    best=[]
    for bound in bounds:
        reference=references[bound]
        current=[]
        for parameters_key in parameters:
            candidates=data[bound,parameters_key]
            if len(candidates)!=9:
                raise ValueError("each coefficient/error-bound pair requires all nine direction/order combinations")
            scored=[{**row,**reference,"score":reference["rate_weight"]*row["BR"]+reference["quality_weight"]*row["PSNR"]} for row in candidates]
            winner=dict(max(scored,key=selection_key))
            t1,t2=winner["t1"],winner["t2"]
            kind="quintic" if parameter_key((t1,t2))==parameter_key((119/768,203/768)) else "equal_weight" if parameters_key==(0,0) else "embedded_1d4r" if abs(t1-1/6)<1e-12 else "transition"
            winner.update({"coefficient_kind":kind,"t1_fraction":str(Fraction(t1).limit_denominator(1000000)),"t2_fraction":str(Fraction(t2).limit_denominator(1000000)),"outer_weight":1/6-t1,"middle_weight":1/6-t2,"inner_weight":1/6+t1+t2})
            current.append(winner)
        optimum=max(current,key=selection_key)
        for row in current:
            row["score_loss_to_best_coefficient"]=optimum["score"]-row["score"]
        selected.extend(current)
        best.append(dict(optimum))
    return selected,best


def write_csv(path,rows):
    with path.open("x",newline="") as output:
        writer=csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyze(inputs,output,keys=None,expand_flat_reference=False):
    if output.exists():
        raise ValueError(f"output already exists; use a fresh output directory: {output}")
    manifests={path:read_manifest(path) for path in inputs}
    keys=list(keys) if keys is not None else list(dict.fromkeys(key for manifest in manifests.values() for key in manifest["datasets"]))
    if not keys or len(set(keys))!=len(keys):
        raise ValueError("dataset names must be nonempty and distinct")
    selected=[]
    best=[]
    sources={}
    hashes={str((path/"provenance.json").resolve()):file_hash(path/"provenance.json") for path in inputs}
    for key in keys:
        directories=[path for path,manifest in manifests.items() if key in manifest["datasets"]]
        if len(directories)!=1:
            raise ValueError(f"dataset {key} must occur in exactly one input directory")
        directory=directories[0]
        data,bounds,parameters,raw_hashes=load_dataset(directory,key,manifests[directory])
        rows,winners=select_coefficients(data,bounds,parameters,expand_flat_reference)
        selected.extend(rows)
        best.extend(winners)
        hashes.update(raw_hashes)
        sources[key]={"directory":str(directory.resolve()),"dataset":manifests[directory]["datasets"][key],"coefficient_count":len(parameters),"error_bounds":bounds,"raw_measurements":sum(len(candidates) for candidates in data.values()),"selected_points":len(rows)}
    if any(file_hash(Path(path))!=digest for path,digest in hashes.items()):
        raise ValueError("input changed during analysis")
    report={"protocol":"fixed 1D6R coefficient pair; independently select one of nine measured direction/QB-order configurations at each error bound; no coefficient is removed before selection","rd_reference":"one shared tangent per dataset/error bound, estimated from neighboring all-coefficient/all-direction/all-order averaged RD points; one-sided endpoint differences","score":"(PSNR-m*BR)/sqrt(1+m*m), evaluated with a unit normal; vertical references use -BR; equal-rate zero-span cases use PSNR; other undefined/nonmonotone references are rejected","tie_break":"exact score ties prefer higher PSNR, then lower BR, then x/y/z and xx0/xx1/xx2","scope":"reuses frozen-original-reference single-round symbol-stream measurements; not full-compressor RD; score losses are not bitrate percentages","measurements_rerun":False,"datasets":sources,"input_sha256":hashes,"analysis_sha256":file_hash(Path(__file__))}
    report["flat_reference_policy"]="expand the symmetric error-bound index neighborhood until its averaged endpoints differ, only for a fully flat original reference with unequal current candidate bit rates; still reject a fully flat dataset or nonmonotone expanded reference" if expand_flat_reference else "reject a fully flat reference with unequal current candidate bit rates"
    report["expanded_references"]=[{"dataset":key,"rel_eb":bound,"slope_left_eb":rows[0]["slope_left_eb"],"slope_right_eb":rows[0]["slope_right_eb"]} for key in keys for bound in sources[key]["error_bounds"] if (rows:=[row for row in selected if row["dataset"]==key and row["rel_eb"]==bound and row["flat_reference_expanded"]])]
    output.mkdir(parents=True,exist_ok=False)
    write_csv(output/"selected.csv",selected)
    write_csv(output/"best-coefficients.csv",best)
    (output/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report


def cli():
    parser=argparse.ArgumentParser(description="Select the best direction and QB order separately for every fixed 1D6R coefficient pair")
    parser.add_argument("--input",type=Path,nargs="+",required=True,help="Original s2 sweep directories containing raw 1D6R CSVs and provenance.json")
    parser.add_argument("--datasets",nargs="+",help="Dataset keys to analyze; default: all datasets in the supplied inputs")
    parser.add_argument("--output",type=Path,required=True,help="Fresh analysis directory; existing outputs are never replaced")
    parser.add_argument("--expand-flat-reference",action="store_true",help="For fully flat local RD references with unequal candidate rates, expand to the nearest nonflat error-bound neighborhood and record its endpoints")
    arguments=parser.parse_args()
    report=analyze(arguments.input,arguments.output,arguments.datasets,arguments.expand_flat_reference)
    for key,dataset in report["datasets"].items():
        print(f"{key}: {dataset['coefficient_count']} coefficient curves, {dataset['selected_points']} selected points from {dataset['raw_measurements']} existing measurements")


if __name__=="__main__":
    cli()
