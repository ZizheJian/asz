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

cur_data=data[0:8,0:8,0:9]

x=0.5*(cur_data[:,:,2::2]-cur_data[:,:,0:-2:2])
y=cur_data[:,:,1::2]-0.5*(cur_data[:,:,0:-2:2]+cur_data[:,:,2::2])
plt.scatter(x.flatten(),y.flatten(),s=1)
# plt.xlim(-0.005,0.005)
# plt.ylim(-0.0025,0.0025)
plt.tight_layout()
plt.savefig(f"{data_name}_{rel_eb:.0e}_scatter.png",dpi=300)