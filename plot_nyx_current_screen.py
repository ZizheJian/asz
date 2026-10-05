import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from plot_final_eighteen_rd import draw_dataset,methods,styles
from promote_asz_tuning_results import compare_to_envelope

project_root=Path(__file__).resolve().parent
datasets=(
    ("Nyx baryon density",project_root/"results/nyx_current_baryon_density_1024.csv",Path("/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/Nyx-bigdata/NVB_C009_l20n1024_S12345T632_z42/baryon_density.f32")),
    ("Nyx baryon density log10",project_root/"results/nyx_current_baryon_density_log10_512.csv",Path("/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/Nyx-bigdata/SDRBench-512-log/SDRBENCH-EXASKY-NYX-512x512x512_log/baryon_density_log10.f32")),
)


def read_curves(path):
    with open(path,newline="",encoding="utf-8") as input_file:
        rows=list(csv.DictReader(input_file))
    curves={method:sorted((float(row["BR"]),float(row["PSNR"])) for row in rows if row["METHOD"]==method) for method in methods}
    for method in methods:
        if len(curves[method])!=5:
            raise ValueError(f"{path}的{method}应有5个点，实际有{len(curves[method])}个")
    return curves


def as_psnr_bitrate(curve):
    return [(psnr,bitrate) for bitrate,psnr in curve]


def main():
    plt.rcParams.update({"font.family":"sans-serif","font.size":10,"axes.titlesize":11,"axes.labelsize":11,"legend.fontsize":10,"pdf.fonttype":42,"ps.fonttype":42})
    figure,axes=plt.subplots(1,2,figsize=(10,3.8))
    for index,((title,result_path,data_path),axis) in enumerate(zip(datasets,axes)):
        curves=read_curves(result_path)
        draw_dataset(axis,title,data_path.stat().st_size,curves,index)
        axis.set_xlabel("Bitrate (bits/value)")
        axis.set_ylabel("PSNR (dB)")
        for baseline in ("sz3","qoz"):
            ratio,winning_fraction,interval=compare_to_envelope(as_psnr_bitrate(curves["asz"]),[as_psnr_bitrate(curves[baseline])])
            print(f"{title} vs {styles[baseline]['label']}: saving={100*(1-ratio):+.3f}%,win={100*winning_fraction:.1f}%,common_psnr=[{interval[0]:.3f},{interval[1]:.3f}]")
        ratio,winning_fraction,interval=compare_to_envelope(as_psnr_bitrate(curves["asz"]),[as_psnr_bitrate(curves["sz3"]),as_psnr_bitrate(curves["qoz"])])
        print(f"{title} vs best: saving={100*(1-ratio):+.3f}%,win={100*winning_fraction:.1f}%,common_psnr=[{interval[0]:.3f},{interval[1]:.3f}]")
    handles=[plt.Line2D([],[],color=styles[method]["color"],linestyle=styles[method]["linestyle"],marker=styles[method]["marker"],markerfacecolor="white",linewidth=1.8,markersize=5,label=styles[method]["label"]) for method in methods]
    figure.legend(handles=handles,loc="upper center",ncol=3,frameon=False,bbox_to_anchor=(.5,1.01))
    figure.subplots_adjust(left=.08,right=.99,bottom=.14,top=.78,wspace=.24)
    output=project_root/"新论文/figs/5/nyx-current-screen-rd"
    figure.savefig(output.with_suffix(".pdf"),bbox_inches="tight")
    figure.savefig(output.with_suffix(".png"),dpi=300,bbox_inches="tight")
    plt.close(figure)
    print(f"写入：{output.with_suffix('.pdf')}")
    print(f"写入：{output.with_suffix('.png')}")


if __name__=="__main__":
    main()
