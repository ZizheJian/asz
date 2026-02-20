import pickle
import numpy as np
from sz3_record import sz3_record_c
import matplotlib.pyplot as plt
import matplotlib.cm as cm

rel_eb=1e-4

with open(f"sz3_record_{rel_eb:.0e}.pkl","rb") as f:
    sz3_record_list=pickle.load(f)

cmap=cm.get_cmap("viridis",len(sz3_record_list))
plt.figure(figsize=(10,5))
non_zero_indices=np.nonzero(sz3_record_list[0].freq)[0]
x_min=non_zero_indices[0]-32768
x_max=non_zero_indices[-1]-32768
x=np.arange(x_min,x_max+1)
for i,sz3_record in enumerate(sz3_record_list):
    plt.plot(x,sz3_record.freq[x_min+32768:x_max+32769],color=cmap(i),alpha=0.5)
plt.xlabel("qb")
plt.ylabel("freq")
plt.yscale("log")
plt.tight_layout()
plt.savefig(f"sz3_record_freq_{rel_eb:.0e}.png",dpi=300)

plt.figure(figsize=(5,5))
plt.plot(np.arange(-20,21),[sz3_record.cr for sz3_record in sz3_record_list])
plt.xlabel("abs_eb_power")
plt.ylabel("cr")
plt.tight_layout()
plt.savefig(f"sz3_record_cr_{rel_eb:.0e}.png",dpi=300)