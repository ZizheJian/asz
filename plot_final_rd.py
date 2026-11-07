import argparse
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import LogLocator,MaxNLocator,NullLocator

from evaluation_datasets import dataset_size,default_manifest,format_size,load_datasets,methods,read_curves,styles
from paperfig import PANEL_GAP_WITH_YTICKS_PT,PaperFigureSpec,add_shared_xlabel,apply_paper_style,layout_panel_grid,legend_above,legend_spacing_kwargs,panel_aspect_ratios,save_paper_png_vertical_crop,style_plot_axis

project_root=Path(__file__).resolve().parent
panel_titles={"QMCPACK Orbital 144":"QMCPACK\nOrbital 144","Miranda Velocity-x":"Miranda\nVelocity-x","Nyx Baryon density 632":"Nyx Baryon 632"}


def pareto_frontier(points):
    best_by_bitrate={}
    for bitrate,psnr in points:
        best_by_bitrate[bitrate]=max(psnr,best_by_bitrate.get(bitrate,-math.inf))
    frontier=[]
    best_psnr=-math.inf
    for bitrate in sorted(best_by_bitrate):
        psnr=best_by_bitrate[bitrate]
        if psnr>best_psnr:
            frontier.append((bitrate,psnr))
            best_psnr=psnr
    return frontier


def draw_dataset(axis,dataset,curves,index):
    for method in methods:
        points=curves[method]
        style=styles[method]
        frontier=pareto_frontier(points)
        axis.plot([point[0] for point in frontier],[point[1] for point in frontier],color=style["color"],linestyle="-",linewidth=.8)
    bound_points=[point for method in methods if method!="zfp" for point in curves[method]]
    bound_points.extend(sorted(curves["zfp"],key=lambda point:point[0])[:2])
    min_bitrate=min(point[0] for point in bound_points)
    max_bitrate=max(point[0] for point in bound_points)
    min_psnr=min(point[1] for point in bound_points)
    max_psnr=max(point[1] for point in bound_points)
    psnr_padding=max(1.5,(max_psnr-min_psnr)*0.04)
    axis.set_xscale("log")
    axis.set_xlim(min_bitrate*.8,max_bitrate*1.15)
    axis.set_ylim(math.floor((min_psnr-psnr_padding)/5)*5,math.ceil((max_psnr+psnr_padding)/5)*5)
    axis.xaxis.set_major_locator(LogLocator(base=10,numticks=5))
    axis.xaxis.set_minor_locator(NullLocator())
    axis.yaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=3))
    style_plot_axis(axis)
    axis.grid(True,color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
    axis.set_axisbelow(True)


def main():
    parser=argparse.ArgumentParser(description="Plot RD curves for the final 18-field evaluation")
    parser.add_argument("--manifest",type=Path,default=default_manifest)
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--output-png",type=Path,default=project_root/"新论文/figs/6/rate-distortion-final-eighteen-log.png")
    parser.add_argument("--dpi",type=int,default=300)
    arguments=parser.parse_args()
    datasets=load_datasets(arguments.manifest)
    apply_paper_style(serif_fonts=["Nimbus Roman"])
    ordered=sorted(datasets,key=lambda dataset:(dataset_size(dataset),dataset["title"]))
    spec=PaperFigureSpec.text(dpi=arguments.dpi)
    figure,axes=plt.subplots(3,6,figsize=spec.size_in,dpi=spec.dpi,squeeze=False)
    for index,(dataset,axis) in enumerate(zip(ordered,axes.flat)):
        draw_dataset(axis,dataset,read_curves(arguments.result_directory,dataset),index)
    labels=[f"({chr(ord('a')+index)}) {panel_titles.get(dataset['title'],dataset['title'])}" for index,dataset in enumerate(ordered)]
    for axis,label in zip(axes.flat,labels):
        axis.set_xlabel(label,labelpad=2)
    layout_panel_grid(figure,axes,panel_aspect_ratios(1,1,1,1,1,1),bottom_pt=52,column_gap_pt=PANEL_GAP_WITH_YTICKS_PT,row_content_gap_pt=4,left_edge_gap_pt=14,right_edge_gap_pt=3)
    add_shared_xlabel(figure,axes[2],"Bit rate (bits/value)",gap_pt=2,source_artists=[axis.xaxis.label for axis in axes[2]])
    grid_center=(min(axis.get_position().y0 for axis in axes.flat)+max(axis.get_position().y1 for axis in axes.flat))/2
    figure.supylabel("PSNR (dB)",x=7/spec.width_pt,y=grid_center,fontsize=8)
    handles=[Line2D([],[],color=styles[method]["color"],linestyle="-",linewidth=.8,label=styles[method]["label"]) for method in methods]
    top=max(axis.get_position().y1 for axis in axes[0])
    legend_above(axes[0,0],handles=handles,ncol=5,frameon=False,bbox_to_anchor=(.5,top+1/spec.height_pt),bbox_transform=figure.transFigure,**legend_spacing_kwargs(12,column_gap_pt=8))
    arguments.output_png.parent.mkdir(parents=True,exist_ok=True)
    save_paper_png_vertical_crop(figure,arguments.output_png,spec,edge_gap_pt=3)
    plt.close(figure)
    for index,dataset in enumerate(ordered,1):
        print(f"{index:2d}. {dataset['title']}: {format_size(dataset_size(dataset))}")
    print(f"wrote {arguments.output_png}")


if __name__=="__main__":
    main()
