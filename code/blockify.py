import numpy as np
from typing import Generator,Tuple

def blockify(cur_data:np.ndarray,tgt_data:np.ndarray,padding:int=0)->Generator[Tuple[Tuple[int],np.ndarray,np.ndarray],None,None]:
    temp_cur_data=np.pad(cur_data,[[0,0]]*2+[[padding,padding]],mode="edge")
    pos=np.zeros((4,16,16,16),dtype=np.float32)
    pos[0,:,:,:]=(2*np.arange(16)/15-1).reshape(16,1,1).repeat(16,axis=1).repeat(16,axis=2)
    pos[1,:,:,:]=(2*np.arange(16)/15-1).reshape(1,16,1).repeat(16,axis=0).repeat(16,axis=2)
    pos[2,:,:,:]=(2*np.arange(16)/15-1).reshape(1,1,16).repeat(16,axis=0).repeat(16,axis=1)
    pos[3,:,:,:]=1
    for i0 in range(0,tgt_data.shape[0],16):
        for i1 in range(0,tgt_data.shape[1],16):
            for i2 in range(0,tgt_data.shape[2],16):
                cur_block=temp_cur_data[i0:i0+16,i1:i1+16,i2:i2+16+2*padding]
                tgt_block=tgt_data[i0:i0+16,i1:i1+16,i2:i2+16]
                yield (i0,i1,i2),cur_block,tgt_block,pos[:,0:tgt_block.shape[0],0:tgt_block.shape[1],0:tgt_block.shape[2]]