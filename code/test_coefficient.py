import pickle,os
import numpy as np
from typing import List
import zstandard as zstd
import matplotlib.pyplot as plt
from sz3_record import sz3_record_c
from quantize import quantize
from huffman import huffman_encode
from fit_f import f_c
from fit_l import l_c
from blockify import blockify

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
data=data[0:10,0:10,0:50]
data_shape=data.shape
cctx=zstd.ZstdCompressor()

with open(f"f/{data_name}_{rel_eb:.0e}.pkl","rb") as file:
    f:f_c=pickle.load(file)
with open(f"l/{data_name}_{rel_eb:.0e}.pkl","rb") as file:
    l:l_c=pickle.load(file)

def calc_pred(param,cur_data,pos):
    pred=param[0]*cur_data[0:-6:2]+param[1]*cur_data[2:-4:2]+param[2]*cur_data[4:-2:2]+param[3]*cur_data[6::2]
    pred+=param[4]*pos[1::2]+param[5]
    return pred

def loss(param,cur_data,pos):
    return l.l_single(f.f((calc_pred(param,cur_data,pos)-cur_data[3:-2:2])/(2*abs_eb))).sum()

qb=np.zeros((data_shape[0],data_shape[1],data_shape[2]//2),dtype=np.int32)
param=[0,0.5,0.5,0,0,0]
bs_len_baseline=0
pos=(2*np.arange(data_shape[2])/(2*data_shape[2]-1)-1)
for i0 in range(data_shape[0]):
    for i1 in range(data_shape[1]):
        cur_data=data[i0,i1]
        cur_data=np.pad(cur_data,[[2,3]],mode="edge")
        pred=calc_pred(param,cur_data,pos)
        diff=cur_data[3:-2:2]-pred
        quantize(diff,qb[i0,i1],abs_eb)
bs_huffman=huffman_encode(qb.flatten())
bs_zstd=cctx.compress(bs_huffman)
bs_len_baseline=len(bs_zstd)
print(f"baseline CR={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/bs_len_baseline}")

delta=abs_eb/10
bs_len_pred=0
for i0 in range(data_shape[0]):
    for i1 in range(data_shape[1]):
        print(f"i0={i0},i1={i1}")
        cur_data=data[i0,i1]
        cur_data=np.pad(cur_data,[[2,3]],mode="edge")
        param=[0,0.5,0.5,0,0,0]
        D_array=np.zeros(len(param),dtype=np.float32)
        H_array=np.zeros((len(param),len(param)),dtype=np.float32)
        for epid in range(100):
            l0=loss(param,cur_data,pos)
            # print(f"l0={l0}")
            for i in range(len(param)):
                param[i]+=delta
                l1=loss(param,cur_data,pos)
                param[i]-=2*delta
                l2=loss(param,cur_data,pos)
                param[i]+=delta
                D_array[i]=(l1-l2)/(2*delta)
                H_array[i,i]=(l1-2*l0+l2)/(delta*delta)
            for i in range(len(param)):
                for j in range(i+1,len(param)):
                    param[i]+=delta
                    param[j]+=delta
                    l1=loss(param,cur_data,pos)
                    param[j]-=2*delta
                    l2=loss(param,cur_data,pos)
                    param[i]-=2*delta
                    param[j]+=2*delta
                    l3=loss(param,cur_data,pos)
                    param[j]-=2*delta
                    l4=loss(param,cur_data,pos)
                    param[i]+=delta
                    param[j]+=delta
                    H_array[i,j]=(l1-l2-l3+l4)/(4*delta*delta)
                    H_array[j,i]=H_array[i,j]
            H_array+=np.eye(len(param))*1e4
            try:
                d_param=np.linalg.solve(H_array,D_array)
            except np.linalg.LinAlgError:
                print("H_array不可逆")
                exit()
            alpha=1
            while True:
                new_param=np.array(param)-alpha*d_param
                l1=loss(new_param,cur_data,pos)
                if l1<l0:
                    param=new_param
                    break
                alpha*=0.5
                if alpha<1e-3:
                    break
            if alpha<1e-3:
                break
        pred=calc_pred(param,cur_data,pos)
        diff=cur_data[3:-2:2]-pred
        bs_len_pred+=l.l_single(f.f(diff/(2*abs_eb))).sum()
        quantize(diff,qb[i0,i1],abs_eb)
        # input()
bs_huffman=huffman_encode(qb.flatten())
bs_zstd=cctx.compress(bs_huffman)

print(f"bs_len_baseline={bs_len_baseline}")
print(f"bs_len_pred={bs_len_pred}")
print(f"bs_len={len(bs_zstd)}")
print(f"CR_baseline={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/bs_len_baseline}")
print(f"CR_pred={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/bs_len_pred}")
print(f"CR={data_shape[0]*data_shape[1]*(data_shape[2]//2)*32/len(bs_zstd)}")