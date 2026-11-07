import argparse,csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator,FuncFormatter,MaxNLocator,NullLocator

from paperfig import PANEL_GAP_WITH_YTICKS_PT,PaperFigureSpec,add_panel_captions,add_shared_xlabel,apply_paper_style,layout_panel_row,legend_above,legend_spacing_kwargs,panel_aspect_ratios,save_paper_png_vertical_crop,style_plot_axis

from analyze_temporal_plan_reuse import fields,result_root,temporal_fields,uses_list

project_root=Path(__file__).resolve().parent
styles={"average":{"label":"Average","color":"#2166ac","marker":"o","linestyle":"-"},"minimum":{"label":"Minimum","color":"#b2182b","marker":"s","linestyle":"--"}}
columns={"average":"AGGREGATE_RELATIVE_CR","minimum":"MIN_FILE_RELATIVE_CR"}


def load_summary(field):
    path=result_root/field/"relative_cr.csv"
    with open(path,newline="",encoding="utf-8") as input_file:
        rows=list(csv.DictReader(input_file))
    if tuple(int(row["USES"]) for row in rows)!=uses_list:
        raise ValueError(f"{path} does not cover uses {uses_list}")
    return rows


# 每个field一个子图，画所有文件汇总后的平均相对压缩比和单文件最小相对压缩比，m=1时两者都为1
def render(summaries,output_png):
    apply_paper_style()
    spec=PaperFigureSpec.column()
    figure,axes=plt.subplots(1,len(summaries),figsize=spec.size_in,dpi=spec.dpi,squeeze=False)
    axes=list(axes[0])
    for axis,rows in zip(axes,summaries.values()):
        uses=[int(row["USES"]) for row in rows]
        for kind,style in styles.items():
            axis.plot(uses,[1]+[float(row[columns[kind]]) for row in rows[1:]],linewidth=.8,markersize=2.5,**style)
        axis.set_xscale("log",base=2)
        axis.xaxis.set_major_locator(FixedLocator(uses_list))
        axis.xaxis.set_major_formatter(FuncFormatter(lambda value,_:f"{value:g}"))
        axis.xaxis.set_minor_locator(NullLocator())
        axis.yaxis.set_major_locator(MaxNLocator(nbins=4))
        axis.axhline(1,color="#616161",linewidth=.45)
        style_plot_axis(axis)
        axis.grid(True,color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
        axis.set_axisbelow(True)
    axes[0].set_ylabel("Relative compression ratio")
    layout_panel_row(figure,axes,panel_aspect_ratios(*[1]*len(axes)),bottom_pt=40,panel_gap_pt=PANEL_GAP_WITH_YTICKS_PT,left_edge_gap_pt=3,right_edge_gap_pt=3)
    handles=[Line2D([],[],linewidth=.8,markersize=2.5,**style) for style in styles.values()]
    legend_above(axes[len(axes)//2],handles=handles,ncol=len(handles),frameon=False,gap_pt=1,row_gap_pt=1,**legend_spacing_kwargs(10,column_gap_pt=5))
    captions=add_panel_captions(figure,axes,[f"({chr(97+index)}) {fields[field]['title']}" for index,field in enumerate(summaries)],gap_pt=2,source="ticks")
    add_shared_xlabel(figure,axes,"Files sharing one plan",gap_pt=2,source_artists=captions)
    output_png.parent.mkdir(parents=True,exist_ok=True)
    save_paper_png_vertical_crop(figure,output_png,spec,edge_gap_pt=3)
    plt.close(figure)


def main():
    parser=argparse.ArgumentParser(description="Plot the equal-PSNR relative compression ratio against the number of files sharing one plan")
    parser.add_argument("--field",nargs="+",choices=list(fields),default=list(temporal_fields))
    parser.add_argument("--output-png",type=Path,default=project_root/"新论文/figs/6/temporal-plan-reuse.png")
    arguments=parser.parse_args()
    render({field:load_summary(field) for field in arguments.field},arguments.output_png)
    print(f"wrote {arguments.output_png}")


if __name__=="__main__":
    main()
