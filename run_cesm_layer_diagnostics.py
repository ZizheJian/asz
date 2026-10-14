#!/usr/bin/env python3

import argparse,csv,json,re,subprocess
from pathlib import Path


CASES=[
    {
        "rel_eb":"0.001",
        "plan":"cubic1_012,cubic2_012,cubic2_012,cubic2_012,cubic1_012,cubic2_012,cubic2_012,cubic2_012,cubic1_012,cubic1_012,cubic1_120,cubic2_120,cubic2_120,cubic2_120",
    },
    {
        "rel_eb":"0.1",
        "plan":"cubic2_012,cubic1_012,cubic2_012,cubic2_012,cubic1_012,cubic2_012,cubic1_012,cubic2_012,cubic1_012,cubic2_012,cubic1_120,cubic2_120,cubic1_120,cubic2_120",
    },
]


def parse_args():
    parser=argparse.ArgumentParser()
    parser.add_argument("--binary",type=Path,default=Path("build-layer-diagnostics/s1_compress"))
    parser.add_argument("--input",type=Path,default=Path("/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/cesm-atm-1.5TB/31/T_26x1800x3600.dat"))
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--reuse-logs",action="store_true")
    return parser.parse_args()


def parse_layer(line):
    fields={}
    for item in line.split(":",1)[1].split(","):
        key,value=item.strip().split("=",1)
        fields[key]=value
    return fields


def write_csv(path,rows,fieldnames):
    with path.open("w",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    args=parse_args()
    if args.output.exists() and not args.reuse_logs:
        raise FileExistsError(args.output)
    if not args.output.exists() and args.reuse_logs:
        raise FileNotFoundError(args.output)
    args.output.mkdir(parents=True,exist_ok=args.reuse_logs)
    layer_rows=[]
    summary_rows=[]
    commands=[]
    point_count=26*1800*3600
    for case in CASES:
        for family in ("cubic","quintic"):
            label="1d4r" if family=="cubic" else "1d6r"
            stem=f"cesm-t-{case['rel_eb']}-{label}"
            compressed_path=args.output/f"{stem}.asz"
            log_path=args.output/f"{stem}.log"
            command=[str(args.binary),"-f","-i",str(args.input),"-3","26","1800","3600","-M","REL",case["rel_eb"],"-z",str(compressed_path),"--predictor-plan",case["plan"],"--predictor-family",family,"--report-layer-diagnostics"]
            commands.append({"rel_eb":case["rel_eb"],"predictor":label,"command":command})
            if args.reuse_logs:
                output=log_path.read_text()
            else:
                print(f"Running {stem}",flush=True)
                completed=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                output=completed.stdout
                log_path.write_text(output)
                if completed.returncode!=0:
                    raise RuntimeError(f"{stem} failed; see {log_path}")
            for line in output.splitlines():
                if line.startswith("Layer diagnostics:"):
                    row=parse_layer(line)
                    row["layer_predictor"]=row.pop("predictor")
                    row={"rel_eb":case["rel_eb"],"family":label,**row}
                    layer_rows.append(row)
            metric_match=re.search(r"CR: ([^,]+), BR: ([^,]+), PSNR: ([^\n]+)",output)
            time_match=re.search(r"Compression time: ([^ ]+) s",output)
            if metric_match is None or time_match is None:
                raise RuntimeError(f"missing summary metrics in {log_path}")
            compressed_bytes=compressed_path.stat().st_size
            summary_rows.append({
                "rel_eb":case["rel_eb"],
                "family":label,
                "compressed_bytes":compressed_bytes,
                "measured_bit_rate":8*compressed_bytes/point_count,
                "reported_cr":metric_match.group(1),
                "reported_br":metric_match.group(2),
                "reported_psnr":metric_match.group(3),
                "compression_seconds":time_match.group(1),
            })
    layer_fields=["rel_eb","family","layer","layer_predictor","points","eb","prediction_mse","prediction_mae","reconstruction_mse","reconstruction_mae","reconstruction_psnr","h1","zero_fraction","huffman_bytes","huffman_bps","slope","h1_psnr_score"]
    summary_fields=["rel_eb","family","compressed_bytes","measured_bit_rate","reported_cr","reported_br","reported_psnr","compression_seconds"]
    write_csv(args.output/"layers.csv",layer_rows,layer_fields)
    write_csv(args.output/"summary.csv",summary_rows,summary_fields)
    indexed={(row["rel_eb"],row["layer"],row["family"]):row for row in layer_rows}
    comparison_rows=[]
    for case in CASES:
        for layer in range(len(case["plan"].split(","))):
            four=indexed[(case["rel_eb"],str(layer),"1d4r")]
            six=indexed[(case["rel_eb"],str(layer),"1d6r")]
            value=lambda row,key:float(row[key])
            score_delta=value(six,"h1_psnr_score")-value(four,"h1_psnr_score")
            comparison_rows.append({
                "rel_eb":case["rel_eb"],
                "layer":layer,
                "points":four["points"],
                "prediction_mse_ratio_1d6r_to_1d4r":value(six,"prediction_mse")/value(four,"prediction_mse"),
                "prediction_mae_ratio_1d6r_to_1d4r":value(six,"prediction_mae")/value(four,"prediction_mae"),
                "reconstruction_psnr_delta_1d6r_minus_1d4r":value(six,"reconstruction_psnr")-value(four,"reconstruction_psnr"),
                "h1_delta_1d6r_minus_1d4r":value(six,"h1")-value(four,"h1"),
                "zero_fraction_delta_1d6r_minus_1d4r":value(six,"zero_fraction")-value(four,"zero_fraction"),
                "huffman_bytes_ratio_1d6r_to_1d4r":value(six,"huffman_bytes")/value(four,"huffman_bytes"),
                "h1_psnr_score_delta_1d6r_minus_1d4r":score_delta,
                "score_choice":"1d6r" if score_delta>0 else "1d4r",
            })
    comparison_fields=["rel_eb","layer","points","prediction_mse_ratio_1d6r_to_1d4r","prediction_mae_ratio_1d6r_to_1d4r","reconstruction_psnr_delta_1d6r_minus_1d4r","h1_delta_1d6r_minus_1d4r","zero_fraction_delta_1d6r_minus_1d4r","huffman_bytes_ratio_1d6r_to_1d4r","h1_psnr_score_delta_1d6r_minus_1d4r","score_choice"]
    write_csv(args.output/"comparison.csv",comparison_rows,comparison_fields)
    (args.output/"commands.json").write_text(json.dumps(commands,indent=2)+"\n")


if __name__=="__main__":
    main()
