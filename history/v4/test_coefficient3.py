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
cctx=zstd.ZstdCompressor()

with open(f"f/{data_name}_{rel_eb:.0e}.pkl","rb") as file:
    f:f_c=pickle.load(file)
with open(f"l/{data_name}_{rel_eb:.0e}.pkl","rb") as file:
    l:l_c=pickle.load(file)

qb=np.zeros((data_shape[0],data_shape[1],data_shape[2]//2),dtype=np.int32)
total_l=0
for i0 in range(data_shape[0]):
    print(f"i0={i0}")
    for i1 in range(data_shape[1]):
        cur_data=data[i0,i1]
        if cur_data.shape[0]%2==0:
            cur_data=np.concatenate((cur_data,np.ones((1))*cur_data[-1]),axis=0)
        best_cur_l=np.inf
        best_coeff1=0.5
        for coeff1 in np.arange(0.4,0.61,0.01):
            pred_data=coeff1*cur_data[0:-2:2]+(1-coeff1)*cur_data[2::2]
            diff=cur_data[1::2]-pred_data
            # cur_l=l.l_single(f.f(diff/(2*abs_eb))).sum()
            quantize(diff,qb[i0,i1],abs_eb)
            bs_huffman=huffman_encode(qb[i0,i1])
            bs_zstd=cctx.compress(bs_huffman)
            if len(bs_zstd)<best_cur_l:
                best_cur_l=len(bs_zstd)
                best_coeff1=coeff1
            # print(f"coeff1={coeff1}, cur_l={cur_l}, bs_zstd length={len(bs_zstd)}")
        # print(f"best_coeff1={best_coeff1}, best_l={best_cur_l}")
        pred_data=best_coeff1*cur_data[0:-2:2]+(1-best_coeff1)*cur_data[2::2]
        diff=cur_data[1::2]-pred_data
        quantize(diff,qb[i0,i1],abs_eb)
        total_l+=best_cur_l
        # input()
bs_huffman=huffman_encode(qb.flatten())
bs_zstd=cctx.compress(bs_huffman)
print(f"bs_zstd length={len(bs_zstd)}, cr={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/len(bs_zstd)}")
print(f"total_l={total_l}, cr={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/total_l}")