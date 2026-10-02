import argparse,csv,math
from pathlib import Path

methods=("asz","sz3","qoz")
fieldnames=("REL_EB","METHOD","CR","BR","PSNR")

def main():
    parser=argparse.ArgumentParser(description="按指定误差界合并已有和补充RD结果")
    parser.add_argument("--input",type=Path,action="append",required=True)
    parser.add_argument("--rel-eb",type=float,action="append",required=True)
    parser.add_argument("--output",type=Path,required=True)
    arguments=parser.parse_args()
    if len(arguments.rel_eb)!=5 or len(set(arguments.rel_eb))!=5:
        raise ValueError("必须提供5个互不重复的rel_eb")

    records={}
    for path in arguments.input:
        with open(path,newline="",encoding="utf-8") as input_file:
            for row in csv.DictReader(input_file):
                rel_eb=float(row["REL_EB"])
                matches=[target for target in arguments.rel_eb if math.isclose(rel_eb,target,rel_tol=1e-12,abs_tol=0)]
                if not matches or row["METHOD"] not in methods:
                    continue
                key=(matches[0],row["METHOD"])
                if key in records:
                    raise ValueError(f"重复结果：rel_eb={key[0]:g},method={key[1]}")
                records[key]={field:row[field] for field in fieldnames}
    expected={(rel_eb,method) for rel_eb in arguments.rel_eb for method in methods}
    if set(records)!=expected:
        missing=expected-set(records)
        extra=set(records)-expected
        raise ValueError(f"结果集合不完整：missing={sorted(missing)},extra={sorted(extra)}")

    arguments.output.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=arguments.output.with_name(arguments.output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        for key in sorted(records,key=lambda item:(-item[0],methods.index(item[1]))):
            writer.writerow(records[key])
    temporary_path.replace(arguments.output)
    print(f"写入合并结果：{arguments.output}")

if __name__=="__main__":
    main()
