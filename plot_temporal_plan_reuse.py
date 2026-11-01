import argparse,csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator,FuncFormatter,MaxNLocator,NullLocator

from paperfig import PaperFigureSpec,apply_paper_style,layout_panel_row,legend_above,legend_spacing_kwargs,panel_aspect_ratios,save_paper_png_vertical_crop,style_plot_axis

from analyze_temporal_plan_reuse import fields,result_root,uses_list

project_root=Path(__file__).resolve().parent
styles={"isabel_precip":{"color":"#2166ac","marker":"o"},"rtm_small":{"color":"#b2182b","marker":"s"},"cesm_uu":{"color":"#1b7837","marker":"^"}}


def load_summary(field):
    path=result_root/field/"loss.csv"
    with open(path,newline="",encoding="utf-8") as input_file:
        rows=list(csv.DictReader(input_file))
    if tuple(int(row["USES"]) for row in rows)!=uses_list:
        raise ValueError(f"{path} does not cover uses {uses_list}")
    return rows


# band=range画单文件最小到最大损失的阴影，band=max只画最大损失虚线
def render(summaries,band,output_png):
    apply_paper_style()
    spec=PaperFigureSpec.column()
    figure,axis=plt.subplots(figsize=spec.size_in,dpi=spec.dpi)
    for field,rows in summaries.items():
        style=styles[field]
        uses=[int(row["USES"]) for row in rows]
        axis.plot(uses,[float(row["AGGREGATE_CR_LOSS_PERCENT"]) for row in rows],linewidth=.8,markersize=2.5,**style)
        upper=[0]+[float(row["MAX_FILE_CR_LOSS_PERCENT"]) for row in rows[1:]]
        if band=="range":
            lower=[0]+[float(row["MIN_FILE_CR_LOSS_PERCENT"]) for row in rows[1:]]
            axis.fill_between(uses,lower,upper,color=style["color"],alpha=.15,linewidth=0)
        else:
            axis.plot(uses,upper,color=style["color"],linestyle="--",linewidth=.6)
    axis.set_xscale("log",base=2)
    axis.xaxis.set_major_locator(FixedLocator(uses_list))
    axis.xaxis.set_major_formatter(FuncFormatter(lambda value,_:f"{value:g}"))
    axis.xaxis.set_minor_locator(NullLocator())
    axis.yaxis.set_major_locator(MaxNLocator(nbins=5))
    axis.axhline(0,color="#616161",linewidth=.45)
    style_plot_axis(axis)
    axis.grid(True,color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
    axis.set_axisbelow(True)
    axis.set_xlabel("Files sharing one plan")
    axis.set_ylabel("Compression-ratio loss (%)")
    layout_panel_row(figure,[axis],panel_aspect_ratios(1),bottom_pt=24,panel_gap_pt=0,left_edge_gap_pt=3,right_edge_gap_pt=3)
    handles=[Line2D([],[],label=fields[field]["title"],linewidth=.8,markersize=2.5,**styles[field]) for field in summaries]
    legend_above(axis,handles=handles,ncol=len(handles),frameon=False,gap_pt=1,row_gap_pt=1,**legend_spacing_kwargs(10,column_gap_pt=5))
    output_png.parent.mkdir(parents=True,exist_ok=True)
    save_paper_png_vertical_crop(figure,output_png,spec,edge_gap_pt=3)
    plt.close(figure)


def main():
    parser=argparse.ArgumentParser(description="Plot equal-PSNR compression-ratio loss against the number of files sharing one plan")
    parser.add_argument("--field",nargs="+",choices=list(fields),default=list(fields))
    parser.add_argument("--band",choices=("range","max"),default="range")
    parser.add_argument("--output-png",type=Path,default=project_root/"新论文/revised-fig/temporal-plan-reuse.png")
    arguments=parser.parse_args()
    render({field:load_summary(field) for field in arguments.field},arguments.band,arguments.output_png)
    print(f"wrote {arguments.output_png}")


if __name__=="__main__":
    main()
