import argparse,csv,math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

project_root=Path(__file__).resolve().parent
datasets=(
    ("APS-Kaz","final_eight_aps_kaz.csv","aps_kaz"),
    ("Aramco","final_eight_aramco.csv","aramco"),
    ("CLDICE","final_eight_cldice.csv","cldice"),
    ("Isabel Pf01","final_eight_isabel.csv","isabel_pf01"),
    ("LETKF PRES","final_eight_letkf.csv","letkf_pres"),
    ("VideoLLaVA","final_eight_videollava.csv","videollava"),
    ("E017","final_eight_e017.csv","e017"),
    ("APSU004","final_eight_apsu.csv","apsu004"),
)
methods=("asz","sz3","qoz")
styles={
    "asz":{"label":"ASZ","color":"#000000","linestyle":"-","marker":"o"},
    "sz3":{"label":"SZ3","color":"#e41a1c","linestyle":"--","marker":"s"},
    "qoz":{"label":"QoZ","color":"#e6ab02","linestyle":"-.","marker":"^"},
}

def read_curves(path):
    curves={method:[] for method in methods}
    with open(path,newline="",encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            method=row["METHOD"]
            if method in curves:
                curves[method].append((float(row["BR"]),float(row["PSNR"])))
    for method,points in curves.items():
        if len(points)!=5:
            raise ValueError(f"{path}的{method}应有5个RD点，实际有{len(points)}个")
        points.sort()
    return curves

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

def draw_dataset(ax,title,curves,title_prefix=""):
    all_points=[]
    for method in methods:
        points=curves[method]
        all_points.extend(points)
        style=styles[method]
        frontier=pareto_frontier(points)
        ax.plot([point[0] for point in frontier],[point[1] for point in frontier],label=style["label"],color=style["color"],linestyle=style["linestyle"],linewidth=2.1)
        ax.plot([point[0] for point in points],[point[1] for point in points],color=style["color"],linestyle="None",marker=style["marker"],markersize=5.5,markeredgewidth=1.0,markerfacecolor="white")
    max_bitrate=max(point[0] for point in all_points)
    min_psnr=min(point[1] for point in all_points)
    max_psnr=max(point[1] for point in all_points)
    psnr_padding=max(2.0,(max_psnr-min_psnr)*0.04)
    ax.set_xlim(0,max_bitrate*1.05)
    ax.set_ylim(math.floor((min_psnr-psnr_padding)/5)*5,math.ceil((max_psnr+psnr_padding)/5)*5)
    ax.set_title(f"{title_prefix}{title}",pad=7)
    ax.grid(True,color="#bdbdbd",linestyle="--",linewidth=0.7,alpha=0.55)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=3))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=4))
    ax.tick_params(direction="in",top=True,right=True)
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)

def save_individuals(curves_by_dataset,output_directory,dpi):
    output_directory.mkdir(parents=True,exist_ok=True)
    for title,_,stem in datasets:
        figure,axis=plt.subplots(figsize=(4.2,3.2))
        draw_dataset(axis,title,curves_by_dataset[title])
        axis.set_xlabel("Bitrate (bits/value)")
        axis.set_ylabel("PSNR (dB)")
        axis.legend(frameon=False,fontsize=9,loc="best")
        figure.tight_layout(pad=0.5)
        figure.savefig(output_directory/f"{stem}.pdf",bbox_inches="tight")
        figure.savefig(output_directory/f"{stem}.png",dpi=dpi,bbox_inches="tight")
        plt.close(figure)

def save_overview(curves_by_dataset,pdf_path,png_path,dpi):
    figure,axes=plt.subplots(2,4,figsize=(13.2,6.2))
    for index,((title,_,_),axis) in enumerate(zip(datasets,axes.flat)):
        draw_dataset(axis,title,curves_by_dataset[title],f"({chr(ord('a')+index)}) ")
        if index//4==1:
            axis.set_xlabel("Bitrate (bits/value)")
        if index%4==0:
            axis.set_ylabel("PSNR (dB)")
    handles=[plt.Line2D([],[],color=styles[method]["color"],linestyle=styles[method]["linestyle"],marker=styles[method]["marker"],markerfacecolor="white",linewidth=2.1,markersize=6,label=styles[method]["label"]) for method in methods]
    figure.legend(handles=handles,loc="upper center",ncol=3,frameon=False,bbox_to_anchor=(0.5,0.995),handlelength=3.0,columnspacing=2.5)
    figure.subplots_adjust(left=0.065,right=0.99,bottom=0.095,top=0.885,wspace=0.29,hspace=0.34)
    pdf_path.parent.mkdir(parents=True,exist_ok=True)
    figure.savefig(pdf_path,bbox_inches="tight")
    figure.savefig(png_path,dpi=dpi,bbox_inches="tight")
    plt.close(figure)

def main():
    parser=argparse.ArgumentParser(description="绘制最终八数据的ASZ、SZ3和QoZ RD曲线")
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--output-directory",type=Path,default=project_root/"新论文/figs/5/rd-final-eight")
    parser.add_argument("--overview-pdf",type=Path,default=project_root/"新论文/figs/5/rate-distortion-eight.pdf")
    parser.add_argument("--overview-png",type=Path,default=project_root/"新论文/figs/5/rate-distortion-eight.png")
    parser.add_argument("--dpi",type=int,default=300)
    arguments=parser.parse_args()

    plt.rcParams.update({"font.family":"sans-serif","font.size":11,"axes.titlesize":12,"axes.labelsize":11,"xtick.labelsize":9,"ytick.labelsize":9,"legend.fontsize":12,"pdf.fonttype":42,"ps.fonttype":42})
    curves_by_dataset={title:read_curves(arguments.result_directory/filename) for title,filename,_ in datasets}
    save_individuals(curves_by_dataset,arguments.output_directory,arguments.dpi)
    save_overview(curves_by_dataset,arguments.overview_pdf,arguments.overview_png,arguments.dpi)
    print(f"写入8张独立RD图：{arguments.output_directory}")
    print(f"写入总览图：{arguments.overview_pdf}")
    print(f"写入总览预览：{arguments.overview_png}")

if __name__=="__main__":
    main()
