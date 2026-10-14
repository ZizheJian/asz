import argparse,csv,json,math,statistics
from pathlib import Path


def load_rows(root):
    rows=[]
    for path in sorted(root.glob("*/raw.csv")):
        with path.open(newline="") as input_file:
            for row in csv.DictReader(input_file):
                converted=dict(row)
                for key in ("REL_EB","BR","PSNR","DATA_RANGE_TIME","CORE_COMPRESSION_TIME","COMPRESSION_TIME"):
                    converted[key]=float(converted[key])
                rows.append(converted)
    if not rows:
        raise ValueError(f"no raw.csv files found under {root}")
    return rows


def baseline_slopes(rows):
    slopes={}
    datasets=sorted(set(row["DATASET"] for row in rows))
    for dataset in datasets:
        curve=[row for row in rows if row["DATASET"]==dataset and row["VARIANT"]=="sample4_block"]
        curve.sort(key=lambda row:row["BR"])
        if len(curve)<2:
            raise ValueError(f"{dataset} has fewer than two sample4_block points")
        for index,row in enumerate(curve):
            left=max(0,index-1)
            right=min(len(curve)-1,index+1)
            if left==right:
                raise ValueError(f"cannot estimate slope for {dataset}")
            rate_difference=curve[right]["BR"]-curve[left]["BR"]
            psnr_difference=curve[right]["PSNR"]-curve[left]["PSNR"]
            if rate_difference<=0 or psnr_difference<=0:
                raise ValueError(f"nonmonotone BR-PSNR reference for {dataset} at rel_eb={row['REL_EB']:g}")
            slopes[(dataset,row["REL_EB"])]=psnr_difference/rate_difference
    return slopes


def classify(candidate,reference,slope):
    delta_br=candidate["BR"]-reference["BR"]
    delta_psnr=candidate["PSNR"]-reference["PSNR"]
    score_delta=delta_psnr-slope*delta_br
    tolerance=1e-12*max(1,abs(candidate["PSNR"]),abs(reference["PSNR"]),abs(slope*candidate["BR"]),abs(slope*reference["BR"]))
    decision="win" if score_delta>tolerance else "loss" if score_delta<-tolerance else "tie"
    dominance="dominates" if delta_br<=0 and delta_psnr>=0 and (delta_br<0 or delta_psnr>0) else "dominated" if delta_br>=0 and delta_psnr<=0 and (delta_br>0 or delta_psnr<0) else "tradeoff"
    equivalent_br=-score_delta/slope
    return {"DELTA_BR":delta_br,"DELTA_PSNR":delta_psnr,"SCORE_DELTA":score_delta,"EQUIVALENT_BR_CHANGE":equivalent_br,"EQUIVALENT_BR_CHANGE_PERCENT":100*equivalent_br/reference["BR"],"DECISION":decision,"DOMINANCE":dominance}


def comparisons(rows,slopes):
    by_case={(row["DATASET"],row["REL_EB"],row["VARIANT"]):row for row in rows}
    specifications=[("sample5_block","sample4_block"),("fixed4","sample4_block"),("fixed5","sample5_block"),("fixed5","fixed4")]
    output=[]
    for candidate_name,reference_name in specifications:
        case_keys=sorted({(dataset,bound) for dataset,bound,variant in by_case if variant==candidate_name and (dataset,bound,reference_name) in by_case})
        for dataset,bound in case_keys:
            candidate=by_case[(dataset,bound,candidate_name)]
            reference=by_case[(dataset,bound,reference_name)]
            slope=slopes[(dataset,bound)]
            output.append({"DATASET":dataset,"REL_EB":bound,"FAMILY":candidate["FAMILY"],"CANDIDATE":candidate_name,"REFERENCE":reference_name,"SLOPE":slope,"CANDIDATE_BR":candidate["BR"],"REFERENCE_BR":reference["BR"],"CANDIDATE_PSNR":candidate["PSNR"],"REFERENCE_PSNR":reference["PSNR"],**classify(candidate,reference,slope)})
    return output


def summarize(comparisons,rows):
    result={}
    for candidate,reference in sorted(set((row["CANDIDATE"],row["REFERENCE"]) for row in comparisons)):
        selected=[row for row in comparisons if row["CANDIDATE"]==candidate and row["REFERENCE"]==reference]
        changes=[row["EQUIVALENT_BR_CHANGE_PERCENT"] for row in selected]
        result[f"{candidate}_vs_{reference}"]={"cases":len(selected),"wins":sum(row["DECISION"]=="win" for row in selected),"ties":sum(row["DECISION"]=="tie" for row in selected),"losses":sum(row["DECISION"]=="loss" for row in selected),"dominates":sum(row["DOMINANCE"]=="dominates" for row in selected),"dominated":sum(row["DOMINANCE"]=="dominated" for row in selected),"tradeoffs":sum(row["DOMINANCE"]=="tradeoff" for row in selected),"mean_equivalent_br_change_percent":statistics.fmean(changes),"median_equivalent_br_change_percent":statistics.median(changes),"minimum_equivalent_br_change_percent":min(changes),"maximum_equivalent_br_change_percent":max(changes)}
    range_shares=[100*row["DATA_RANGE_TIME"]/row["COMPRESSION_TIME"] for row in rows]
    result["timing"]={"runs":len(rows),"mean_data_range_share_percent":statistics.fmean(range_shares),"median_data_range_share_percent":statistics.median(range_shares),"minimum_data_range_share_percent":min(range_shares),"maximum_data_range_share_percent":max(range_shares)}
    return result


def write_csv(path,rows):
    temporary=path.with_suffix(path.suffix+".tmp")
    with temporary.open("w",newline="") as output:
        writer=csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main():
    parser=argparse.ArgumentParser(description="Compare ASZ coefficient fallback policies with measured BR-PSNR")
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path)
    arguments=parser.parse_args()
    root=arguments.input.resolve()
    output=(arguments.output or root/"analysis").resolve()
    output.mkdir(parents=True,exist_ok=True)
    rows=load_rows(root)
    slopes=baseline_slopes(rows)
    case_rows=comparisons(rows,slopes)
    summary=summarize(case_rows,rows)
    write_csv(output/"cases.csv",case_rows)
    temporary=output/"summary.json.tmp"
    temporary.write_text(json.dumps(summary,indent=2)+"\n")
    temporary.replace(output/"summary.json")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
