import numpy as np
import matplotlib.pyplot as plt

data_codename="LETKF_center"
with open(f"csv/results_cubic_prediction_{data_codename}.csv","r") as f:
    lines=f.readlines()
    lines=[line.strip().split(",") for line in lines]
    rel_eb_set=set()
    t2_set=set()
    val_name_list=[]
    for line in lines[1:]:
        rel_eb_set.add(float(line[0]))
        t2_set.add(float(line[1]))
    for item in lines[0][2:]:
        val_name_list.append(item)
    rel_eb_list=sorted(map(float,rel_eb_set),reverse=True)
    t2_list=sorted(t2_set)
    data=np.zeros((len(rel_eb_list),len(t2_list),len(val_name_list)))
    for line in lines[1:]:
        rel_eb=float(line[0])
        rel_eb_index=rel_eb_list.index(rel_eb)
        t2=float(line[1])
        t2_index=t2_list.index(t2)
        for i in range(2,len(line)):
            data[rel_eb_index][t2_index][i-2]=float(line[i])

br=data[:,:,0]
H1=data[:,:,1]
H2=data[:,:,2]
H3=data[:,:,3]
H4=data[:,:,4]
psnr=data[:,:,5]

def plot_curve(br,psnr,xlabel):
    plt.figure()
    for i in range(len(t2_list)):
        plt.plot(br[:,i],psnr[:,i],label=f"t2={t2_list[i]}")
    plt.xlabel(xlabel)
    plt.ylabel("PSNR")
    plt.legend()
    plt.savefig(f"{xlabel}-psnr.png")

plot_curve(br,psnr,"BR")
plot_curve(H1,psnr,"H1")
plot_curve(H2,psnr,"H2")
plot_curve(H3,psnr,"H3")
plot_curve(H4,psnr,"H4")

# 以origin的格式打印br-psnr到控制台
for rel_eb_id in range(len(rel_eb_list)):
    for t2_id in range(len(t2_list)):
        print(f"{br[rel_eb_id][t2_id]} {psnr[rel_eb_id][t2_id]} ",end="")
    print()