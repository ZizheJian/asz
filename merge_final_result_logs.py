import argparse,csv,re
from pathlib import Path

result_pattern=re.compile(r"^result method=(?P<METHOD>[^,]+),rel_eb=(?P<REL_EB>[^,]+),cr=(?P<CR>[^,]+),br=(?P<BR>[^,]+),psnr=(?P<PSNR>[^,]+),max_error=(?P<MAX_ERROR>[^,]+),absolute_eb=(?P<ABSOLUTE_EB>[^,]+),compressed_bytes=(?P<COMPRESSED_BYTES>[^,]+)(?:,compression_time=(?P<COMPRESSION_TIME>[^,]+),decompression_time=(?P<DECOMPRESSION_TIME>[^,]+))?(?:,generate_config_time=(?P<GENERATE_CONFIG_TIME>[^,]+))?$")
fieldnames=("REL_EB","METHOD","CR","BR","PSNR","MAX_ERROR","ABSOLUTE_EB","COMPRESSED_BYTES","GENERATE_CONFIG_TIME","COMPRESSION_TIME","DECOMPRESSION_TIME")

def main():
    parser=argparse.ArgumentParser(description="从成功点日志合并最终RD结果")
    parser.add_argument("--log",type=Path,action="append",required=True)
    parser.add_argument("--output",type=Path,required=True)
    arguments=parser.parse_args()

    records={}
    for path in arguments.log:
        with open(path,encoding="utf-8") as input_file:
            for line in input_file:
                match=result_pattern.fullmatch(line.rstrip("\n"))
                if match is None:
                    continue
                record={key:value or "" for key,value in match.groupdict().items()}
                key=(float(record["REL_EB"]),record["METHOD"])
                if key in records:
                    raise ValueError(f"重复结果：rel_eb={key[0]:g},method={key[1]}")
                records[key]=record
    expected={(rel_eb,method) for rel_eb in (0.1,0.01,0.001,0.0001,0.00001) for method in ("asz","sz3","qoz")}
    if set(records)!=expected:
        missing=expected-set(records)
        extra=set(records)-expected
        raise ValueError(f"结果集合不完整：missing={sorted(missing)},extra={sorted(extra)}")

    arguments.output.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=arguments.output.with_name(arguments.output.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        for key in sorted(records,key=lambda item:(-item[0],("asz","sz3","qoz").index(item[1]))):
            writer.writerow(records[key])
    temporary_path.replace(arguments.output)
    print(f"写入合并结果：{arguments.output}")

if __name__=="__main__":
    main()
