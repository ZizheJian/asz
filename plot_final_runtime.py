import argparse
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator,NullLocator

from evaluation_datasets import dataset_size,default_manifest,load_datasets,load_timings,methods,preprocessing_time,row_at_rel_eb,styles
from paper_plot_layout import PANEL_ASPECT,add_panel_footers,style_plot_axis

project_root=Path(__file__).resolve().parent
panel_titles={"Nyx Baryon density 632":"Nyx Baryon 632","Nyx Dark-matter density 632":"Nyx Dark matter 632"}
runtime_titles={"QMCPACK Orbital 144":"QMCPACK\nOrbital 144","Isabel PRECIP 24":"Isabel PRECIP\n24","Isabel QRAIN 24":"Isabel QRAIN\n24","Miranda Density":"Miranda\nDensity","Miranda Velocity-x":"Miranda\nVelocity-x","Aramco 1800":"Aramco\n1800","SCALE-LETKF PRES":"SCALE-LETKF\nPRES","SCALE-LETKF T":"SCALE-LETKF\nT","CESM Q 31":"CESM Q\n31","CESM UU 31":"CESM UU\n31","RTM 0750":"RTM\n0750","APS CSSI L0471":"APS CSSI\nL0471","Nyx Baryon density 632":"Nyx Baryon density\n632","Nyx Dark-matter density 632":"Nyx Dark-matter density\n632","APSU 004":"APSU\n004","E 017":"E\n017","APSU 006":"APSU\n006"}


def draw_throughput_panel(axis,dataset,timings,index):
    file_size=dataset_size(dataset)
    all_values=[]
    rel_eb_values=sorted({float(row["REL_EB"]) for rows in timings.values() for row in rows})
    min_exponent=math.floor(math.log10(rel_eb_values[0]))
    max_exponent=math.ceil(math.log10(rel_eb_values[-1]))
    middle_exponent=round((min_exponent+max_exponent)/2)
    x_ticks=[10.0**min_exponent,10.0**middle_exponent,10.0**max_exponent]
    operations=(("COMPRESSION_TIME","-"),("DECOMPRESSION_TIME",(0,(2.4,1.4))))
    for time_field,linestyle in operations:
        for method in methods:
            points=sorted((float(row["REL_EB"]),file_size/1e9/float(row[time_field])) for row in timings[method])
            all_values.extend(value for _,value in points)
            style=styles[method]
            axis.plot([point[0] for point in points],[point[1] for point in points],color=style["color"],linestyle=linestyle,linewidth=.8)
    axis.set_xscale("log")
    axis.set_xlim(x_ticks[0]*.75,x_ticks[-1]*1.8)
    axis.set_ylim(0,max(all_values)*1.12)
    axis.set_box_aspect(1/PANEL_ASPECT)
    axis.set_xticks(x_ticks)
    axis.xaxis.set_minor_locator(NullLocator())
    axis.yaxis.set_major_locator(MaxNLocator(nbins=4,min_n_ticks=3,prune="lower"))
    style_plot_axis(axis)


def draw_throughput_legend(axis):
    axis.axis("off")
    method_handles=[plt.Line2D([],[],color=styles[method]["color"],linestyle="-",linewidth=1.2,label=styles[method]["label"]) for method in methods]
    operation_handles=[plt.Line2D([],[],color="black",linestyle="-",linewidth=.8,label="Compression"),plt.Line2D([],[],color="black",linestyle=(0,(2.4,1.4)),linewidth=.8,label="Decompression")]
    axis.legend(handles=method_handles+operation_handles,loc="center left",bbox_to_anchor=(-.08,.5),frameon=False,handlelength=1.8,handletextpad=.5,labelspacing=.55)


def save_throughput(ordered,timings_by_title,output_path,dpi):
    figure,axes=plt.subplots(3,6,figsize=(7.16,3.2))
    for index,(dataset,axis) in enumerate(zip(ordered,axes.flat)):
        draw_throughput_panel(axis,dataset,timings_by_title[dataset["title"]],index)
    draw_throughput_legend(axes.flat[-1])
    figure.subplots_adjust(left=.06,right=.995,bottom=.13,top=.985,wspace=.25,hspace=.25)
    add_panel_footers(figure,list(axes.flat)[:len(ordered)],[f"({chr(ord('a')+index)}) {panel_titles.get(dataset['title'],dataset['title'])}" for index,dataset in enumerate(ordered)],6,"Relative error bound",8,caption_gap_pt=1,xlabel_gap_pt=3,xlabel_x=.52)
    figure.supylabel("Throughput (GB/s)",x=.006,fontsize=8)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    figure.savefig(output_path.with_suffix(".pdf"))
    figure.savefig(output_path.with_suffix(".png"),dpi=dpi)
    plt.close(figure)


def load_bar_timings(result_directory,ordered,rel_eb):
    result={}
    for dataset in ordered:
        rows=load_timings(result_directory,dataset)
        result[dataset["title"]]={method:row_at_rel_eb(rows[method],rel_eb) for method in methods}
    return result


def save_runtime_bars(ordered,bar_timings,output_path,dpi,rel_eb):
    method_colors={method:styles[method]["color"] for method in methods}
    size_groups=[("<10 MiB",[]),("10–256 MiB",[]),("256 MiB–2 GiB",[]),("≥2 GiB",[])]
    for dataset in ordered:
        file_size=dataset_size(dataset)
        group_index=0 if file_size<10*2**20 else 1 if file_size<256*2**20 else 2 if file_size<2*2**30 else 3
        size_groups[group_index][1].append(dataset)
    figure,axes=plt.subplots(2,2,figsize=(7.16,3.8))
    width=.245
    offsets={"asz":-width,"sz3":0,"qoz":width}
    for panel_index,((size_label,panel_datasets),axis) in enumerate(zip(size_groups,axes.flat)):
        if not panel_datasets:
            axis.axis("off")
            continue
        group_positions=list(range(len(panel_datasets)))
        panel_totals=[]
        totals_by_method={}
        for method in methods:
            positions=[position+offsets[method] for position in group_positions]
            rows=[bar_timings[dataset["title"]][method] for dataset in panel_datasets]
            compression=[float(row["COMPRESSION_TIME"]) for row in rows]
            decompression=[float(row["DECOMPRESSION_TIME"]) for row in rows]
            if method=="asz":
                preprocessing=[preprocessing_time(row) for row in rows]
                axis.bar(positions,preprocessing,width,color=method_colors[method],alpha=.35,edgecolor=method_colors[method],hatch="xx",linewidth=.5)
                axis.bar(positions,compression,width,bottom=preprocessing,color=method_colors[method],alpha=.9,edgecolor=method_colors[method],linewidth=.5)
                bottoms=[preprocessing[index]+compression[index] for index in range(len(rows))]
                axis.bar(positions,decompression,width,bottom=bottoms,color=method_colors[method],alpha=.35,edgecolor=method_colors[method],linewidth=.5)
                totals=[bottoms[index]+decompression[index] for index in range(len(rows))]
            else:
                axis.bar(positions,compression,width,color=method_colors[method],alpha=.9,edgecolor=method_colors[method],linewidth=.5)
                axis.bar(positions,decompression,width,bottom=compression,color=method_colors[method],alpha=.35,edgecolor=method_colors[method],linewidth=.5)
                totals=[compression[index]+decompression[index] for index in range(len(rows))]
            totals_by_method[method]=totals
            panel_totals.extend(totals)
        maximum=max(panel_totals)
        axis.set_ylim(0,maximum*1.18)
        for method in methods:
            positions=[position+offsets[method] for position in group_positions]
            for position,total in zip(positions,totals_by_method[method]):
                precision=3 if total<.1 else 2 if total<10 else 1
                axis.text(position,total+maximum*.018,f"{total:.{precision}f}",ha="center",va="bottom",fontsize=5,rotation=90)
        axis.set_xticks(group_positions,[runtime_titles[dataset["title"]] for dataset in panel_datasets],rotation=25,ha="right")
        axis.set_title(f"({chr(ord('a')+panel_index)}) Input size {size_label}",pad=3)
        axis.set_ylabel("Total time (s)")
        style_plot_axis(axis,grid_axis="y")
        axis.yaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=3))
    method_handles=[Patch(facecolor=method_colors[method],edgecolor=method_colors[method],label=styles[method]["label"]) for method in methods]
    stage_handles=[Patch(facecolor="#777777",edgecolor="#333333",hatch="xx",alpha=.35,label="Preprocessing"),Patch(facecolor="#777777",edgecolor="#333333",alpha=.9,label="Compression"),Patch(facecolor="#777777",edgecolor="#333333",alpha=.35,label="Decompression")]
    figure.suptitle(f"Runtime breakdown at relative error bound {rel_eb:g}",y=.995,fontsize=7)
    figure.legend(handles=method_handles+stage_handles,loc="upper center",ncol=6,frameon=False,bbox_to_anchor=(.5,.96))
    figure.subplots_adjust(left=.065,right=.995,bottom=.18,top=.84,wspace=.2,hspace=.62)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    figure.savefig(output_path.with_suffix(".pdf"))
    figure.savefig(output_path.with_suffix(".png"),dpi=dpi)
    plt.close(figure)


def main():
    parser=argparse.ArgumentParser(description="Plot throughput and runtime for the final 17-field evaluation")
    parser.add_argument("--manifest",type=Path,default=default_manifest)
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--output-directory",type=Path,default=project_root/"新论文/figs/5")
    parser.add_argument("--rel-eb",type=float,default=1e-3)
    parser.add_argument("--dpi",type=int,default=300)
    arguments=parser.parse_args()
    datasets=load_datasets(arguments.manifest)
    plt.rcParams.update({"font.family":"Nimbus Roman","mathtext.fontset":"stix","font.size":8,"axes.titlesize":8,"axes.labelsize":8,"xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":8,"pdf.fonttype":42,"ps.fonttype":42})
    ordered=sorted(datasets,key=lambda dataset:(dataset_size(dataset),dataset["title"]))
    timings_by_title={dataset["title"]:load_timings(arguments.result_directory,dataset) for dataset in ordered}
    with plt.rc_context({"font.size":8,"axes.labelsize":8,"xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":8}):
        save_throughput(ordered,timings_by_title,arguments.output_directory/"throughput-combined-vs-rel-eb",arguments.dpi)
    bar_timings=load_bar_timings(arguments.result_directory,ordered,arguments.rel_eb)
    save_runtime_bars(ordered,bar_timings,arguments.output_directory/"runtime-breakdown-seventeen-1e-3",arguments.dpi,arguments.rel_eb)
    print(f"wrote runtime figures to {arguments.output_directory}")


if __name__=="__main__":
    main()
