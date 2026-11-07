import argparse,csv,json,math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator,FuncFormatter,MultipleLocator,NullLocator

from paperfig import PANEL_GAP_WITH_YTICKS_PT,PaperFigureSpec,add_panel_captions,apply_paper_style,layout_panel_row,legend_above,legend_spacing_kwargs,panel_aspect_ratios,save_paper_png_vertical_crop,style_plot_axis

from analyze_temporal_plan_reuse import interpolate_bit_rate,target_bound,uses_list
from plot_temporal_plan_reuse import columns,load_summary,styles

project_root=Path(__file__).resolve().parent
components="UVW"
component_colors={"U":"#2166ac","V":"#b2182b","W":"#1b7837"}


def read_curves(path,method_prefix=""):
    curves={}
    with open(path,newline="",encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            if row["METHOD"].startswith(method_prefix):
                curves.setdefault((row["DATA_PATH"],row["METHOD"]),{})[float(row["REL_EB"])]=(float(row["PSNR"]),float(row["BR"]))
    return curves


def bound_point(curve,rel_eb):
    return next(value for bound,value in curve.items() if math.isclose(bound,rel_eb,rel_tol=1e-12))


# 每个分量用自己plan在1e-3下的PSNR作为目标，比较另外两个分量的plan在同PSNR下的压缩比
def wind_ratios(self_path,transfer_path):
    self_curves=read_curves(self_path,"asz_self_plan")
    transfer_curves=read_curves(transfer_path)
    ratios=[]
    for target in components:
        data_path=next(path for path,_ in self_curves if path.endswith(f"/{target}f24.bin"))
        psnr,self_rate=bound_point(self_curves[(data_path,"asz_self_plan")],target_bound)
        for source in components:
            if source!=target:
                ratios.append((source,target,self_rate/interpolate_bit_rate(transfer_curves[(data_path,f"asz_{source}_plan")],psnr)))
    return ratios


# APSU006自身plan的结果来自正式18-field实验，在每个误差界的自身PSNR处插值APSU004 plan的码率，超出复用曲线PSNR范围的误差界跳过
def apsu_ratios(manifest_path,transfer_path):
    apsu006=next(dataset for dataset in json.load(open(manifest_path,encoding="utf-8")) if dataset["title"]=="APSU 006")
    self_curve=next(curve for (data_path,method),curve in read_curves(project_root/"results"/apsu006["results"]["asz"]).items() if method=="asz" and data_path==apsu006["data_path"])
    transfer_curve=next(iter(read_curves(transfer_path,"asz_apsu004_plan").values()))
    points=sorted(transfer_curve.values())
    ratios=[]
    for rel_eb,(psnr,self_rate) in sorted(self_curve.items(),reverse=True):
        if points[0][0]<=psnr<=points[-1][0]:
            ratios.append((rel_eb,self_rate/interpolate_bit_rate(transfer_curve,psnr)))
    return ratios


def style_ratio_axis(axis,ylim,step):
    axis.axhline(1,color="#616161",linewidth=.45)
    axis.set_ylim(*ylim)
    axis.yaxis.set_major_locator(MultipleLocator(step))
    style_plot_axis(axis)
    axis.grid(True,axis="y",color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
    axis.set_axisbelow(True)


def render(qmcpack_rows,wind,apsu,output_png):
    apply_paper_style()
    spec=PaperFigureSpec.column()
    figure,axes=plt.subplots(1,3,figsize=spec.size_in,dpi=spec.dpi)
    uses=[int(row["USES"]) for row in qmcpack_rows]
    for kind,style in styles.items():
        axes[0].plot(uses,[1]+[float(row[columns[kind]]) for row in qmcpack_rows[1:]],linewidth=.8,markersize=2.5,**style)
    axes[0].set_xscale("log",base=2)
    axes[0].xaxis.set_major_locator(FixedLocator(uses_list))
    axes[0].xaxis.set_major_formatter(FuncFormatter(lambda value,_:f"{value:g}"))
    axes[0].xaxis.set_minor_locator(NullLocator())
    axes[0].grid(True,axis="x",color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
    axes[0].set_xlabel("Files sharing one plan")
    # 按目标分量分组，每组两根柱子分别来自另外两个分量的plan，柱顶标出plan来源
    for target_index,target in enumerate(components):
        sources=[(source,ratio) for source,local_target,ratio in wind if local_target==target]
        for offset,(source,ratio) in zip((-.18,.18),sources):
            axes[1].bar(target_index+offset,ratio,width=.32,color=component_colors[source])
            axes[1].text(target_index+offset,ratio,source,ha="center",va="bottom",fontsize=6)
    axes[1].set_xticks(range(len(components)),list(components))
    axes[1].set_xlim(-.6,len(components)-.4)
    axes[1].set_ylim(0,1.15)
    axes[1].set_xlabel("Target component")
    # 误差界从左到右减小，只在10的整数次幂处标刻度
    axes[2].plot([rel_eb for rel_eb,_ in apsu],[ratio for _,ratio in apsu],color="#2166ac",marker="o",linewidth=.8,markersize=2.5)
    axes[2].set_xscale("log")
    axes[2].set_xlim(.2,6e-5)
    axes[2].xaxis.set_major_locator(FixedLocator([1e-1,1e-2,1e-3,1e-4]))
    axes[2].xaxis.set_major_formatter(FuncFormatter(lambda value,_:rf"$10^{{{round(math.log10(value))}}}$"))
    axes[2].xaxis.set_minor_locator(NullLocator())
    axes[2].grid(True,axis="x",color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
    axes[2].set_xlabel("Relative error bound")
    # (a)和(c)使用相同的纵轴范围，便于比较
    for axis,ylim,step in zip(axes,((.6,1.04),(0,1.15),(.6,1.04)),(.1,.5,.1)):style_ratio_axis(axis,ylim,step)
    axes[0].set_ylabel("Relative compression ratio")
    layout_panel_row(figure,axes,panel_aspect_ratios(1,1,1),bottom_pt=60,panel_gap_pt=PANEL_GAP_WITH_YTICKS_PT,left_edge_gap_pt=3,right_edge_gap_pt=3)
    handles=[Line2D([],[],linewidth=.8,markersize=2.5,**style) for style in styles.values()]
    legend_above(axes[0],handles=handles,ncol=len(handles),frameon=False,gap_pt=1,row_gap_pt=1,**legend_spacing_kwargs(10,column_gap_pt=5))
    add_panel_captions(figure,axes,["(a) QMCPACK Orbital","(b) Isabel Wind 24","(c) APSU 004$\\to$006"],gap_pt=2,source="xlabel")
    output_png.parent.mkdir(parents=True,exist_ok=True)
    save_paper_png_vertical_crop(figure,output_png,spec,edge_gap_pt=3)
    plt.close(figure)


def main():
    parser=argparse.ArgumentParser(description="Plot the equal-PSNR relative compression ratio of non-temporal plan reuse")
    parser.add_argument("--manifest",type=Path,default=project_root/"configs/final_eighteen.json")
    parser.add_argument("--wind-self",type=Path,default=project_root/"results/isabel_wind_plan_transfer_self.csv")
    parser.add_argument("--wind-transfer",type=Path,default=project_root/"results/isabel_wind_plan_transfer.csv")
    parser.add_argument("--apsu-transfer",type=Path,default=project_root/"results/apsu006_apsu004_plan.csv")
    parser.add_argument("--output-png",type=Path,default=project_root/"overleaf/figures/6/non-temporal-plan-reuse.png")
    arguments=parser.parse_args()
    wind=wind_ratios(arguments.wind_self,arguments.wind_transfer)
    apsu=apsu_ratios(arguments.manifest,arguments.apsu_transfer)
    for source,target,ratio in wind:print(f"wind {source}->{target}: {ratio:.4f}")
    for rel_eb,ratio in apsu:print(f"apsu rel_eb={rel_eb:g}: {ratio:.4f}")
    render(load_summary("qmcpack_orbital"),wind,apsu,arguments.output_png)
    print(f"wrote {arguments.output_png}")


if __name__=="__main__":
    main()
