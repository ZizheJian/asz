import argparse
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

from evaluation_datasets import compression_time,dataset_size,default_manifest,load_datasets,load_timings,preprocessing_time,styles,throughput_methods
from paperfig import PANEL_GAP_WITH_YTICKS_PT,PaperFigureSpec,add_shared_xlabel,apply_paper_style,layout_panel_grid,legend_above,legend_spacing_kwargs,panel_aspect_ratios,save_paper_png_vertical_crop,style_plot_axis

project_root=Path(__file__).resolve().parent
panel_titles={"QMCPACK Orbital 144":"QMCPACK\nOrbital 144","Miranda Velocity-x":"Miranda\nVelocity-x","Nyx Baryon density 632":"Nyx Baryon 632"}


def format_rel_eb(value):
    exponent=math.floor(math.log10(value))
    coefficient=value/10**exponent
    if math.isclose(coefficient,1,rel_tol=1e-10,abs_tol=1e-12):return rf"$10^{{{exponent}}}$"
    return rf"${coefficient:g}\!\times\!10^{{{exponent}}}$"


def draw_time_panel(axis,dataset,timings):
    rel_eb_values=sorted(float(row["REL_EB"]) for row in timings["asz"])
    rows_by_method={method:{float(row["REL_EB"]):row for row in method_rows} for method,method_rows in timings.items()}
    group_positions=list(range(len(rel_eb_values)))
    width=.16
    maximum=0
    for method_index,method in enumerate(throughput_methods):
        positions=[position+(method_index-2)*width for position in group_positions]
        rows=[rows_by_method[method][rel_eb] for rel_eb in rel_eb_values]
        preprocessing=[preprocessing_time(row) if method=="asz" else 0 for row in rows]
        compression=[compression_time(row) for row in rows]
        decompression=[float(row["DECOMPRESSION_TIME"]) for row in rows]
        color=styles[method]["color"]
        if method=="asz":axis.bar(positions,preprocessing,width,color=color,alpha=.25,edgecolor=color,hatch="xx",linewidth=.35)
        axis.bar(positions,compression,width,bottom=preprocessing,color=color,alpha=.9,edgecolor=color,linewidth=.35)
        compression_tops=[preprocessing[index]+compression[index] for index in range(len(rows))]
        axis.bar(positions,decompression,width,bottom=compression_tops,color=color,alpha=.35,edgecolor=color,linewidth=.35)
        maximum=max(maximum,max(compression_tops[index]+decompression[index] for index in range(len(rows))))
    axis.set_xlim(-.42,len(rel_eb_values)-.58)
    axis.set_ylim(0,maximum*1.08)
    labeled_positions=group_positions[::2]
    labeled_values=rel_eb_values[::2]
    axis.set_xticks(labeled_positions,[format_rel_eb(value) for value in labeled_values],rotation=0,ha="center")
    axis.yaxis.set_major_locator(MaxNLocator(nbins=4,min_n_ticks=3,prune="lower"))
    style_plot_axis(axis)
    axis.grid(True,axis="y",color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
    axis.set_axisbelow(True)


def save_time_by_error_bound(ordered,timings_by_title,output_path,dpi):
    spec=PaperFigureSpec.text(dpi=dpi)
    figure,axes=plt.subplots(3,6,figsize=spec.size_in,dpi=spec.dpi,squeeze=False)
    for dataset,axis in zip(ordered,axes.flat):draw_time_panel(axis,dataset,timings_by_title[dataset["title"]])
    labels=[f"({chr(ord('a')+index)}) {panel_titles.get(dataset['title'],dataset['title'])}" for index,dataset in enumerate(ordered)]
    for axis,label in zip(axes.flat,labels):
        axis.set_xlabel(label,labelpad=2)
    layout_panel_grid(figure,axes,panel_aspect_ratios(1,1,1,1,1,1),bottom_pt=82,column_gap_pt=PANEL_GAP_WITH_YTICKS_PT,row_content_gap_pt=4,left_edge_gap_pt=14,right_edge_gap_pt=3)
    add_shared_xlabel(figure,axes[2],"Relative error bound",gap_pt=2,source_artists=[axis.xaxis.label for axis in axes[2]])
    grid_center=(min(axis.get_position().y0 for axis in axes.flat)+max(axis.get_position().y1 for axis in axes.flat))/2
    figure.supylabel("Time (s)",x=7/spec.width_pt,y=grid_center,fontsize=8)
    method_handles=[Patch(facecolor=styles[method]["color"],edgecolor=styles[method]["color"],label=styles[method]["label"]) for method in throughput_methods]
    stage_handles=[Patch(facecolor="#777777",edgecolor="#333333",hatch="xx",alpha=.25,label="Preprocessing"),Patch(facecolor="#777777",edgecolor="#333333",alpha=.9,label="Compression"),Patch(facecolor="#777777",edgecolor="#333333",alpha=.35,label="Decompression")]
    top=max(axis.get_position().y1 for axis in axes[0])
    legend_above(axes[0,0],handles=method_handles+stage_handles,ncol=8,frameon=False,bbox_to_anchor=(.5,top+1/spec.height_pt),bbox_transform=figure.transFigure,**legend_spacing_kwargs(7,column_gap_pt=3))
    output_path.parent.mkdir(parents=True,exist_ok=True)
    save_paper_png_vertical_crop(figure,output_path.with_suffix(".png"),spec,edge_gap_pt=3)
    plt.close(figure)


def main():
    parser=argparse.ArgumentParser(description="Plot throughput and runtime for the final 18-field evaluation")
    parser.add_argument("--manifest",type=Path,default=default_manifest)
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--output-directory",type=Path,default=project_root/"overleaf/figures/6")
    parser.add_argument("--dpi",type=int,default=300)
    arguments=parser.parse_args()
    datasets=load_datasets(arguments.manifest)
    apply_paper_style(serif_fonts=["Nimbus Roman"])
    ordered=sorted(datasets,key=lambda dataset:(dataset_size(dataset),dataset["title"]))
    timings_by_title={dataset["title"]:load_timings(arguments.result_directory,dataset) for dataset in ordered}
    save_time_by_error_bound(ordered,timings_by_title,arguments.output_directory/"time-breakdown-final-eighteen-vs-rel-eb",arguments.dpi)
    print(f"wrote {arguments.output_directory/'time-breakdown-final-eighteen-vs-rel-eb.png'}")


if __name__=="__main__":
    main()
