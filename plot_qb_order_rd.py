import argparse,csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import LogLocator,MaxNLocator,NullLocator

from paperfig import PANEL_GAP_WITH_YTICKS_PT,PaperFigureSpec,add_panel_captions,add_shared_xlabel,apply_paper_style,layout_panel_row,legend_above,legend_spacing_kwargs,panel_aspect_ratios,save_paper_png_vertical_crop,style_plot_axis

project_root=Path(__file__).resolve().parent
datasets=(("precip24","Isabel PRECIP\n24"),("qmcpack144","QMCPACK\nOrbital 144"),("aramco1800","Aramco\n1800"))
orders=(0,1,2)
styles={0:{"color":"#2166ac"},1:{"color":"#b2182b"},2:{"color":"#1b7837"}}
markers={0:"o",1:"s",2:"^"}


def load_rows(directory):
    rows=[]
    required={"family","rel_eb","axis","qb_order","coefficient","BR","PSNR"}
    for dataset,_ in datasets:
        path=directory/f"{dataset}.csv"
        with path.open(newline="",encoding="utf-8") as source:
            reader=csv.DictReader(source)
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise ValueError(f"missing required columns in {path}")
            dataset_rows=list(reader)
        for row in dataset_rows:
            row["dataset"]=dataset
            row["rel_eb"]=float(row["rel_eb"])
            row["qb_order"]=int(row["qb_order"])
            row["BR"]=float(row["BR"])
            row["PSNR"]=float(row["PSNR"])
        if {row["family"] for row in dataset_rows}!={"1d4r"} or {row["qb_order"] for row in dataset_rows}!=set(orders):
            raise ValueError(f"incomplete 1D4R QB orders in {path}")
        bounds={order:{row["rel_eb"] for row in dataset_rows if row["qb_order"]==order} for order in orders}
        if len({tuple(sorted(values)) for values in bounds.values()})!=1 or len(next(iter(bounds.values())))!=5:
            raise ValueError(f"inconsistent error bounds in {path}")
        rows.extend(dataset_rows)
    return rows


def render(rows,output_png):
    apply_paper_style()
    spec=PaperFigureSpec.column()
    figure,axes=plt.subplots(1,3,figsize=spec.size_in,dpi=spec.dpi,sharey=False)
    for axis,(dataset,_) in zip(axes,datasets):
        selected=[row for row in rows if row["dataset"]==dataset]
        bounds=sorted({row["rel_eb"] for row in selected},reverse=True)
        groups={bound:[row for row in selected if row["rel_eb"]==bound] for bound in bounds}
        max_bound=max(bounds,key=lambda bound:max(row["BR"] for row in groups[bound])/min(row["BR"] for row in groups[bound]))
        max_group=groups[max_bound]
        max_ratio=max(row["BR"] for row in max_group)/min(row["BR"] for row in max_group)
        for order in orders:
            points=[next(row for row in selected if row["rel_eb"]==bound and row["qb_order"]==order) for bound in bounds]
            axis.plot([row["BR"] for row in points],[row["PSNR"] for row in points],linewidth=.8,marker=markers[order],markersize=2.5,markerfacecolor="white",markeredgewidth=.55,**styles[order])
        axis.set_xscale("log")
        axis.xaxis.set_major_locator(LogLocator(base=100,numticks=4))
        axis.xaxis.set_minor_locator(NullLocator())
        axis.yaxis.set_major_locator(MaxNLocator(nbins=4))
        style_plot_axis(axis)
        axis.grid(True,color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
        axis.set_axisbelow(True)
        for order in orders:
            point=next(row for row in max_group if row["qb_order"]==order)
            axis.plot(point["BR"],point["PSNR"],marker=markers[order],markersize=3,markerfacecolor=styles[order]["color"],markeredgewidth=.55,linestyle="None",**styles[order])
        axis.text(.04,.95,rf"Max. CR ratio: {max_ratio:.2f}$\times$",transform=axis.transAxes,fontsize=6,ha="left",va="top",bbox={"facecolor":"white","edgecolor":"none","pad":.5,"alpha":.8})
    axes[0].set_ylabel("PSNR (dB)")
    layout_panel_row(figure,axes,panel_aspect_ratios(1,1,1),bottom_pt=52,panel_gap_pt=PANEL_GAP_WITH_YTICKS_PT,left_edge_gap_pt=3,right_edge_gap_pt=3)
    handles=[Line2D([],[],label=rf"${axis}$ fastest",linewidth=.8,marker=markers[order],markersize=2.5,markerfacecolor="white",markeredgewidth=.55,**styles[order]) for axis,order in zip(("x","y","z"),orders)]
    legend_above(axes[1],handles=handles,ncol=3,frameon=False,gap_pt=1,row_gap_pt=1,**legend_spacing_kwargs(8,column_gap_pt=5))
    captions=add_panel_captions(figure,axes,[f"({chr(97+index)}) {label}" for index,(_,label) in enumerate(datasets)],gap_pt=2,source="ticks")
    add_shared_xlabel(figure,axes,"Bit rate (bits/value)",gap_pt=2,source_artists=captions)
    output_png.parent.mkdir(parents=True,exist_ok=True)
    save_paper_png_vertical_crop(figure,output_png,spec,edge_gap_pt=3)
    plt.close(figure)


def main():
    parser=argparse.ArgumentParser(description="Plot independently optimized QB serialization-order RD curves")
    parser.add_argument("--input-directory",type=Path,default=project_root/"results/qb-order-common-final18-20261025")
    parser.add_argument("--output-png",type=Path,default=project_root/"新论文/revised-fig/qb-order-rd.png")
    arguments=parser.parse_args()
    render(load_rows(arguments.input_directory),arguments.output_png)
    print(f"wrote {arguments.output_png}")


if __name__=="__main__":
    main()
