import numpy as np

def quantize(delta:np.ndarray,qb:np.ndarray,abs_eb:float)->None:
    mask_positive=(delta>=0)
    mask_negative=(~mask_positive)
    temp_qb=np.zeros_like(delta,dtype=np.int32)
    temp_qb[mask_positive]=np.ceil((delta[mask_positive]-abs_eb)/(2*abs_eb)).astype(np.int32)
    temp_qb[mask_negative]=np.floor((delta[mask_negative]+abs_eb)/(2*abs_eb)).astype(np.int32)
    qb[:]=temp_qb[:]