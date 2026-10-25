import argparse,csv,math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import LogLocator,MaxNLocator,NullLocator

from paper_plot_layout import PANEL_ASPECT,add_panel_footers,place_legend_above_axes,style_plot_axis
from paperfig import PANEL_GAP_WITHOUT_Y_DECORATION_PT,PaperFigureSpec,add_panel_captions,add_shared_xlabel,apply_paper_style,layout_panel_grid,layout_panel_row,legend_above,legend_spacing_kwargs,panel_aspect_ratios,save_paper_png_vertical_crop,style_plot_axis as style_paper_axis

project_root=Path(__file__).resolve().parent
family_styles=((0,(3,2)),(0,(1.5,1)),(0,(3,1.5,.75,1)))
family_colors=("#2166ac","#b2182b")
names={"isabel":"Isabel P 24","cldice":"CESM CLDICE 31","cesmt":"CESM T 31","aramco":"Aramco 1800","letkf":"SCALE-LETKF PRES","letkf_qv":"SCALE-LETKF QV","qmcpack":"QMCPACK Orbital 0","precip24":"Isabel PRECIP 24","qmcpack144":"QMCPACK Orbital 144","aramco1800":"Aramco 1800","vd01_31":"CESM VD01 31","letkf_pres":"SCALE-LETKF PRES","letkf_t":"SCALE-LETKF T"}
multiline_names={"isabel":"Isabel P\n24","cesmt":"CESM T\n31","aramco":"Aramco\n1800","letkf":"SCALE-LETKF\nPRES","letkf_qv":"SCALE-LETKF\nQV","qmcpack":"QMCPACK\nOrbital 0","precip24":"Isabel PRECIP\n24","qmcpack144":"QMCPACK\nOrbital 144","aramco1800":"Aramco\n1800","vd01_31":"CESM VD01\n31","letkf_pres":"SCALE-LETKF\nPRES","letkf_t":"SCALE-LETKF\nT"}
row_names={**multiline_names,"precip24":"Isabel PRECIP 24","aramco1800":"Aramco 1800"}


def hide_outside_x_tick_labels(axis):
    lower,upper=axis.get_xlim()
    for location,label in zip(axis.get_xticks(),axis.get_xticklabels()):
        if location<lower or location>upper:label.set_visible(False)


def read_family(path,family):
    with path.open(newline="",encoding="utf-8") as source:
        reader=csv.DictReader(source)
        rows=list(reader)
    suffixes=("01","02","12") if family=="2d4r" else ("0","1","2")
    wide_required={"rel_eb",*(family+suffix+"_"+metric for suffix in suffixes for metric in ("BR","PSNR"))}
    if rows and wide_required.issubset(rows[0]):
        return {suffix:sorted((float(row[family+suffix+"_BR"]),float(row[family+suffix+"_PSNR"])) for row in rows) for suffix in suffixes},suffixes
    long_required={"family","rel_eb","axis","BR","PSNR"}
    if not rows or reader.fieldnames is None or not long_required.issubset(reader.fieldnames):
        raise ValueError(f"invalid predictor summary: {path}")
    rows=[row for row in rows if row["family"]==family]
    if {row["axis"] for row in rows}!=set(suffixes):
        raise ValueError(f"incomplete predictor axes for {family}: {path}")
    curves={suffix:sorted((float(row["BR"]),float(row["PSNR"])) for row in rows if row["axis"]==suffix) for suffix in suffixes}
    bounds={suffix:{float(row["rel_eb"]) for row in rows if row["axis"]==suffix} for suffix in suffixes}
    if len({tuple(sorted(values)) for values in bounds.values()})!=1 or any(len(values)<2 or len(curves[suffix])!=len(values) for suffix,values in bounds.items()):
        raise ValueError(f"inconsistent predictor error bounds for {family}: {path}")
    return curves,suffixes


def draw_panel(axis,directory,key,families,paperfig_layout=False):
    for family_index,family in enumerate(families):
        path=directory/f"{key}-{family}-best.csv"
        if not path.exists():
            path=directory/f"{key}-best.csv"
        curves,suffixes=read_family(path,family)
        for suffix,style in zip(suffixes,family_styles):
            points=curves[suffix]
            shifted=(sum(style[1])/2,style[1]) if family_index==0 else style
            axis.plot(*zip(*points),color=family_colors[family_index],linestyle=shifted,linewidth=.8,dash_capstyle="butt")
    axis.set_xscale("log")
    axis.xaxis.set_major_locator(LogLocator(base=10,numticks=3))
    axis.xaxis.set_minor_locator(NullLocator())
    axis.yaxis.set_major_locator(MaxNLocator(nbins=4))
    hide_outside_x_tick_labels(axis)
    if paperfig_layout:
        style_paper_axis(axis)
        axis.grid(True,color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
        axis.set_axisbelow(True)
    else:
        axis.set_box_aspect(1/PANEL_ASPECT)
        style_plot_axis(axis)


def family_legend_handles(families):
    handles=[]
    for family_index,family in enumerate(families):
        directions=("xy","xz","yz") if family=="2d4r" else ("x","y","z")
        for direction,style in zip(directions,family_styles):
            shifted=(sum(style[1])/2,style[1]) if family_index==0 else style
            handles.append(Line2D([],[],color=family_colors[family_index],linestyle=shifted,linewidth=.8,label=f"{family.upper()} {direction}"))
    return handles


def render_paperfig_row(spec,output_png):
    datasets=spec["datasets"]
    if len(datasets)!=3:
        raise ValueError("paperfig row rendering requires exactly three datasets")
    apply_paper_style()
    paper_spec=PaperFigureSpec.column()
    figure,axes=plt.subplots(1,3,figsize=paper_spec.size_in,dpi=paper_spec.dpi,sharey=True)
    for axis,(key,directory) in zip(axes,datasets):
        draw_panel(axis,directory,key,spec["families"],paperfig_layout=True)
    axes[0].set_ylabel("PSNR (dB)")
    layout_panel_row(figure,axes,panel_aspect_ratios(1,1,1),bottom_pt=52,panel_gap_pt=PANEL_GAP_WITHOUT_Y_DECORATION_PT,left_edge_gap_pt=3,right_edge_gap_pt=3)
    handles=family_legend_handles(spec["families"])
    order=(0,3,1,4,2,5)
    legend_above(axes[1],[handles[index] for index in order],[handles[index].get_label() for index in order],ncol=3,frameon=False,gap_pt=1,row_gap_pt=1,**legend_spacing_kwargs(8,column_gap_pt=5))
    captions=add_panel_captions(figure,axes,[f"({chr(97+index)}) {row_names[key]}" for index,(key,_) in enumerate(datasets)],gap_pt=2,source="ticks")
    add_shared_xlabel(figure,axes,"Bit rate (bits/value)",gap_pt=2,source_artists=captions)
    output_png.parent.mkdir(parents=True,exist_ok=True)
    save_paper_png_vertical_crop(figure,output_png,paper_spec,edge_gap_pt=3)
    plt.close(figure)


def render_paperfig_grid(spec,output_png):
    datasets=spec["datasets"]
    if len(datasets)!=6:
        raise ValueError("paperfig grid rendering requires exactly six datasets")
    apply_paper_style()
    paper_spec=PaperFigureSpec.column()
    figure,axes=plt.subplots(2,3,figsize=paper_spec.size_in,dpi=paper_spec.dpi,sharey="row",squeeze=False)
    for axis,(key,directory) in zip(axes.flat,datasets):
        draw_panel(axis,directory,key,spec["families"],paperfig_layout=True)
    layout_panel_grid(figure,axes,panel_aspect_ratios(1,1,1),bottom_pt=52,column_gap_pt=PANEL_GAP_WITHOUT_Y_DECORATION_PT,row_content_gap_pt=24,left_edge_gap_pt=14,right_edge_gap_pt=3)
    handles=family_legend_handles(spec["families"])
    order=(0,3,1,4,2,5)
    legend_above(axes[0,1],[handles[index] for index in order],[handles[index].get_label() for index in order],ncol=3,frameon=False,gap_pt=1,row_gap_pt=1,**legend_spacing_kwargs(8,column_gap_pt=5))
    labels=[f"({chr(97+index)}) {multiline_names[key]}" for index,(key,_) in enumerate(datasets)]
    add_panel_captions(figure,axes[0],labels[:3],gap_pt=2,source="ticks")
    bottom_captions=add_panel_captions(figure,axes[1],labels[3:],gap_pt=2,source="ticks")
    add_shared_xlabel(figure,axes[1],"Bit rate (bits/value)",gap_pt=2,source_artists=bottom_captions)
    figure.supylabel("PSNR (dB)",x=7/paper_spec.width_pt,fontsize=8)
    output_png.parent.mkdir(parents=True,exist_ok=True)
    save_paper_png_vertical_crop(figure,output_png,paper_spec,edge_gap_pt=3)
    plt.close(figure)


def render_figure(spec,output_pdf,output_png):
    datasets=spec["datasets"]
    columns=3
    rows=(len(datasets)+columns-1)//columns
    with plt.rc_context({"font.family":"Nimbus Roman","mathtext.fontset":"stix","font.size":8,"axes.labelsize":8,"xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":8,"pdf.fonttype":42,"ps.fonttype":42}):
        figure,axes=plt.subplots(rows,columns,figsize=(3.5,spec["height"]),sharey="row",squeeze=False)
        figure.subplots_adjust(left=.12,right=.99,bottom=spec["bottom"],top=.72 if rows==1 else .83,wspace=.22,hspace=.72)
        panel_axes=list(axes.flat)[:len(datasets)]
        for axis in list(axes.flat)[len(datasets):]:
            axis.set_visible(False)
        for axis,(key,directory) in zip(panel_axes,datasets):
            draw_panel(axis,directory,key,spec["families"])
        handles=family_legend_handles(spec["families"])
        order=(0,3,1,4,2,5)
        legend=figure.legend([handles[index] for index in order],[handles[index].get_label() for index in order],loc="upper center",bbox_to_anchor=(.5,1),ncol=3,frameon=False,handlelength=1.3,handletextpad=.35,columnspacing=.8,labelspacing=.12,borderaxespad=0)
        place_legend_above_axes(figure,legend,panel_axes)
        labels=[f"({chr(97+index)}) {multiline_names[key] if rows>1 or spec.get('multiline_labels') else names[key]}" for index,(key,_) in enumerate(datasets)]
        add_panel_footers(figure,panel_axes,labels,columns,"Bit rate (bits/value)",8,caption_gap_pt=spec["caption_gap"],xlabel_gap_pt=spec["xlabel_gap"],xlabel_x=spec["xlabel_x"])
        figure.supylabel("PSNR (dB)",x=.005,fontsize=8)
        output_pdf.parent.mkdir(parents=True,exist_ok=True)
        figure.savefig(output_pdf)
        figure.savefig(output_png,dpi=400)
        plt.close(figure)


def render_coefficient_figure(output_png):
    input_directory=project_root/"results/predictor-reference-count-common-final18-20261025"
    selected=("aramco1800","letkf_pres","qmcpack144")
    rows=[]
    for key in selected:
        with (input_directory/f"{key}-1d6r-coefficients.csv").open(newline="",encoding="utf-8") as source:
            for row in csv.DictReader(source):
                row["dataset"]=key
                row["coefficient_kind"]="quintic" if math.isclose(float(row["a"]),3/256,rel_tol=1e-12,abs_tol=1e-15) and math.isclose(float(row["b"]),-25/256,rel_tol=1e-12,abs_tol=1e-15) else "other"
                rows.append(row)
    coefficient_styles={"quintic":{"color":"#b2182b","linewidth":1.1,"linestyle":"-"},"other":{"color":".72","linewidth":.45,"linestyle":"-"}}
    apply_paper_style()
    paper_spec=PaperFigureSpec.column()
    figure,axes=plt.subplots(1,3,figsize=paper_spec.size_in,dpi=paper_spec.dpi,sharey=True)
    for axis,key in zip(axes,selected):
        dataset_rows=[row for row in rows if row["dataset"]==key]
        curves=defaultdict(list)
        for row in dataset_rows:
            curves[(row["a"],row["b"])].append(row)
        for curve in curves.values():
            points=sorted(((float(row["BR"]),float(row["PSNR"]),row["coefficient_kind"]) for row in curve))
            style=coefficient_styles["quintic" if points[0][2]=="quintic" else "other"]
            axis.plot([point[0] for point in points],[point[1] for point in points],marker="None",zorder=4 if points[0][2]=="quintic" else 1,**style)
        by_bound=defaultdict(list)
        for row in dataset_rows:
            by_bound[float(row["rel_eb"])].append(row)
        best=[max(bound_rows,key=lambda row:(float(row["score"]),float(row["PSNR"]),-float(row["BR"]))) for _,bound_rows in sorted(by_bound.items(),reverse=True)]
        axis.plot([float(row["BR"]) for row in best],[float(row["PSNR"]) for row in best],color=".1",linewidth=.85,linestyle=(0,(2.5,2.5)),dash_capstyle="butt",zorder=5)
        axis.set_xscale("log")
        axis.xaxis.set_major_locator(LogLocator(base=10,numticks=3))
        axis.xaxis.set_minor_locator(NullLocator())
        axis.yaxis.set_major_locator(MaxNLocator(nbins=4))
        hide_outside_x_tick_labels(axis)
        style_paper_axis(axis)
        axis.grid(True,color="#9e9e9e",linestyle="--",linewidth=.45,alpha=.55)
        axis.set_axisbelow(True)
    axes[0].set_ylabel("PSNR (dB)")
    layout_panel_row(figure,axes,panel_aspect_ratios(1,1,1),bottom_pt=52,panel_gap_pt=PANEL_GAP_WITHOUT_Y_DECORATION_PT,left_edge_gap_pt=3,right_edge_gap_pt=3)
    handles=[Line2D([],[],label="Fixed quintic",**coefficient_styles["quintic"]),Line2D([],[],label="Best per error bound",color=".1",linewidth=.85,linestyle=(0,(2.5,2.5))),Line2D([],[],label="Other coefficients",**coefficient_styles["other"])]
    legend_above(axes[1],handles=handles,ncol=3,frameon=False,gap_pt=1,row_gap_pt=1,**legend_spacing_kwargs(8,column_gap_pt=4))
    captions=add_panel_captions(figure,axes,["(a) Aramco\n1800","(b) SCALE-LETKF\nPRES","(c) QMCPACK\nOrbital 144"],gap_pt=2,source="ticks")
    add_shared_xlabel(figure,axes,"Bit rate (bits/value)",gap_pt=2,source_artists=captions)
    output_png.parent.mkdir(parents=True,exist_ok=True)
    save_paper_png_vertical_crop(figure,output_png,paper_spec,edge_gap_pt=3)
    plt.close(figure)


def specifications():
    legacy=project_root/"results/predictor-family-legacy-middle-21244405"
    main=project_root/"results/predictor-family-4r6r-middle-21250842-recovered"
    supplement=project_root/"results/predictor-family-4r6r-supplement-21274865-recovered"
    qmcpack=project_root/"results/predictor-family-4r6r-qmcpack-orbital0-20261011"
    return {
        "fig7":{"families":("1d4r","2d4r"),"datasets":[("isabel",legacy),("cldice",legacy),("aramco",legacy)],"output":project_root/"新论文/revised-fig/predictor-family-legacy-middle/iv-1d4r-vs-2d4r-legacy-middle","height":1.46,"bottom":.32,"caption_gap":.5,"xlabel_gap":3,"xlabel_x":.55},
        "fig7-final18":{"families":("1d4r","2d4r"),"datasets":[("precip24",project_root/"results/predictor-dimensionality-common-final18-20261024"),("qmcpack144",project_root/"results/predictor-dimensionality-common-final18-20261024"),("aramco1800",project_root/"results/predictor-dimensionality-common-final18-20261024")],"output":project_root/"新论文/revised-fig/predictor-family-common-final18/iv-1d4r-vs-2d4r-common-targets","paperfig":True},
        "fig8":{"families":("1d4r","1d6r"),"datasets":[("isabel",main),("cesmt",main),("letkf_qv",supplement),("aramco",main),("letkf",supplement),("qmcpack",qmcpack)],"output":project_root/"新论文/revised-fig/predictor-family-4r6r-middle/iv-1d4r-vs-1d6r-legacy-middle","height":2.8,"bottom":.24,"caption_gap":1,"xlabel_gap":3,"xlabel_x":.55},
        "fig8-final18":{"families":("1d4r","1d6r"),"datasets":[("precip24",project_root/"results/predictor-reference-count-common-final18-20261025"),("vd01_31",project_root/"results/predictor-reference-count-common-final18-20261025"),("letkf_t",project_root/"results/predictor-reference-count-common-final18-20261025"),("aramco1800",project_root/"results/predictor-reference-count-common-final18-20261025"),("letkf_pres",project_root/"results/predictor-reference-count-common-final18-20261025"),("qmcpack144",project_root/"results/predictor-reference-count-common-final18-20261025")],"output":project_root/"新论文/revised-fig/predictor-reference-count-common-final18/iv-1d4r-vs-1d6r-common-targets","paperfig":True},
    }


def main():
    parser=argparse.ArgumentParser(description="Plot predictor-family RD comparisons")
    parser.add_argument("figures",nargs="*")
    arguments=parser.parse_args()
    specs=specifications()
    figures=arguments.figures or ("fig7-final18",)
    unknown=set(figures)-set(specs)-{"fig9"}
    if unknown:
        parser.error(f"unknown figures: {', '.join(sorted(unknown))}")
    for name in figures:
        if name=="fig9":
            output=project_root/"新论文/revised-fig/1d6r-coefficients-common-final18/iv-1d6r-coefficients-common-targets"
            render_coefficient_figure(output.with_suffix(".png"))
            print(f"wrote {output}.png")
            continue
        output=specs[name]["output"]
        if specs[name].get("paperfig"):
            renderer=render_paperfig_row if len(specs[name]["datasets"])==3 else render_paperfig_grid
            renderer(specs[name],output.with_suffix(".png"))
            print(f"wrote {output}.png")
        else:
            render_figure(specs[name],output.with_suffix(".pdf"),output.with_suffix(".png"))
            print(f"wrote {output}.pdf")


if __name__=="__main__":
    main()
