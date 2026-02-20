import pickle,os
import numpy as np
from typing import List
import zstandard as zstd
from sz3_record import sz3_record_c
from quantize import quantize
from huffman import huffman_encode
from fit_f import f_c
from fit_l import l_c
import matplotlib.pyplot as plt

src_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin"
data_shape=(100,500,500)
rel_eb=1e-4

data_name=os.path.basename(src_data_path)
data=np.fromfile(src_data_path,dtype=np.float32)
data=data.reshape(data_shape)
data_max=data.max()
data_min=data.min()
data=2*(data-data_min)/(data_max-data_min)-1
abs_eb=2*rel_eb

with open(f"f/{data_name}_{rel_eb:.0e}.pkl","rb") as file:
    f:f_c=pickle.load(file)
with open(f"l/{data_name}_{rel_eb:.0e}.pkl","rb") as file:
    l:l_c=pickle.load(file)

actual_cr=[]
predicted_cr=[]
for coeff1 in np.arange(0.49,0.51,0.001):
    l_total=0
    qb=np.zeros((data_shape[0],data_shape[1],data_shape[2]//2),dtype=np.int32)
    print(f"coeff1={coeff1}, coeff2={1-coeff1}")
    for i0 in range(data_shape[0]):
        for i1 in range(data_shape[1]):
            cur_data=data[i0,i1]
            if cur_data.shape[0]%2==0:
                cur_data=np.concatenate((cur_data,np.ones((1))*cur_data[-1]),axis=0)
            pred_data=coeff1*cur_data[0:-2:2]+(1-coeff1)*cur_data[2::2]
            diff=cur_data[1::2]-pred_data
            quantize(diff,qb[i0,i1],abs_eb)
            l_total+=l.l_single(f.f(diff/(2*abs_eb))).sum()
    freq=np.bincount(qb.flatten()+32768,minlength=65536).astype(np.int32)
    bs_huffman=huffman_encode(qb.flatten())
    # print(f"bs_huffman length={len(bs_huffman)}, cr={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/len(bs_huffman)}")
    cctx=zstd.ZstdCompressor()
    bs_zstd=cctx.compress(bs_huffman)
    print(f"bs_zstd length={len(bs_zstd)}, cr={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/len(bs_zstd)}")
    actual_cr.append(data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/len(bs_zstd))
    print(f"l_total={l_total}, cr={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/l_total}")
    predicted_cr.append(data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/l_total)

plt.figure(figsize=(5,5))
plt.plot(actual_cr,predicted_cr,"o")
plt.xlabel("Actual CR")
plt.ylabel("Predicted CR")
plt.tight_layout()
plt.savefig(f"{data_name}_{rel_eb:.0e}_pred_cr.png",dpi=300)