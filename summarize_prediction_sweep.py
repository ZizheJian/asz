import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

metrics=("BR","H1","PSNR","RMSE","MAE","SAMPLES")
dimensions=("axis","coefficient","qb_order")
file_pattern=re.compile(r"^(?P<prefix>.+)_(?P<family>1d4r|1d6r|2d4r)(?P<axis>01|02|12|0|1|2)_xx(?P<qb_order>[0-2])\.csv$")


def sha256(path):
    digest=hashlib.sha256()
    with open(path,"rb") as input_file:
        while chunk:=input_file.read(1<<20):
            digest.update(chunk)
    return digest.hexdigest()


def close(first,second):
    return math.isclose(first,second,rel_tol=1e-12,abs_tol=1e-15)


def coefficient_key(row):
    values=[row["t1"]]
    if row.get("t2") is not None:
        values.append(row["t2"])
    return tuple(values)


def coefficient_text(values):
    return ",".join(f"{value:.17g}" for value in values)


def parse_coefficient(text):
    values=tuple(float(value) for value in text.split(","))
    if len(values) not in (1,2) or not all(math.isfinite(value) for value in values):
        raise argparse.ArgumentTypeError("coefficient must contain one or two finite comma-separated numbers")
    return values


def parse_source(path,prefix):
    match=file_pattern.match(path.name)
    if match is None or match.group("prefix")!=prefix.name:
        return None
    return match.group("family"),match.group("axis"),int(match.group("qb_order"))


def read_rows(prefix,families):
    rows=[]
    hashes={}
    paths=sorted(prefix.parent.glob(prefix.name+"_*.csv"))
    for path in paths:
        source=parse_source(path,prefix)
        if source is None:
            continue
        family,axis,qb_order=source
        if family not in families:
            continue
        hashes[str(path.resolve())]=sha256(path)
        with open(path,newline="",encoding="utf-8") as input_file:
            reader=csv.DictReader(input_file)
            required={"rel_eb","t1",*metrics}
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                missing=sorted(required-set(reader.fieldnames or ()))
                raise ValueError(f"{path} is missing columns: {','.join(missing)}")
            if family=="1d6r" and "t2" not in reader.fieldnames:
                raise ValueError(f"{path} is missing t2")
            for source_row in reader:
                row={"family":family,"axis":axis,"qb_order":qb_order,"rel_eb":float(source_row["rel_eb"]),"t1":float(source_row["t1"]),"t2":float(source_row["t2"]) if family=="1d6r" else None,"source":str(path.resolve())}
                for metric in metrics:
                    row[metric]=float(source_row[metric])
                if not all(math.isfinite(row[key]) for key in ("rel_eb","t1","BR","H1","PSNR","RMSE","MAE","SAMPLES")):
                    raise ValueError(f"{path} contains a nonfinite value")
                if row["t2"] is not None and not math.isfinite(row["t2"]):
                    raise ValueError(f"{path} contains a nonfinite t2")
                rows.append(row)
    found={row["family"] for row in rows}
    missing=families-found
    if missing:
        raise ValueError(f"no sweep CSVs found for: {','.join(sorted(missing))}")
    return rows,hashes


def filter_rows(rows,axes,qb_orders,coefficients):
    selected=[]
    for row in rows:
        if axes and row["axis"] not in axes:
            continue
        if qb_orders and row["qb_order"] not in qb_orders:
            continue
        if coefficients and not any(len(candidate)==len(coefficient_key(row)) and all(close(first,second) for first,second in zip(candidate,coefficient_key(row))) for candidate in coefficients):
            continue
        selected.append(row)
    if not selected:
        raise ValueError("filters removed every candidate")
    return selected


def validate_grid(rows):
    bounds=sorted({row["rel_eb"] for row in rows},reverse=True)
    if len(bounds)<2:
        raise ValueError("at least two relative error bounds are required")
    by_candidate=defaultdict(set)
    seen=set()
    for row in rows:
        key=(row["family"],row["axis"],row["qb_order"],coefficient_key(row))
        identity=(key,row["rel_eb"])
        if identity in seen:
            raise ValueError(f"duplicate candidate at rel_eb={row['rel_eb']:.17g}: {key}")
        seen.add(identity)
        by_candidate[key].add(row["rel_eb"])
    expected=set(bounds)
    incomplete=[key for key,available in by_candidate.items() if available!=expected]
    if incomplete:
        raise ValueError(f"incomplete error-bound grid for {len(incomplete)} candidates")
    return bounds


def rd_scores(rows,bounds,rate_metric):
    by_bound=defaultdict(list)
    for row in rows:
        by_bound[row["rel_eb"]].append(row)
    averages={bound:(sum(row[rate_metric] for row in by_bound[bound])/len(by_bound[bound]),sum(row["PSNR"] for row in by_bound[bound])/len(by_bound[bound])) for bound in bounds}
    result={}
    for index,bound in enumerate(bounds):
        radius=1
        left=max(0,index-radius)
        right=min(len(bounds)-1,index+radius)
        while left!=right and close(averages[bounds[left]][0],averages[bounds[right]][0]) and (left>0 or right+1<len(bounds)):
            radius+=1
            left=max(0,index-radius)
            right=min(len(bounds)-1,index+radius)
        left_bound=bounds[left]
        right_bound=bounds[right]
        delta_rate=averages[right_bound][0]-averages[left_bound][0]
        delta_psnr=averages[right_bound][1]-averages[left_bound][1]
        current=by_bound[bound]
        if close(delta_rate,0):
            rates=[row[rate_metric] for row in current]
            if all(close(value,rates[0]) for value in rates[1:]):
                kind="equal-rate"
                scores={id(row):row["PSNR"] for row in current}
                slope=None
            else:
                kind="vertical"
                scores={id(row):-row[rate_metric] for row in current}
                slope=None
        else:
            slope=delta_psnr/delta_rate
            if not math.isfinite(slope) or slope<=0:
                raise ValueError(f"nonpositive RD slope at rel_eb={bound:.17g}")
            kind="tangent"
            denominator=math.sqrt(1+slope*slope)
            scores={id(row):(row["PSNR"]-slope*row[rate_metric])/denominator for row in current}
        for row in current:
            result[id(row)]={"score":scores[id(row)],"slope":slope,"score_kind":kind,"slope_left_eb":left_bound,"slope_right_eb":right_bound}
    return result


def direct_scores(rows,criterion):
    if criterion=="rmse":
        return {id(row):{"score":-row["RMSE"],"slope":None,"score_kind":"minimum-rmse","slope_left_eb":None,"slope_right_eb":None} for row in rows}
    if criterion=="mae":
        return {id(row):{"score":-row["MAE"],"slope":None,"score_kind":"minimum-mae","slope_left_eb":None,"slope_right_eb":None} for row in rows}
    if criterion=="psnr":
        return {id(row):{"score":row["PSNR"],"slope":None,"score_kind":"maximum-psnr","slope_left_eb":None,"slope_right_eb":None} for row in rows}
    raise ValueError(f"unknown direct criterion: {criterion}")


def score_rows(rows,bounds,criterion):
    if criterion=="br-psnr":
        return rd_scores(rows,bounds,"BR")
    if criterion=="h1-psnr":
        return rd_scores(rows,bounds,"H1")
    return direct_scores(rows,criterion)


def group_value(row,name):
    return coefficient_key(row) if name=="coefficient" else row[name]


def tie_key(row):
    return row["axis"],row["qb_order"],coefficient_key(row)


def summarize(rows,bounds,retain,criterion):
    scores=score_rows(rows,bounds,criterion)
    groups=defaultdict(list)
    for row in rows:
        key=(row["family"],row["rel_eb"],*(group_value(row,name) for name in retain))
        groups[key].append(row)
    output=[]
    for key,candidates in groups.items():
        best_score=max(scores[id(row)]["score"] for row in candidates)
        tied=[row for row in candidates if close(scores[id(row)]["score"],best_score)]
        winner=min(tied,key=tie_key)
        score=scores[id(winner)]
        output.append({"family":winner["family"],"rel_eb":winner["rel_eb"],"axis":winner["axis"],"qb_order":winner["qb_order"],"coefficient":coefficient_text(coefficient_key(winner)),"t1":winner["t1"],"t2":"" if winner["t2"] is None else winner["t2"],"BR":winner["BR"],"H1":winner["H1"],"PSNR":winner["PSNR"],"RMSE":winner["RMSE"],"MAE":winner["MAE"],"SAMPLES":int(winner["SAMPLES"]),"criterion":criterion,"score":score["score"],"score_kind":score["score_kind"],"slope":"" if score["slope"] is None else score["slope"],"slope_left_eb":"" if score["slope_left_eb"] is None else score["slope_left_eb"],"slope_right_eb":"" if score["slope_right_eb"] is None else score["slope_right_eb"],"tie_count":len(tied),"candidate_count":len(candidates),"source":winner["source"]})
    order={family:index for index,family in enumerate(("1d4r","2d4r","1d6r"))}
    def output_group_value(row,name):
        if name=="coefficient":
            return tuple(float(value) for value in row["coefficient"].split(","))
        return row[name]
    return sorted(output,key=lambda row:(order.get(row["family"],99),-row["rel_eb"],*(output_group_value(row,name) for name in retain)))


def write_csv(path,rows):
    if path.exists():
        raise FileExistsError(f"output already exists: {path}")
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".tmp")
    with open(temporary,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main():
    parser=argparse.ArgumentParser(description="Select prediction-sweep candidates while retaining requested configuration dimensions")
    parser.add_argument("input_prefix",type=Path)
    parser.add_argument("--family",nargs="+",choices=("1d4r","2d4r","1d6r"),required=True)
    parser.add_argument("--retain",nargs="*",choices=dimensions,default=("axis",))
    parser.add_argument("--criterion",choices=("br-psnr","h1-psnr","rmse","mae","psnr"),default="br-psnr")
    parser.add_argument("--axis",nargs="+")
    parser.add_argument("--qb-order",nargs="+",type=int,choices=(0,1,2))
    parser.add_argument("--coefficient",nargs="+",type=parse_coefficient)
    parser.add_argument("--output",type=Path,required=True)
    arguments=parser.parse_args()
    families=set(arguments.family)
    retain=tuple(dict.fromkeys(arguments.retain))
    rows,hashes=read_rows(arguments.input_prefix,families)
    rows=filter_rows(rows,set(arguments.axis or ()),set(arguments.qb_order or ()),arguments.coefficient or ())
    bounds=validate_grid(rows)
    selected=summarize(rows,bounds,retain,arguments.criterion)
    write_csv(arguments.output,selected)
    report={"input_prefix":str(arguments.input_prefix.resolve()),"families":sorted(families),"retain":retain,"criterion":arguments.criterion,"filters":{"axis":arguments.axis or [],"qb_order":arguments.qb_order or [],"coefficient":[coefficient_text(value) for value in arguments.coefficient or ()]},"relative_error_bounds":bounds,"input_rows":len(rows),"output_rows":len(selected),"input_sha256":hashes,"program_sha256":sha256(Path(__file__))}
    report_path=arguments.output.with_suffix(arguments.output.suffix+".json")
    report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(f"wrote {arguments.output}")
    print(f"wrote {report_path}")


if __name__=="__main__":
    main()
