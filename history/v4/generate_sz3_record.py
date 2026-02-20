#需要求出qb的频率f(qb)，以及一个频率为f的qb的编码后字长l(f)

import pickle,os
import numpy as np
from typing import List
import zstandard as zstd
from sz3_record import sz3_record_c
from quantize import quantize
from huffman import huffman_encode

src_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin"
data_shape=(100,500,500)
rel_eb=1e-4

data_name=os.path.basename(src_data_path)
data=np.fromfile(src_data_path,dtype=np.float32)
data=data.reshape(data_shape)
data_max=data.max()
data_min=data.min()
data=2*(data-data_min)/(data_max-data_min)-1
abs_eb_list=[2*rel_eb*(1.03**i) for i in range(-20,21)]

########get sz3 baseline########
sz3_record_list:List[sz3_record_c]=[]
for abs_eb in abs_eb_list:
    print(f"abs_eb={abs_eb}")
    qb=np.zeros((data_shape[0],data_shape[1],data_shape[2]//2),dtype=np.int32)
    for i0 in range(data_shape[0]):
        for i1 in range(data_shape[1]):
            cur_data=data[i0,i1]
            if cur_data.shape[2]%2==0:
                cur_data=np.concatenate((cur_data,np.ones((1))*cur_data[-1]),axis=0)
            pred_data=0.5*(cur_data[0:-2:2]+cur_data[2::2])
            diff=cur_data[1::2]-pred_data
            quantize(diff,qb[i0,i1],abs_eb)
    freq=np.bincount(qb.flatten()+32768,minlength=65536).astype(np.int32)
    bs_huffman=huffman_encode(qb.flatten())
    print(f"bs_huffman length={len(bs_huffman)}, cr={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/len(bs_huffman)}")
    cctx=zstd.ZstdCompressor()
    bs_zstd=cctx.compress(bs_huffman)
    print(f"bs_zstd length={len(bs_zstd)}, cr={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/len(bs_zstd)}")
    sz3_record_list.append(sz3_record_c())
    sz3_record_list[-1].freq=freq
    sz3_record_list[-1].cr=data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/len(bs_zstd)
with open(f"sz3_record/{data_name}_{rel_eb:.0e}.pkl","wb") as file:
    pickle.dump(sz3_record_list,file)