import pickle
import numpy as np
from sz3_record import sz3_record_c

rel_eb=1e-4
with open(f"sz3_record_{rel_eb:.0e}.pkl","rb") as f:
    sz3_record_list=pickle.load(f)
for i in range(len(sz3_record_list)):
    freq_sum=sz3_record_list[i].freq.sum()
    sz3_record_list[i].freq=sz3_record_list[i].freq/freq_sum

def l(f):
    return -np.log2(f**f)

def loss_func(param,f):
    