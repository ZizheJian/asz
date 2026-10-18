import argparse,csv,math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import LogLocator,MaxNLocator,NullLocator

from plot_final_eighteen_rd import dataset_size,datasets,format_size,methods,styles

project_root=Path(__file__).resolve().parent
timing_baseline_overrides={
    "E017":{"sz3":"final_eighteen_sz3_timing_e017.csv","qoz":"final_eighteen_qoz_timing_e017.csv"},
    "APSU004":{"sz3":"final_eighteen_sz3_timing_apsu004.csv","qoz":"final_eighteen_qoz_timing_apsu004.csv"},
    "Aramco 1800":{"sz3":"final_eight_frozen_aramco.csv","qoz":"final_eight_frozen_aramco.csv"},
    "LETKF PRES":{"sz3":"final_eight_frozen_letkf.csv","qoz":"final_eight_frozen_letkf.csv"},
}


def read_timing_rows(path,method):
    with open(path,newline="",encoding="utf-8") as input_file:
        rows=[row for row in csv.DictReader(input_file) if row["METHOD"]==method]
    if len(rows)!=5:
        raise ValueError(f"{path}的{method}应有5个计时点，实际有{len(rows)}个")
    for row in rows:
        if not row.get("COMPRESSION_TIME") or not row.get("DECOMPRESSION_TIME"):
            raise ValueError(f"{path}的{method}缺少压缩或解压时间")
    return rows


def timing_sources(result_directory,dataset):
    title,_,asz_filename,baseline_filename=dataset
    overrides=timing_baseline_overrides.get(title,{})
    return {
        "asz":result_directory/asz_filename,
        "sz3":result_directory/overrides.get("sz3",baseline_filename),
        "qoz":result_directory/overrides.get("qoz",baseline_filename),
    }


def load_timings(result_directory,dataset):
    sources=timing_sources(result_directory,dataset)
    return {method:read_timing_rows(sources[method],method) for method in methods}


def draw_throughput_panel(axis,title,file_size,timings,index,time_field):
    all_values=[]
    for method in methods:
        points=sorted((float(row["REL_EB"]),file_size/1e9/float(row[time_field])) for row in timings[method])
        all_values.extend(value for _,value in points)
        style=styles[method]
        axis.plot([point[0] for point in points],[point[1] for point in points],color=style["color"],linestyle=style["linestyle"],marker=style["marker"],markerfacecolor="white",linewidth=1.7,markersize=4.2,markeredgewidth=0.9)
    axis.set_xscale("log")
    axis.set_xlim(min(float(row["REL_EB"]) for rows in timings.values() for row in rows)*.75,max(float(row["REL_EB"]) for rows in timings.values() for row in rows)*1.3)
    axis.set_ylim(0,max(all_values)*1.12)
    axis.set_title(f"({chr(ord('a')+index)}) {title}\n{format_size(file_size)}",pad=4)
    axis.grid(True,color="#bdbdbd",linestyle="--",linewidth=0.55,alpha=0.55)
    axis.xaxis.set_major_locator(LogLocator(base=10,numticks=5))
    axis.xaxis.set_minor_locator(NullLocator())
    axis.yaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=3))
    axis.tick_params(direction="in",top=True,right=True,length=3)
    for spine in axis.spines.values():
        spine.set_linewidth(0.85)


def save_throughput(ordered,timings_by_title,output_path,dpi,time_field,y_label):
    figure,axes=plt.subplots(2,6,figsize=(17.5,5.6))
    for index,((title,data_path,_,_),axis) in enumerate(zip(ordered,axes.flat)):
        draw_throughput_panel(axis,title,dataset_size(ordered[index]),timings_by_title[title],index,time_field)
        if index//6==1:
            axis.set_xlabel("Relative error bound")
        if index%6==0:
            axis.set_ylabel(y_label)
    handles=[plt.Line2D([],[],color=styles[method]["color"],linestyle=styles[method]["linestyle"],marker=styles[method]["marker"],markerfacecolor="white",linewidth=1.8,markersize=5,label=styles[method]["label"]) for method in methods]
    figure.legend(handles=handles,loc="upper center",ncol=3,frameon=False,bbox_to_anchor=(0.5,0.997),handlelength=3,columnspacing=2.5)
    figure.subplots_adjust(left=0.05,right=0.995,bottom=0.105,top=0.86,wspace=0.3,hspace=0.5)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    figure.savefig(output_path.with_suffix(".pdf"),bbox_inches="tight")
    figure.savefig(output_path.with_suffix(".png"),dpi=dpi,bbox_inches="tight")
    plt.close(figure)


def preprocessing_time(row):
    if row.get("PREPROCESSING_TIME"):
        return float(row["PREPROCESSING_TIME"])
    return sum(float(row.get(key) or 0) for key in ("GET_DEFAULT_SLOPE_TIME","GENERATE_CONFIG_TIME","PREDICTOR_FAMILY_SELECTION_TIME"))


def row_at_rel_eb(rows,rel_eb):
    matches=[row for row in rows if math.isclose(float(row["REL_EB"]),rel_eb,rel_tol=1e-12,abs_tol=0)]
    if len(matches)!=1:
        raise ValueError(f"rel_eb={rel_eb:g}应有一个计时点，实际有{len(matches)}个")
    return matches[0]


def load_bar_timings(result_directory,ordered,rel_eb):
    result={}
    for dataset in ordered:
        title=dataset[0]
        rows=load_timings(result_directory,dataset)
        result[title]={method:row_at_rel_eb(rows[method],rel_eb) for method in methods}
    return result


def save_runtime_bars(ordered,bar_timings,output_path,dpi,rel_eb):
    method_colors={method:styles[method]["color"] for method in methods}
    size_groups=[("<10 MiB",[]),("10–256 MiB",[]),("256 MiB–2 GiB",[]),("≥2 GiB",[])]
    for dataset in ordered:
        file_size=dataset_size(dataset)
        group_index=0 if file_size<10*2**20 else 1 if file_size<256*2**20 else 2 if file_size<2*2**30 else 3
        size_groups[group_index][1].append(dataset)
    figure,axes=plt.subplots(2,2,figsize=(17.5,9.2))
    width=.245
    offsets={"asz":-width,"sz3":0,"qoz":width}
    for panel_index,((size_label,panel_datasets),axis) in enumerate(zip(size_groups,axes.flat)):
        group_positions=list(range(len(panel_datasets)))
        panel_totals=[]
        totals_by_method={}
        for method in methods:
            positions=[position+offsets[method] for position in group_positions]
            rows=[bar_timings[dataset[0]][method] for dataset in panel_datasets]
            compression=[float(row["COMPRESSION_TIME"]) for row in rows]
            decompression=[float(row["DECOMPRESSION_TIME"]) for row in rows]
            if method=="asz":
                preprocessing=[preprocessing_time(row) for row in rows]
                axis.bar(positions,preprocessing,width,color=method_colors[method],alpha=.35,edgecolor=method_colors[method],hatch="xx",linewidth=.8)
                axis.bar(positions,compression,width,bottom=preprocessing,color=method_colors[method],alpha=.9,edgecolor=method_colors[method],linewidth=.8)
                bottoms=[preprocessing[index]+compression[index] for index in range(len(rows))]
                axis.bar(positions,decompression,width,bottom=bottoms,color=method_colors[method],alpha=.35,edgecolor=method_colors[method],linewidth=.8)
                totals=[bottoms[index]+decompression[index] for index in range(len(rows))]
            else:
                axis.bar(positions,compression,width,color=method_colors[method],alpha=.9,edgecolor=method_colors[method],linewidth=.8)
                axis.bar(positions,decompression,width,bottom=compression,color=method_colors[method],alpha=.35,edgecolor=method_colors[method],linewidth=.8)
                totals=[compression[index]+decompression[index] for index in range(len(rows))]
            totals_by_method[method]=totals
            panel_totals.extend(totals)
        maximum=max(panel_totals)
        axis.set_ylim(0,maximum*1.18)
        for method in methods:
            positions=[position+offsets[method] for position in group_positions]
            for position,total in zip(positions,totals_by_method[method]):
                precision=3 if total<.1 else 2 if total<10 else 1
                axis.text(position,total+maximum*.018,f"{total:.{precision}f}",ha="center",va="bottom",fontsize=6.5,rotation=90)
        axis.set_xticks(group_positions,[dataset[0] for dataset in panel_datasets],rotation=25,ha="right")
        axis.set_title(f"({chr(ord('a')+panel_index)}) Input size {size_label}",pad=8)
        axis.set_ylabel("Total time (s)")
        axis.grid(True,axis="y",color="#bdbdbd",linestyle="--",linewidth=.55,alpha=.55)
        axis.tick_params(direction="in",top=True,right=True)
        axis.yaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=3))
    method_handles=[Patch(facecolor=method_colors[method],edgecolor=method_colors[method],label=styles[method]["label"]) for method in methods]
    stage_handles=[Patch(facecolor="#777777",edgecolor="#333333",hatch="xx",alpha=.35,label="Preprocessing"),Patch(facecolor="#777777",edgecolor="#333333",alpha=.9,label="Compression"),Patch(facecolor="#777777",edgecolor="#333333",alpha=.35,label="Decompression")]
    figure.suptitle(f"Runtime breakdown at relative error bound {rel_eb:g}",y=.995,fontsize=12)
    figure.legend(handles=method_handles+stage_handles,loc="upper center",ncol=6,frameon=False,bbox_to_anchor=(.5,.965))
    figure.subplots_adjust(left=.06,right=.995,bottom=.085,top=.89,wspace=.19,hspace=.48)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    figure.savefig(output_path.with_suffix(".pdf"),bbox_inches="tight")
    figure.savefig(output_path.with_suffix(".png"),dpi=dpi,bbox_inches="tight")
    plt.close(figure)


def main():
    parser=argparse.ArgumentParser(description="绘制最终12数据的吞吐曲线和固定误差界运行时间分解")
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--output-directory",type=Path,default=project_root/"新论文/figs/5")
    parser.add_argument("--rel-eb",type=float,default=1e-3)
    parser.add_argument("--dpi",type=int,default=300)
    arguments=parser.parse_args()

    plt.rcParams.update({"font.family":"sans-serif","font.size":8.5,"axes.titlesize":9.5,"axes.labelsize":10,"xtick.labelsize":7.5,"ytick.labelsize":7.5,"legend.fontsize":10,"pdf.fonttype":42,"ps.fonttype":42})
    ordered=sorted(datasets,key=lambda item:(dataset_size(item),item[0]))
    timings_by_title={dataset[0]:load_timings(arguments.result_directory,dataset) for dataset in ordered}
    save_throughput(ordered,timings_by_title,arguments.output_directory/"throughput-compression-vs-rel-eb",arguments.dpi,"COMPRESSION_TIME","Compression throughput (GB/s)")
    save_throughput(ordered,timings_by_title,arguments.output_directory/"throughput-decompression-vs-rel-eb",arguments.dpi,"DECOMPRESSION_TIME","Decompression throughput (GB/s)")
    bar_timings=load_bar_timings(arguments.result_directory,ordered,arguments.rel_eb)
    save_runtime_bars(ordered,bar_timings,arguments.output_directory/"runtime-breakdown-twelve-1e-3",arguments.dpi,arguments.rel_eb)
    print(f"写入吞吐与运行时间图：{arguments.output_directory}")


if __name__=="__main__":
    main()
