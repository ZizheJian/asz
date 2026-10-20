import argparse,csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import LogLocator,MaxNLocator,NullLocator

from paper_plot_layout import PANEL_ASPECT,add_panel_footers,place_legend_above_axes,style_plot_axis

project_root=Path(__file__).resolve().parent
orders=("xx0","xx1","xx2")
labels={"isabel":"Isabel P 24","cldice":"CESM CLDICE 31","aramco":"Aramco 1800"}
styles={"xx0":{"color":"#2166ac"},"xx1":{"color":"#b2182b"},"xx2":{"color":"#1b7837"}}


def load_rows(path):
    with path.open(newline="",encoding="utf-8") as source:
        reader=csv.DictReader(source)
        required={"dataset","rel_eb","qb_order","BR","PSNR"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"missing required columns in {path}")
        rows=list(reader)
    for row in rows:
        row["rel_eb"]=float(row["rel_eb"])
        row["BR"]=float(row["BR"])
        row["PSNR"]=float(row["PSNR"])
    return rows


def render(rows,output_pdf,output_png):
    with plt.rc_context({"font.family":"Nimbus Roman","mathtext.fontset":"stix","font.size":8,"axes.labelsize":8,"axes.titlesize":8,"xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":8,"pdf.fonttype":42,"ps.fonttype":42}):
        figure,axes=plt.subplots(1,3,figsize=(3.5,1.45),squeeze=False)
        figure.subplots_adjust(left=.105,right=.995,bottom=.38,top=.83,wspace=.3)
        for index,(axis,(dataset,label)) in enumerate(zip(axes.flat,labels.items())):
            selected=[row for row in rows if row["dataset"]==dataset]
            bounds=sorted({row["rel_eb"] for row in selected},reverse=True)
            for order in orders:
                points=[next(row for row in selected if row["rel_eb"]==bound and row["qb_order"]==order) for bound in bounds]
                axis.plot([row["BR"] for row in points],[row["PSNR"] for row in points],linewidth=.8,**styles[order])
            axis.set_xscale("log")
            axis.set_box_aspect(1/PANEL_ASPECT)
            axis.xaxis.set_major_locator(LogLocator(base=10,numticks=4))
            axis.xaxis.set_minor_locator(NullLocator())
            axis.yaxis.set_major_locator(MaxNLocator(nbins=4))
            style_plot_axis(axis)
        add_panel_footers(figure,list(axes.flat),[f"({chr(97+index)}) {label}" for index,label in enumerate(labels.values())],3,"Bit rate (bits/value)",8,caption_gap_pt=1,xlabel_gap_pt=3,xlabel_x=.55)
        figure.supylabel("PSNR (dB)",x=.005,fontsize=8)
        handles=[Line2D([],[],label=rf"${axis}$ fastest",linewidth=.8,**styles[order]) for axis,order in zip(("x","y","z"),orders)]
        legend=figure.legend(handles=handles,loc="upper center",bbox_to_anchor=(.5,1),ncol=3,frameon=False,handlelength=1.25,handletextpad=.3,columnspacing=.65,borderaxespad=0)
        place_legend_above_axes(figure,legend,list(axes.flat))
        output_pdf.parent.mkdir(parents=True,exist_ok=True)
        figure.savefig(output_pdf)
        figure.savefig(output_png,dpi=400)
        plt.close(figure)


def main():
    parser=argparse.ArgumentParser(description="Plot the QB serialization-order RD comparison")
    parser.add_argument("--input",type=Path,default=project_root/"results/qb-order-selection-20261016/selected-by-order.csv")
    parser.add_argument("--output-pdf",type=Path,default=project_root/"新论文/revised-fig/qb-order-rd.pdf")
    parser.add_argument("--output-png",type=Path,default=project_root/"新论文/revised-fig/qb-order-rd.png")
    arguments=parser.parse_args()
    render(load_rows(arguments.input),arguments.output_pdf,arguments.output_png)
    print(f"wrote {arguments.output_pdf}")
    print(f"wrote {arguments.output_png}")


if __name__=="__main__":
    main()
