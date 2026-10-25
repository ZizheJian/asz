import argparse
import csv
import hashlib
import json
import math
import re
import struct
from collections import defaultdict
from pathlib import Path

metrics=("BR","H1","PSNR","RMSE","MAE","SAMPLES")
dimensions=("axis","coefficient","qb_order")
file_pattern=re.compile(r"^(?P<prefix>.+)_(?P<family>1d4r|1d6r|2d4r)(?P<axis>01|02|12|0|1|2)_xx(?P<qb_order>[0-2])\.csv$")
family_axes={"1d4r":("0","1","2"),"2d4r":("01","02","12"),"1d6r":("0","1","2")}


def sha256(path):
    digest=hashlib.sha256()
    with open(path,"rb") as input_file:
        while chunk:=input_file.read(1<<20):
            digest.update(chunk)
    return digest.hexdigest()


def close(first,second):
    return math.isclose(first,second,rel_tol=1e-12,abs_tol=1e-15)


def coefficient_key(row):
    return (row["a"],row["b"]) if row["family"]=="1d6r" else (row["t"],)


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
            required={"rel_eb",*metrics}
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                missing=sorted(required-set(reader.fieldnames or ()))
                raise ValueError(f"{path} is missing columns: {','.join(missing)}")
            fields=set(reader.fieldnames)
            if family=="1d6r" and not ({"a","b"}.issubset(fields) or {"t1","t2"}.issubset(fields)):
                raise ValueError(f"{path} is missing 1D6R coefficient columns a,b")
            if family!="1d6r" and "t" not in fields and "t1" not in fields:
                raise ValueError(f"{path} is missing coefficient column t")
            for source_row in reader:
                if family=="1d6r":
                    if {"a","b"}.issubset(fields):
                        t=None;a=float(source_row["a"]);b=float(source_row["b"])
                    else:
                        t=None;a=1/6-float(source_row["t1"]);b=1/6-float(source_row["t2"])
                else:
                    t=float(source_row["t"] if "t" in fields else source_row["t1"]);a=None;b=None
                row={"family":family,"axis":axis,"qb_order":qb_order,"rel_eb":float(source_row["rel_eb"]),"t":t,"a":a,"b":b,"source":str(path.resolve())}
                for metric in metrics:
                    row[metric]=float(source_row[metric])
                if not all(math.isfinite(row[key]) for key in ("rel_eb","BR","H1","PSNR","RMSE","MAE","SAMPLES")) or not all(math.isfinite(value) for value in coefficient_key(row)):
                    raise ValueError(f"{path} contains a nonfinite value")
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


def same_coefficients(first,second):
    return len(first)==len(second) and all(len(left)==len(right) and all(close(a,b) for a,b in zip(left,right)) for left,right in zip(sorted(first),sorted(second)))


def expected_coefficients(family):
    if family=="1d4r":
        return [(index/32,) for index in range(13)]
    if family=="2d4r":
        return [(index/24,) for index in range(-6,7)]
    return None


def float32(value):
    return struct.unpack("f",struct.pack("f",value))[0]


def six_reference_grids():
    legacy=[(1/6-float32(float32(first)/186),1/6-float32(float32(second)/1488)) for first in (0,11,22,31,41) for second in (0,113,248,341,453,567,680,793)]
    augmented=list(legacy)
    exact=[(3/256,-25/256),*((0,(8-index)/32) for index in range(13))]
    for candidate in exact:
        matching=next((index for index,point in enumerate(augmented) if all(abs(left-right)<1e-7 for left,right in zip(point,candidate))),None)
        if matching is None:
            augmented.append(candidate)
        else:
            augmented[matching]=candidate
    equal=(1/6,1/6)
    quintic=(3/256,-25/256)
    four=[(0,(8-index)/32) for index in range(13)]
    transition=[equal,quintic,*four,tuple((left+right)/2 for left,right in zip(equal,quintic))]
    for point in four:
        transition.extend((tuple((left+right)/2 for left,right in zip(equal,point)),tuple((left+right)/2 for left,right in zip(quintic,point))))
    return {"legacy":legacy,"augmented":augmented,"transition":transition}


def matches_expected_coefficients(actual,expected):
    return len(actual)==len(expected) and all(any(len(candidate)==len(reference) and all(math.isclose(value,target,rel_tol=1e-7,abs_tol=1e-8) for value,target in zip(candidate,reference)) for reference in expected) for candidate in actual)


def validate_exhaustive_grid(rows,families,bounds):
    detected={}
    for family in families:
        family_rows=[row for row in rows if row["family"]==family]
        actual_axes={row["axis"] for row in family_rows}
        expected_axes=set(family_axes[family])
        if actual_axes!=expected_axes:
            raise ValueError(f"{family} axes mismatch: expected {sorted(expected_axes)},found {sorted(actual_axes)}")
        reference_coefficients=None
        for axis in family_axes[family]:
            actual_orders={row["qb_order"] for row in family_rows if row["axis"]==axis}
            if actual_orders!={0,1,2}:
                raise ValueError(f"{family} axis {axis} QB orders mismatch: expected [0,1,2],found {sorted(actual_orders)}")
            for qb_order in range(3):
                candidates=[row for row in family_rows if row["axis"]==axis and row["qb_order"]==qb_order]
                coefficients={coefficient_key(row) for row in candidates}
                if reference_coefficients is None:
                    reference_coefficients=coefficients
                elif not same_coefficients(coefficients,reference_coefficients):
                    raise ValueError(f"{family} axis {axis} QB order {qb_order} coefficient grid mismatch")
                expected_rows=len(bounds)*len(coefficients)
                if len(candidates)!=expected_rows:
                    raise ValueError(f"{family} axis {axis} QB order {qb_order} has {len(candidates)} rows,expected {expected_rows}")
        expected=expected_coefficients(family)
        if expected is not None:
            if not matches_expected_coefficients(reference_coefficients,expected):
                raise ValueError(f"{family} coefficient grid does not match the expected {len(expected)} candidates")
            detected[family]=family
        else:
            grids=six_reference_grids()
            matches=[name for name,grid in grids.items() if matches_expected_coefficients(reference_coefficients,grid)]
            if len(matches)!=1:
                raise ValueError(f"{family} coefficient grid does not match a defined grid")
            detected[family]=matches[0]
            grid=grids[matches[0]]
            for row in family_rows:
                coefficient=coefficient_key(row)
                canonical=next(point for point in grid if all(math.isclose(value,target,rel_tol=1e-7,abs_tol=1e-8) for value,target in zip(coefficient,point)))
                row["a"],row["b"]=canonical
    return detected


def validate_uniform_samples(rows):
    counts={int(row["SAMPLES"]) for row in rows}
    if any(row["SAMPLES"]!=int(row["SAMPLES"]) or row["SAMPLES"]<=0 for row in rows):
        raise ValueError("sample counts must be positive integers")
    if len(counts)!=1:
        raise ValueError(f"target sample counts differ: {sorted(counts)}")
    return counts.pop()


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


def matching_bound(bounds,target):
    matches=[bound for bound in bounds if close(bound,target)]
    if len(matches)!=1:
        raise ValueError(f"expected one measured bound matching {target:.17g},found {matches}")
    return matches[0]


def shared_rd_scores(rows,bounds,target_bounds,rate_metric,slope_span):
    by_bound=defaultdict(list)
    for row in rows:
        by_bound[row["rel_eb"]].append(row)
    result={}
    report={}
    for target in target_bounds:
        bound=matching_bound(bounds,target)
        if slope_span is None:
            index=bounds.index(bound)
            coarse=bounds[max(0,index-1)]
            fine=bounds[min(len(bounds)-1,index+1)]
        else:
            coarse=matching_bound(bounds,target*slope_span)
            fine=matching_bound(bounds,target/slope_span)
        coarse_rate=sum(row[rate_metric] for row in by_bound[coarse])/len(by_bound[coarse])
        coarse_psnr=sum(row["PSNR"] for row in by_bound[coarse])/len(by_bound[coarse])
        fine_rate=sum(row[rate_metric] for row in by_bound[fine])/len(by_bound[fine])
        fine_psnr=sum(row["PSNR"] for row in by_bound[fine])/len(by_bound[fine])
        delta_rate=fine_rate-coarse_rate
        delta_psnr=fine_psnr-coarse_psnr
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
                raise ValueError(f"nonpositive shared RD slope at rel_eb={bound:.17g}")
            kind="shared-tangent"
            denominator=math.sqrt(1+slope*slope)
            scores={id(row):(row["PSNR"]-slope*row[rate_metric])/denominator for row in current}
        for row in current:
            result[id(row)]={"score":scores[id(row)],"slope":slope,"score_kind":kind,"slope_left_eb":coarse,"slope_right_eb":fine}
        report[f"{bound:.17g}"]={"coarse_eb":coarse,"fine_eb":fine,"coarse_mean_rate":coarse_rate,"coarse_mean_psnr":coarse_psnr,"fine_mean_rate":fine_rate,"fine_mean_psnr":fine_psnr,"slope":slope,"score_kind":kind,"candidate_count":len(current)}
    return result,report


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


def output_group_value(row,name):
    return tuple(float(value) for value in row["coefficient"].split(",")) if name=="coefficient" else row[name]


def tie_key(row):
    return row["axis"],row["qb_order"],coefficient_key(row)


def selected_row(winner,criterion,score,tie_count,candidate_count,extra=None):
    row={"family":winner["family"],"rel_eb":winner["rel_eb"],"axis":winner["axis"],"qb_order":winner["qb_order"],"coefficient":coefficient_text(coefficient_key(winner)),"t":"" if winner["t"] is None else winner["t"],"a":"" if winner["a"] is None else winner["a"],"b":"" if winner["b"] is None else winner["b"],"BR":winner["BR"],"H1":winner["H1"],"PSNR":winner["PSNR"],"RMSE":winner["RMSE"],"MAE":winner["MAE"],"SAMPLES":int(winner["SAMPLES"]),"criterion":criterion,"score":score["score"],"score_kind":score["score_kind"],"slope":"" if score["slope"] is None else score["slope"],"slope_left_eb":"" if score["slope_left_eb"] is None else score["slope_left_eb"],"slope_right_eb":"" if score["slope_right_eb"] is None else score["slope_right_eb"],"tie_count":tie_count,"candidate_count":candidate_count,"source":winner["source"]}
    if extra:
        row.update(extra)
    return row


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
        output.append(selected_row(winner,criterion,score,len(tied),len(candidates)))
    order={family:index for index,family in enumerate(("1d4r","2d4r","1d6r"))}
    return sorted(output,key=lambda row:(order.get(row["family"],99),-row["rel_eb"],*(output_group_value(row,name) for name in retain)))


def summarize_two_stage(rows,bounds,criterion):
    coefficient_winners=[]
    for family in sorted({row["family"] for row in rows}):
        for axis in family_axes[family]:
            for qb_order in range(3):
                candidates=[row for row in rows if row["family"]==family and row["axis"]==axis and row["qb_order"]==qb_order]
                scores=score_rows(candidates,bounds,criterion)
                for bound in bounds:
                    current=[row for row in candidates if close(row["rel_eb"],bound)]
                    best=max(scores[id(row)]["score"] for row in current)
                    tied=[row for row in current if scores[id(row)]["score"]==best]
                    winner=max(tied,key=coefficient_key)
                    coefficient_winners.append({**winner,"coefficient_selection":scores[id(winner)],"coefficient_tie_count":len(tied),"coefficient_candidate_count":len(current)})
    order_scores={}
    for family in sorted({row["family"] for row in coefficient_winners}):
        for axis in family_axes[family]:
            candidates=[row for row in coefficient_winners if row["family"]==family and row["axis"]==axis]
            order_scores.update(score_rows(candidates,bounds,criterion))
    output=[]
    for family in sorted({row["family"] for row in coefficient_winners}):
        for axis in family_axes[family]:
            for bound in bounds:
                candidates=[row for row in coefficient_winners if row["family"]==family and row["axis"]==axis and close(row["rel_eb"],bound)]
                best=max(order_scores[id(row)]["score"] for row in candidates)
                tied=[row for row in candidates if order_scores[id(row)]["score"]==best]
                winner=min(tied,key=lambda row:row["qb_order"])
                score=order_scores[id(winner)]
                coefficient_score=winner["coefficient_selection"]
                extra={"coefficient_score":coefficient_score["score"],"coefficient_score_kind":coefficient_score["score_kind"],"coefficient_slope":"" if coefficient_score["slope"] is None else coefficient_score["slope"],"coefficient_tie_count":winner["coefficient_tie_count"],"coefficient_candidate_count":winner["coefficient_candidate_count"]}
                output.append(selected_row(winner,criterion,score,len(tied),len(candidates),extra))
    order={family:index for index,family in enumerate(("1d4r","2d4r","1d6r"))}
    return sorted(output,key=lambda row:(order.get(row["family"],99),-row["rel_eb"],row["axis"]))


def summarize_shared_slope(rows,bounds,target_bounds,criterion,slope_span,retain):
    if criterion=="br-psnr":
        scores,slope_report=shared_rd_scores(rows,bounds,target_bounds,"BR",slope_span)
    elif criterion=="h1-psnr":
        scores,slope_report=shared_rd_scores(rows,bounds,target_bounds,"H1",slope_span)
    else:
        raise ValueError("shared-slope selection requires br-psnr or h1-psnr")
    target_rows=[row for row in rows if id(row) in scores]
    groups=defaultdict(list)
    for row in target_rows:
        key=(row["family"],row["rel_eb"],*(group_value(row,name) for name in retain))
        groups[key].append(row)
    output=[]
    for candidates in groups.values():
        best=max(scores[id(row)]["score"] for row in candidates)
        tied=[row for row in candidates if scores[id(row)]["score"]==best]
        winner=min(tied,key=tie_key)
        score=scores[id(winner)]
        output.append(selected_row(winner,criterion,score,len(tied),len(candidates)))
    order={family:index for index,family in enumerate(("1d4r","2d4r","1d6r"))}
    return sorted(output,key=lambda row:(order.get(row["family"],99),-row["rel_eb"],*(output_group_value(row,name) for name in retain))),slope_report


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
    parser.add_argument("--selection",choices=("joint","two-stage","shared-slope"),default="joint")
    parser.add_argument("--target-bound",nargs="+",type=float)
    parser.add_argument("--slope-span",type=float)
    parser.add_argument("--axis",nargs="+")
    parser.add_argument("--qb-order",nargs="+",type=int,choices=(0,1,2))
    parser.add_argument("--coefficient",nargs="+",type=parse_coefficient)
    parser.add_argument("--require-uniform-samples",action="store_true")
    parser.add_argument("--output",type=Path,required=True)
    arguments=parser.parse_args()
    families=set(arguments.family)
    retain=tuple(dict.fromkeys(arguments.retain))
    rows,hashes=read_rows(arguments.input_prefix,families)
    bounds=validate_grid(rows)
    coefficient_grids=validate_exhaustive_grid(rows,families,bounds)
    sample_count=validate_uniform_samples(rows) if arguments.require_uniform_samples else None
    rows=filter_rows(rows,set(arguments.axis or ()),set(arguments.qb_order or ()),arguments.coefficient or ())
    bounds=validate_grid(rows)
    if arguments.selection=="two-stage" and retain!=("axis",):
        raise ValueError("two-stage selection requires --retain axis")
    slope_report=None
    if arguments.selection=="two-stage":
        selected=summarize_two_stage(rows,bounds,arguments.criterion)
    elif arguments.selection=="shared-slope":
        if not arguments.target_bound:
            raise ValueError("shared-slope selection requires --target-bound")
        if arguments.slope_span is not None and (not math.isfinite(arguments.slope_span) or arguments.slope_span<=1):
            raise ValueError("slope span must be finite and greater than one")
        selected,slope_report=summarize_shared_slope(rows,bounds,arguments.target_bound,arguments.criterion,arguments.slope_span,retain)
    else:
        if arguments.target_bound:
            raise ValueError("--target-bound requires shared-slope selection")
        selected=summarize(rows,bounds,retain,arguments.criterion)
    write_csv(arguments.output,selected)
    report={"input_prefix":str(arguments.input_prefix.resolve()),"families":sorted(families),"retain":retain,"criterion":arguments.criterion,"selection":arguments.selection,"coefficient_convention":{"1d4r":"t","2d4r":"t","1d6r":"a is the per-reference weight at +/-5h,b is the per-reference weight at +/-3h,and the +/-h weight is 1/2-a-b"},"coefficient_grids":coefficient_grids,"filters":{"axis":arguments.axis or [],"qb_order":arguments.qb_order or [],"coefficient":[coefficient_text(value) for value in arguments.coefficient or ()]},"relative_error_bounds":bounds,"target_bounds":arguments.target_bound or bounds,"slope_mode":"fixed-span" if arguments.slope_span is not None else "neighboring-measured-bounds" if arguments.selection=="shared-slope" else None,"slope_span":arguments.slope_span,"shared_slopes":slope_report,"uniform_sample_count":sample_count,"input_rows":len(rows),"output_rows":len(selected),"input_sha256":hashes,"program_sha256":sha256(Path(__file__))}
    report_path=arguments.output.with_suffix(arguments.output.suffix+".json")
    report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(f"wrote {arguments.output}")
    print(f"wrote {report_path}")


if __name__=="__main__":
    main()
