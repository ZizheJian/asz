import numpy as np
from quantize import quantize

src_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin"
data_shape=(100,500,500)
rel_eb=1e-3
mode="ASTZ2"
# mode="SZ3"

data=np.fromfile(src_data_path,dtype=np.float32)
data=data.reshape(data_shape)
data_max=data.max()
data_min=data.min()
data=2*(data-data_min)/(data_max-data_min)-1
abs_eb=2*rel_eb

seq=(0,1,2)
data=data.transpose(seq)
data_shape=(data_shape[seq[0]],data_shape[seq[1]],data_shape[seq[2]])
D=0

qb=np.zeros((data_shape[0],data_shape[1],data_shape[2]//2),dtype=np.int32)
x=np.linspace(-1,1,data_shape[2])
sigma2_sum=0
for i0 in range(data_shape[0]):
    for i1 in range(data_shape[1]):
        f=data[i0,i1]
        A=np.stack([x**4,x**3,x**2,x,np.ones_like(x)],axis=1)
        param,residuals,rank,s=np.linalg.lstsq(A,f.T,rcond=None)
        f0=A@param
        g=f-f0
        g=np.concatenate((g,np.zeros((1))),axis=0)
        if mode=="ASTZ2":
            K=np.cov(np.stack([g[0:-2:2],g[1::2],g[2::2]],axis=1).T)
            K11=K[0::2,0::2]
            K12=K[0::2,1:2]
            K22=K[1:2,1:2]
            z1=np.stack([g[0:-2:2],g[2::2]],axis=1).T
            u=(K12.T@np.linalg.inv(K11)@z1)[0]
            sigma2=(K22-K12.T@np.linalg.inv(K11)@K12).item()
            if sigma2<0:
                print(f"sigma2<0, i0={i0}, i1={i1}")
            sigma2_sum+=sigma2
        if mode=="SZ3":
            u=(g[0:-2:2]+g[2::2])/2
        diff=g[1::2]-u
        quantize(diff,qb[i0,i1],abs_eb)
        D+=np.sum((diff-qb[i0,i1]*2*abs_eb)**2)
if mode=="ASTZ2":
    sigma2_sum/=(data_shape[0]*data_shape[1])
    print(f"sigma2_sum: {sigma2_sum}")
    D/=(data_shape[0]*data_shape[1]*data_shape[2])
    print(f"D: {D}")
    D=(abs_eb**2)
    min_bitrate=max(0,0.5*np.log2(1+sigma2_sum/D))
    if min_bitrate==0:
        max_CR=np.inf
    else:
        max_CR=32/min_bitrate
    print(f"max_CR: {max_CR}")
with open("qb.bin","wb") as f:
    f.write((qb+32768).tobytes())

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