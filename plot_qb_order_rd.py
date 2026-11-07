import argparse,csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import LogFormatterSciNotation,LogLocator,MaxNLocator,NullLocator

from paperfig import PANEL_GAP_WITH_YTICKS_PT,PaperFigureSpec,add_panel_captions,add_shared_xlabel,apply_paper_style,layout_panel_row,legend_above,legend_spacing_kwargs,panel_aspect_ratios,save_paper_png_vertical_crop,style_plot_axis

project_root=Path(__file__).resolve().parent
datasets=(("precip24","Isabel PRECIP 24"),("qmcpack144","QMCPACK\nOrbital 144"),("aramco1800","Aramco 1800"))
orders=(0,1,2)
styles={0:{"color":"#2166ac"},1:{"color":"#b2182b"},2:{"color":"#1b7837"}}


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


def render(rows,extension_rows,output_png):
    apply_paper_style()
    spec=PaperFigureSpec.column()
    figure,axes=plt.subplots(1,3,figsize=spec.size_in,dpi=spec.dpi,sharey=False)
    for axis,(dataset,_) in zip(axes,datasets):
        local=[row for row in rows if row["dataset"]==dataset]
        local_bounds=sorted({row["rel_eb"] for row in local},reverse=True)
        outer=[row for row in extension_rows if row["dataset"]==dataset and (row["rel_eb"]>max(local_bounds) or row["rel_eb"]<min(local_bounds))]
        selected=local+outer
        bounds=sorted({row["rel_eb"] for row in selected},reverse=True)
        for order in orders:
            points=[next(row for row in selected if row["rel_eb"]==bound and row["qb_order"]==order) for bound in bounds]
            axis.plot([row["BR"] for row in points],[row["PSNR"] for row in points],linewidth=.8,**styles[order])
        local_rates=[row["BR"] for row in local]
        local_psnr=[row["PSNR"] for row in local]
        rate_padding=(max(local_rates)/min(local_rates))**.035
        psnr_padding=(max(local_psnr)-min(local_psnr))*.04
        axis.set_xscale("log")
        axis.set_xlim(min(local_rates)/rate_padding,max(local_rates)*rate_padding)
        axis.set_ylim(min(local_psnr)-psnr_padding,max(local_psnr)+psnr_padding)
        axis.xaxis.set_major_locator(LogLocator(base=10,subs=(1,2,5),numticks=6))
        axis.xaxis.set_major_formatter(LogFormatterSciNotation(base=10,labelOnlyBase=True))
        axis.xaxis.set_minor_locator(NullLocator())
        axis.yaxis.set_major_locator(MaxNLocator(nbins=4))
        style_plot_axis(axis)
        axis.grid(True,color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
        axis.set_axisbelow(True)
    axes[0].set_ylabel("PSNR (dB)")
    layout_panel_row(figure,axes,panel_aspect_ratios(1,1,1),bottom_pt=52,panel_gap_pt=PANEL_GAP_WITH_YTICKS_PT,left_edge_gap_pt=3,right_edge_gap_pt=3)
    handles=[Line2D([],[],label=rf"${axis}$ fastest",linewidth=.8,**styles[order]) for axis,order in zip(("x","y","z"),orders)]
    legend_above(axes[1],handles=handles,ncol=3,frameon=False,gap_pt=1,row_gap_pt=1,**legend_spacing_kwargs(8,column_gap_pt=5))
    captions=add_panel_captions(figure,axes,[f"({chr(97+index)}) {label}" for index,(_,label) in enumerate(datasets)],gap_pt=2,source="ticks")
    add_shared_xlabel(figure,axes,"Bit rate (bits/value)",gap_pt=2,source_artists=captions)
    output_png.parent.mkdir(parents=True,exist_ok=True)
    save_paper_png_vertical_crop(figure,output_png,spec,edge_gap_pt=3)
    plt.close(figure)


def main():
    parser=argparse.ArgumentParser(description="Plot independently optimized QB serialization-order RD curves")
    parser.add_argument("--input-directory",type=Path,default=project_root/"results/qb-order-zoom-final18-20261025")
    parser.add_argument("--extension-directory",type=Path,default=project_root/"results/qb-order-common-final18-20261025")
    parser.add_argument("--output-png",type=Path,default=project_root/"overleaf/figures/5/qb-order-rd.png")
    arguments=parser.parse_args()
    render(load_rows(arguments.input_directory),load_rows(arguments.extension_directory),arguments.output_png)
    print(f"wrote {arguments.output_png}")


if __name__=="__main__":
    main()
