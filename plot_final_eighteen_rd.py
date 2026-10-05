import argparse,csv,math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator,MaxNLocator,NullLocator

project_root=Path(__file__).resolve().parent
datasets=(
    ("QMCPACK orbital 0","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/QMCPACK/asz_qmcpack_orbital0.f32","final_eighteen_qmcpack_orbital0.csv","final_eighteen_qmcpack_orbital0.csv"),
    ("QMCPACK orbital 287","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/QMCPACK/asz_qmcpack_orbital287.f32","final_eighteen_qmcpack_orbital287.csv","final_eighteen_qmcpack_orbital287.csv"),
    ("APS Kaz","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/APS_Kaz/xpcs-998x128x128.bin.f32","final_eighteen_refresh_aps_kaz.csv","final_eight_aps_kaz.csv"),
    ("Isabel Pf24","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/P/Pf24.bin","final_eighteen_refresh_isabel_pf24.csv","final_eight_middle_isabel_pf24.csv"),
    ("Isabel TC","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/TC/TCf01.bin","final_eighteen_isabel_tc.csv","final_eighteen_isabel_tc.csv"),
    ("Isabel QVAPOR","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/QVAPOR/QVAPORf01.bin","final_eighteen_isabel_qvapor.csv","final_eighteen_isabel_qvapor.csv"),
    ("Miranda pressure","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/Miranda/pressure.f32.dat","final_eighteen_refresh_miranda_pressure.csv","candidate_miranda_pressure.csv"),
    ("Aramco 1800","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/aramco/aramco-snapshot-1800.f32","final_eighteen_refresh_aramco_1800.csv","final_eight_aramco.csv"),
    ("LETKF PRES","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/SCALE_LETKF/PRES-98x1200x1200.dat","final_eighteen_refresh_letkf_pres.csv","final_eight_letkf.csv"),
    ("LETKF QV log10","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/SCALE_LETKF/log10/QV-98x1200x1200.log10.f32","final_eighteen_refresh_letkf_qv_log10.csv","candidate_letkf_qv_log10.csv"),
    ("CESM CLDICE t31","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/cesm-atm-1.5TB/31/CLDICE_26x1800x3600.dat","final_eighteen_refresh_cldice_t31.csv","final_eight_middle_cldice_t31.csv"),
    ("CESM T t31","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/cesm-atm-1.5TB/31/T_26x1800x3600.dat","final_eighteen_refresh_cesm_t31.csv","candidate_cesm_t31.csv"),
    ("CESM Q t31","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/cesm-atm-1.5TB/31/Q_26x1800x3600.dat","final_eighteen_cesm_q_t31.csv","final_eighteen_cesm_q_t31.csv"),
    ("EXAFEL","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/EXAFEL/SDRBENCH-EXAFEL-data-130x1480x1552.f32","final_eighteen_refresh_exafel_3d.csv","candidate_exafel_3d.csv"),
    ("APS CSSI L0471","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/APS_DYS/9-ID_CSSI_data/benchmarkdata/Avg_L0471_Double_exp_elong_siemens_1p00sampit_0p05inplane_patch1_of1_part1_001.h5.f32","final_eighteen_aps_cssi_l0471.csv","final_eighteen_aps_cssi_l0471.csv"),
    ("APSU004","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/APS_DYS/xpcs_datasets/APSU_TestData_004/APSU_TestData_004.h5.f32","final_eighteen_refresh_apsu004.csv","final_eight_apsu.csv"),
    ("E017","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/APS_DYS/xpcs_datasets/E017_CeramicGlass_L2Mq0_060C_att00_001/E017_CeramicGlass_L2Mq0_060C_att00_001_001.h5.f32","final_eighteen_refresh_e017.csv","final_eight_e017.csv"),
    ("APSU006","/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/APS_DYS/xpcs_datasets/APSU_TestData_006/APSU_TestData_006.h5.f32","apsu006.csv","apsu006.csv"),
)
methods=("asz","sz3","qoz")
styles={
    "asz":{"label":"ASZ","color":"#000000","linestyle":"-","marker":"o"},
    "sz3":{"label":"SZ3","color":"#d62728","linestyle":"--","marker":"s"},
    "qoz":{"label":"QoZ","color":"#e6a700","linestyle":"-.","marker":"^"},
}


def read_method(path,method):
    with open(path,newline="",encoding="utf-8") as input_file:
        points=[(float(row["BR"]),float(row["PSNR"])) for row in csv.DictReader(input_file) if row["METHOD"]==method]
    if len(points)!=5:
        raise ValueError(f"{path}的{method}应有5个RD点，实际有{len(points)}个")
    return sorted(points)


def read_curves(result_directory,asz_filename,baseline_filename):
    return {
        "asz":read_method(result_directory/asz_filename,"asz"),
        "sz3":read_method(result_directory/baseline_filename,"sz3"),
        "qoz":read_method(result_directory/baseline_filename,"qoz"),
    }


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


def format_size(byte_count):
    units=("B","KiB","MiB","GiB")
    value=float(byte_count)
    unit=units[0]
    for unit in units:
        if value<1024 or unit==units[-1]:
            break
        value/=1024
    return f"{value:.2f} {unit}"


def draw_dataset(axis,title,file_size,curves,index):
    all_points=[]
    for method in methods:
        points=curves[method]
        all_points.extend(points)
        style=styles[method]
        frontier=pareto_frontier(points)
        axis.plot([point[0] for point in frontier],[point[1] for point in frontier],color=style["color"],linestyle=style["linestyle"],linewidth=1.7)
        axis.plot([point[0] for point in points],[point[1] for point in points],color=style["color"],linestyle="None",marker=style["marker"],markersize=4.2,markeredgewidth=0.9,markerfacecolor="white")
    min_bitrate=min(point[0] for point in all_points)
    max_bitrate=max(point[0] for point in all_points)
    min_psnr=min(point[1] for point in all_points)
    max_psnr=max(point[1] for point in all_points)
    psnr_padding=max(1.5,(max_psnr-min_psnr)*0.04)
    axis.set_xscale("log")
    axis.set_xlim(min_bitrate*.8,max_bitrate*1.15)
    axis.set_ylim(math.floor((min_psnr-psnr_padding)/5)*5,math.ceil((max_psnr+psnr_padding)/5)*5)
    axis.set_title(f"({chr(ord('a')+index)}) {title}\n{format_size(file_size)}",pad=4)
    axis.grid(True,color="#bdbdbd",linestyle="--",linewidth=0.55,alpha=0.55)
    axis.xaxis.set_major_locator(LogLocator(base=10,numticks=5))
    axis.xaxis.set_minor_locator(NullLocator())
    axis.yaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=3))
    axis.tick_params(direction="in",top=True,right=True,length=3)
    for spine in axis.spines.values():
        spine.set_linewidth(0.85)


def main():
    parser=argparse.ArgumentParser(description="按文件大小绘制最终18数据的3x6对数bitrate RD曲线")
    parser.add_argument("--result-directory",type=Path,default=project_root/"results")
    parser.add_argument("--output-pdf",type=Path,default=project_root/"新论文/figs/5/rate-distortion-eighteen-log.pdf")
    parser.add_argument("--output-png",type=Path,default=project_root/"新论文/figs/5/rate-distortion-eighteen-log.png")
    parser.add_argument("--dpi",type=int,default=300)
    arguments=parser.parse_args()

    plt.rcParams.update({"font.family":"sans-serif","font.size":8.5,"axes.titlesize":9.5,"axes.labelsize":10,"xtick.labelsize":7.5,"ytick.labelsize":7.5,"legend.fontsize":10,"pdf.fonttype":42,"ps.fonttype":42})
    ordered=sorted(datasets,key=lambda item:(Path(item[1]).stat().st_size,item[0]))
    figure,axes=plt.subplots(3,6,figsize=(17.5,8.2))
    for index,((title,data_path,asz_filename,baseline_filename),axis) in enumerate(zip(ordered,axes.flat)):
        curves=read_curves(arguments.result_directory,asz_filename,baseline_filename)
        draw_dataset(axis,title,Path(data_path).stat().st_size,curves,index)
        if index//6==2:
            axis.set_xlabel("Bitrate (bits/value)")
        if index%6==0:
            axis.set_ylabel("PSNR (dB)")
    handles=[plt.Line2D([],[],color=styles[method]["color"],linestyle=styles[method]["linestyle"],marker=styles[method]["marker"],markerfacecolor="white",linewidth=1.8,markersize=5,label=styles[method]["label"]) for method in methods]
    figure.legend(handles=handles,loc="upper center",ncol=3,frameon=False,bbox_to_anchor=(0.5,0.997),handlelength=3,columnspacing=2.5)
    figure.subplots_adjust(left=0.05,right=0.995,bottom=0.075,top=0.9,wspace=0.28,hspace=0.47)
    arguments.output_pdf.parent.mkdir(parents=True,exist_ok=True)
    figure.savefig(arguments.output_pdf,bbox_inches="tight")
    figure.savefig(arguments.output_png,dpi=arguments.dpi,bbox_inches="tight")
    plt.close(figure)
    print("排序：")
    for index,(title,data_path,_,_) in enumerate(ordered,1):
        print(f"{index:2d}. {title}: {format_size(Path(data_path).stat().st_size)}")
    print(f"写入：{arguments.output_pdf}")
    print(f"写入：{arguments.output_png}")


if __name__=="__main__":
    main()
