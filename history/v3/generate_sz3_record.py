#需要求出qb的频率f(qb)，以及一个频率为f的qb的编码后字长l(f)

import pickle
import numpy as np
from typing import List
import zstandard as zstd
from sz3_record import sz3_record_c
from quantize import quantize
from huffman import huffman_encode

src_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin"
data_shape=(100,500,500)
rel_eb=1e-4
compressor_name="ASTZ2"
# compressor_name="SZ3"

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
with open(f"sz3_record_{rel_eb:.0e}.pkl","wb") as f:
    pickle.dump(sz3_record_list,f)
exit()
    
# qb=np.zeros((data_shape[0],data_shape[1],data_shape[2]//2),dtype=np.int32)
# sigma2_sum=0
# for i0 in range(data_shape[0]):
#     for i1 in range(data_shape[1]):
#         f=data[i0,i1]
#         A=np.stack([x**4,x**3,x**2,x,np.ones_like(x)],axis=1)
#         param,residuals,rank,s=np.linalg.lstsq(A,f.T,rcond=None)
#         f0=A@param
#         g=f-f0
#         g=np.concatenate((g,np.zeros((1))),axis=0)
#         if compressor_name=="ASTZ2":
#             K=np.cov(np.stack([g[0:-2:2],g[1::2],g[2::2]],axis=1).T)
#             K11=K[0::2,0::2]
#             K12=K[0::2,1:2]
#             K22=K[1:2,1:2]
#             z1=np.stack([g[0:-2:2],g[2::2]],axis=1).T
#             u=(K12.T@np.linalg.inv(K11)@z1)[0]
#             sigma2=(K22-K12.T@np.linalg.inv(K11)@K12).item()
#             if sigma2<0:
#                 print(f"sigma2<0, i0={i0}, i1={i1}")
#             sigma2_sum+=sigma2
#         if compressor_name=="SZ3":
#             u=(g[0:-2:2]+g[2::2])/2
#         diff=g[1::2]-u
#         quantize(diff,qb[i0,i1],abs_eb)
#         D+=np.sum((diff-qb[i0,i1]*2*abs_eb)**2)
# if compressor_name=="ASTZ2":
#     sigma2_sum/=(data_shape[0]*data_shape[1])
#     print(f"sigma2_sum: {sigma2_sum}")
#     D/=(data_shape[0]*data_shape[1]*data_shape[2])
#     print(f"D: {D}")
#     D=(abs_eb**2)
#     min_bitrate=max(0,0.5*np.log2(1+sigma2_sum/D))
#     if min_bitrate==0:
#         max_CR=np.inf
#     else:
#         max_CR=32/min_bitrate
#     print(f"max_CR: {max_CR}")
# with open("qb.bin","wb") as f:
#     f.write((qb+32768).tobytes())

#012
#SZ3:           280.622986
#ASTZ2:         142.077347
#ASTZ2_pred:    13.48989258

#102
#SZ3:           289.742523
#ASTZ2:         147.419998
#ASTZ2_pred:    13.48989258

#021
#SZ3:           320.463531
#ASTZ2:         242.130753
#ASTZ2_pred:    14.04884862

#201:
#ASTZ2:         251.414200
#SZ3:           333.874207
#ASTZ2_pred:    14.04884862

#210:
#SZ3:           396.127472
#ASTZ2:         383.662140
#ASTZ2_pred:    46.40483739

#120:
#SZ3:           430.752258
#ASTZ2:         386.712555
#ASTZ2_pred:    46.40483739