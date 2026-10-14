import argparse,csv,json,math
from pathlib import Path


def read_csv(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="") as input_file:
        return list(csv.DictReader(input_file))


def validate_fallback(root,spec_path):
    spec=json.loads(spec_path.read_text())
    manifest=json.loads((spec_path.parent/spec["base_manifest"]).read_text())
    expected={task["name"] for task in manifest}-set(spec.get("skip_datasets",[]))
    actual={path.parent.name for path in root.glob("*/raw.csv")}
    if actual!=expected:
        raise ValueError(f"fallback datasets differ: missing={sorted(expected-actual)},extra={sorted(actual-expected)}")
    binary_hashes=set()
    source_hashes=set()
    row_count=0
    for dataset in sorted(expected):
        rows=read_csv(root/dataset/"raw.csv")
        provenance=json.loads((root/dataset/"provenance.json").read_text())
        binary_hashes.add(provenance["binary_sha256"])
        source_hashes.add(json.dumps(provenance["source_hashes"],sort_keys=True))
        bounds=sorted(set(row["REL_EB"] for row in rows))
        for variant in ("sample4_block","sample5_block"):
            if sorted(row["REL_EB"] for row in rows if row["VARIANT"]==variant)!=bounds:
                raise ValueError(f"{dataset} is missing {variant} cases")
        for row in rows:
            data_range=float(row["DATA_RANGE_TIME"])
            core=float(row["CORE_COMPRESSION_TIME"])
            total=float(row["COMPRESSION_TIME"])
            if not math.isclose(data_range+core,total,rel_tol=0,abs_tol=2e-6):
                raise ValueError(f"invalid timing sum in {dataset}")
        row_count+=len(rows)
    if len(binary_hashes)!=1 or len(source_hashes)!=1:
        raise ValueError("fallback tasks used different binaries or sources")
    return {"datasets":len(expected),"rows":row_count,"binary_sha256":next(iter(binary_hashes))}


def validate_rtm(paths):
    result={}
    expected_methods={"asz","sz3","qoz"}
    for path in paths:
        rows=read_csv(path)
        bounds=set(row["REL_EB"] for row in rows)
        if len(bounds)!=5 or len(rows)!=15:
            raise ValueError(f"{path} must contain 5 bounds and 15 rows")
        for bound in bounds:
            methods={row["METHOD"] for row in rows if row["REL_EB"]==bound}
            if methods!=expected_methods:
                raise ValueError(f"{path} rel_eb={bound} has methods {sorted(methods)}")
        for row in rows:
            for field in ("CR","BR","PSNR","COMPRESSION_TIME","DECOMPRESSION_TIME"):
                value=float(row[field])
                if not math.isfinite(value) or value<=0:
                    raise ValueError(f"invalid {field} in {path}")
            if row["METHOD"]=="asz":
                data_range=float(row["DATA_RANGE_TIME"])
                if data_range<=0 or data_range>=float(row["COMPRESSION_TIME"]):
                    raise ValueError(f"invalid ASZ data range time in {path}")
        result[path.stem]={"rows":len(rows),"bounds":len(bounds)}
    return result


def main():
    parser=argparse.ArgumentParser(description="Validate completed ASZ fallback and RTM experiments")
    parser.add_argument("--fallback",type=Path,required=True)
    parser.add_argument("--fallback-spec",type=Path,default=Path("configs/t_fallback_validation.json"))
    parser.add_argument("--rtm",type=Path,nargs=2,default=[Path("results/rtm_small_0360.csv"),Path("results/rtm_big_0750.csv")])
    parser.add_argument("--output",type=Path,required=True)
    arguments=parser.parse_args()
    report={"fallback":validate_fallback(arguments.fallback.resolve(),arguments.fallback_spec.resolve()),"rtm":validate_rtm([path.resolve() for path in arguments.rtm])}
    arguments.output.parent.mkdir(parents=True,exist_ok=True)
    temporary=arguments.output.with_suffix(arguments.output.suffix+".tmp")
    temporary.write_text(json.dumps(report,indent=2)+"\n")
    temporary.replace(arguments.output)
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
