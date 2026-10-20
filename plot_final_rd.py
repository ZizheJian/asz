import argparse
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator,MaxNLocator,NullLocator

from evaluation_datasets import dataset_size,default_manifest,format_size,load_datasets,methods,read_curves,styles
from paper_plot_layout import PANEL_ASPECT,add_panel_footers,style_plot_axis

project_root=Path(__file__).resolve().parent
panel_titles={"Nyx Baryon density 632":"Nyx Baryon 632","Nyx Dark-matter density 632":"Nyx Dark matter 632"}


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
    all_points=[]
    for method in methods:
        points=curves[method]
        all_points.extend(points)
        style=styles[method]
        frontier=pareto_frontier(points)
        axis.plot([point[0] for point in frontier],[point[1] for point in frontier],color=style["color"],linestyle="-",linewidth=.8)
    min_bitrate=min(point[0] for point in all_points)
    max_bitrate=max(point[0] for point in all_points)
    min_psnr=min(point[1] for point in all_points)
    max_psnr=max(point[1] for point in all_points)
    psnr_padding=max(1.5,(max_psnr-min_psnr)*0.04)
    axis.set_xscale("log")
    axis.set_xlim(min_bitrate*.8,max_bitrate*1.15)
    axis.set_ylim(math.floor((min_psnr-psnr_padding)/5)*5,math.ceil((max_psnr+psnr_padding)/5)*5)
    axis.set_box_aspect(1/PANEL_ASPECT)
    axis.xaxis.set_major_locator(LogLocator(base=10,numticks=5))
    axis.xaxis.set_minor_locator(NullLocator())
    axis.yaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=3))
    style_plot_axis(axis)


def draw_legend(axis):
    axis.axis("off")
    handles=[plt.Line2D([],[],color=styles[method]["color"],linestyle="-",linewidth=.8,label=styles[method]["label"]) for method in methods]
    axis.legend(handles=handles,loc="center",frameon=False,handlelength=2.4,labelspacing=.8)


def main():
    parser=argparse.ArgumentParser(description="Plot RD curves for the final 17-field evaluation")
    parser.add_argument("--manifest",type=Path,default=default_manifest)
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--output-pdf",type=Path,default=project_root/"新论文/figs/5/rate-distortion-seventeen-log.pdf")
    parser.add_argument("--output-png",type=Path,default=project_root/"新论文/figs/5/rate-distortion-seventeen-log.png")
    parser.add_argument("--dpi",type=int,default=300)
    arguments=parser.parse_args()
    datasets=load_datasets(arguments.manifest)
    plt.rcParams.update({"font.family":"Nimbus Roman","mathtext.fontset":"stix","font.size":8,"axes.labelsize":8,"xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":8,"pdf.fonttype":42,"ps.fonttype":42})
    ordered=sorted(datasets,key=lambda dataset:(dataset_size(dataset),dataset["title"]))
    figure,axes=plt.subplots(3,6,figsize=(7.16,3.2))
    for index,(dataset,axis) in enumerate(zip(ordered,axes.flat)):
        draw_dataset(axis,dataset,read_curves(arguments.result_directory,dataset),index)
    draw_legend(axes.flat[-1])
    figure.subplots_adjust(left=.06,right=.995,bottom=.13,top=.985,wspace=.25,hspace=.25)
    add_panel_footers(figure,list(axes.flat)[:len(ordered)],[f"({chr(ord('a')+index)}) {panel_titles.get(dataset['title'],dataset['title'])}" for index,dataset in enumerate(ordered)],6,"Bit rate (bits/value)",8,caption_gap_pt=1,xlabel_gap_pt=3,xlabel_x=.52)
    figure.supylabel("PSNR (dB)",x=.006,fontsize=8)
    arguments.output_pdf.parent.mkdir(parents=True,exist_ok=True)
    figure.savefig(arguments.output_pdf)
    figure.savefig(arguments.output_png,dpi=arguments.dpi)
    plt.close(figure)
    for index,dataset in enumerate(ordered,1):
        print(f"{index:2d}. {dataset['title']}: {format_size(dataset_size(dataset))}")
    print(f"wrote {arguments.output_pdf}")
    print(f"wrote {arguments.output_png}")


if __name__=="__main__":
    main()
