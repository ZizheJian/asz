import argparse,csv,math,os
from pathlib import Path


project_root=Path(__file__).resolve().parent
result_root=project_root/"results/temporal_plan_reuse"
data_root="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data"
rtm_root="/anvil/projects/x-cis240669/RTM/RtmLab-smalldata-449x449x235/data-3600-intervals5"
fields={
    "isabel_precip":{"title":"Isabel PRECIP","shape":[100,500,500],"labels":[f"{index:02d}" for index in range(1,49)],"path":data_root+"/ISABEL/PRECIP/PRECIPf{label}.bin"},
    "rtm_small":{"title":"RTM Small","shape":[449,449,235],"labels":[f"{index:04d}" for index in range(335,386)],"path":rtm_root+"/aramco-snapshot-{label}.f32"},
    "cesm_uu":{"title":"CESM UU","shape":[26,1800,3600],"labels":[f"{index:02d}" for index in range(63)],"path":data_root+"/cesm-atm-1.5TB/{label}/UU_26x1800x3600.dat"},
    # 非时间复用：按orbital编号排序，与时间步复用用同样的窗口和损失定义
    "qmcpack_orbital":{"title":"QMCPACK Orbital","shape":[115,69,69],"labels":[str(index) for index in range(288)],"path":data_root+"/QMCPACK/orbitals/orbital{label}.f32"},
}
temporal_fields=("isabel_precip","rtm_small","cesm_uu")
uses_list=(1,3,5,9,17)
bounds=(.01,.001,.0001)
target_bound=.001
self_method="asz_self"


def field_paths(field):
    definition=fields[field]
    return [definition["path"].format(label=label) for label in definition["labels"]]


def plan_path(field,label):
    return result_root/field/"plans"/f"{label}.json"


def self_csv_path(field,label):
    return result_root/field/"self"/f"{label}.csv"


def transfer_method(representative_label):
    return f"asz_plan_{representative_label}"


def transfer_csv_path(field,representative_label,target_label):
    return result_root/field/"transfer"/f"{representative_label}_to_{target_label}.csv"


# 每个窗口含uses个文件，代表文件位于窗口中心；放不下一个完整窗口的余数文件前端floor(r/2)个、后端ceil(r/2)个，不参与该uses的统计
def reuse_windows(count,uses):
    if uses<1 or uses%2==0:
        raise ValueError(f"uses must be a positive odd number: {uses}")
    window_count=count//uses
    if window_count==0:
        raise ValueError(f"{count} files cannot hold one {uses}-use window")
    front=(count-window_count*uses)//2
    windows=[]
    for window_id in range(window_count):
        begin=front+window_id*uses
        windows.append((begin+uses//2,tuple(range(begin,begin+uses))))
    return windows


def transfer_pairs(count):
    return sorted({(representative,target) for uses in uses_list for representative,members in reuse_windows(count,uses) for target in members if target!=representative})


def read_curve(path,data_path,method):
    with open(path,newline="",encoding="utf-8") as input_file:
        rows=[row for row in csv.DictReader(input_file) if row["METHOD"]==method]
    if {row["DATA_PATH"] for row in rows}!={data_path}:
        raise ValueError(f"{path} does not contain only {data_path}")
    curve={float(row["REL_EB"]):(float(row["PSNR"]),float(row["BR"])) for row in rows}
    if len(rows)!=len(bounds) or not all(any(math.isclose(bound,rel_eb,rel_tol=1e-12) for rel_eb in curve) for bound in bounds):
        raise ValueError(f"incomplete error-bound grid in {path}")
    return {bound:next(value for rel_eb,value in curve.items() if math.isclose(bound,rel_eb,rel_tol=1e-12)) for bound in bounds}


# PSNR先转换为NMSE再平均，BR直接平均（同一field的文件大小相同）
def aggregate_curves(curves):
    aggregate={}
    for bound in bounds:
        nmse=sum(10**(-curve[bound][0]/10) for curve in curves)/len(curves)
        aggregate[bound]=(-10*math.log10(nmse),sum(curve[bound][1] for curve in curves)/len(curves))
    return aggregate


# 在PSNR上对log(BR)分段线性插值，目标PSNR必须落在曲线测量范围内
def interpolate_bit_rate(curve,psnr):
    points=sorted(curve.values())
    if any(right[0]<=left[0] or right[1]<=left[1] for left,right in zip(points,points[1:])):
        raise ValueError(f"PSNR and BR are not strictly increasing: {points}")
    if not points[0][0]<=psnr<=points[-1][0]:
        raise ValueError(f"target PSNR {psnr} lies outside [{points[0][0]},{points[-1][0]}]")
    for (left_psnr,left_rate),(right_psnr,right_rate) in zip(points,points[1:]):
        if psnr<=right_psnr:
            weight=(psnr-left_psnr)/(right_psnr-left_psnr)
            return math.exp((1-weight)*math.log(left_rate)+weight*math.log(right_rate))
    raise AssertionError("interpolation interval not found")


# 相同PSNR下复用plan与自身plan的压缩比之比，1表示没有损失，小于1表示复用后变差
def relative_compression_ratio(self_curve,reuse_curve):
    psnr,self_rate=self_curve[target_bound]
    return self_rate/interpolate_bit_rate(reuse_curve,psnr)


def load_field(field):
    definition=fields[field]
    labels=definition["labels"]
    paths=field_paths(field)
    self_curves=[read_curve(self_csv_path(field,label),path,self_method) for label,path in zip(labels,paths)]
    transfer_curves={(representative,target):read_curve(transfer_csv_path(field,labels[representative],labels[target]),paths[target],transfer_method(labels[representative])) for representative,target in transfer_pairs(len(labels))}
    return self_curves,transfer_curves


def analyze_field(field,self_curves,transfer_curves):
    labels=fields[field]["labels"]
    summary=[]
    detail=[]
    for uses in uses_list:
        windows=reuse_windows(len(labels),uses)
        members=[target for _,window in windows for target in window]
        reuse_curves={target:self_curves[target] for target in members}
        file_ratios=[]
        for representative,window in windows:
            for target in window:
                if target==representative:
                    continue
                reuse_curves[target]=transfer_curves[(representative,target)]
                ratio=relative_compression_ratio(self_curves[target],reuse_curves[target])
                file_ratios.append(ratio)
                detail.append({"FIELD":field,"USES":uses,"REPRESENTATIVE":labels[representative],"FILE":labels[target],"DISTANCE":abs(target-representative),"SELF_PSNR":self_curves[target][target_bound][0],"SELF_BR":self_curves[target][target_bound][1],"REUSE_BR":interpolate_bit_rate(reuse_curves[target],self_curves[target][target_bound][0]),"RELATIVE_CR":ratio})
        self_aggregate=aggregate_curves([self_curves[target] for target in members])
        reuse_aggregate=aggregate_curves([reuse_curves[target] for target in members])
        summary.append({"FIELD":field,"USES":uses,"PLAN_COUNT":len(windows),"FILE_COUNT":len(members),"TARGET_PSNR":self_aggregate[target_bound][0],"SELF_BR":self_aggregate[target_bound][1],"REUSE_BR":interpolate_bit_rate(reuse_aggregate,self_aggregate[target_bound][0]),"AGGREGATE_RELATIVE_CR":relative_compression_ratio(self_aggregate,reuse_aggregate),"MIN_FILE_RELATIVE_CR":min(file_ratios,default=""),"MAX_FILE_RELATIVE_CR":max(file_ratios,default="")})
    return summary,detail


def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=path.with_name(path.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as output_file:
        writer=csv.DictWriter(output_file,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary_path,path)


def main():
    parser=argparse.ArgumentParser(description="Summarize the equal-PSNR relative compression ratio of plan reuse")
    parser.add_argument("--field",nargs="+",choices=list(fields),default=list(fields))
    arguments=parser.parse_args()
    for field in arguments.field:
        summary,detail=analyze_field(field,*load_field(field))
        write_csv(result_root/field/"relative_cr.csv",summary)
        write_csv(result_root/field/"file_relative_cr.csv",detail)
        for row in summary:
            range_text="" if row["USES"]==1 else f",file_relative_cr=[{row['MIN_FILE_RELATIVE_CR']:.4f},{row['MAX_FILE_RELATIVE_CR']:.4f}]"
            print(f"{field}: uses={row['USES']},plans={row['PLAN_COUNT']},files={row['FILE_COUNT']},aggregate_relative_cr={row['AGGREGATE_RELATIVE_CR']:.4f}{range_text}")


if __name__=="__main__":
    main()
