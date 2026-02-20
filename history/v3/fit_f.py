import pickle
import numpy as np
from sz3_record import sz3_record_c
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from scipy.optimize import minimize

rel_eb=1e-3

with open(f"sz3_record_{rel_eb:.0e}.pkl","rb") as f:
    sz3_record_list=pickle.load(f)

x=np.arange(-32768,32768).astype(float)
y=sz3_record_list[len(sz3_record_list)//2].freq
non_zero_indices=np.nonzero(y)[0]
x_min=non_zero_indices[0]-32768
x_max=non_zero_indices[-1]-32768
print(f"x_min={x_min}, x_max={x_max}")
y_sum=np.sum(y)
print(f"y_sum={y_sum}")
y=y/y_sum

k1=3
k2=2

def f(x,param):
    params1=param[0]
    params2=param[1]
    ans=0
    for i in range(k1):
        a=params1[i][0]
        w=params1[i][1]
        p=params1[i][2]
        ans+=a*np.exp(-((np.abs(x)/w)**p))
    for i in range(k2):
        a=params2[i][0]
        w=i+0.5
        p=params2[i][1]
        ans+=a*np.exp(-((np.abs(x)/w)**p))
    return ans

def loss_func(param,x,y):
    y_pred=f(x,param)
    loss=np.sum((-np.log2(y**(y**0.5))+np.log2(y_pred**(y**0.5)))**2)
    return loss

param1=np.array([[1.03e-1,2.18e-1,4.61e-1],
                 [2.12e-3,5.80e-1,4.10e-1],
                 [1.79e-6,    1e3,3.98e-1]])
param2=np.array([[8.38e-1, 1e1],
                 [1.46e-2, 1e1]])
x_dense=[]
y_dense=[]
for i in range(x_min,x_max+1):
    for j in range(-4,5,1):
        x_dense.append(i+j/10)
        y_dense.append(y[i+32768])
x_dense=np.array(x_dense)
y_dense=np.array(y_dense)
print(f"loss={loss_func([param1,param2],x_dense,y_dense)}")
lr_bound=0.01
for epid in range(10000):
    grad1=np.zeros_like(param1)
    grad2=np.zeros_like(param2)
    loss0=loss_func([param1,param2],x_dense,y_dense)
    for i in range(k1):
        for j in range(3):
            param1[i][j]*=(1+lr_bound)
            loss1=loss_func([param1,param2],x_dense,y_dense)
            param1[i][j]/=(1+lr_bound)
            grad1[i][j]=(loss1-loss0)/(param1[i][j]*lr_bound)
    for i in range(k2):
        for j in range(2):
            param2[i][j]*=(1+lr_bound)
            loss1=loss_func([param1,param2],x_dense,y_dense)
            param2[i][j]/=(1+lr_bound)
            grad2[i][j]=(loss1-loss0)/(param2[i][j]*lr_bound)
    print(param1)
    print(grad1)
    print(param2)
    print(grad2)
    lr1=np.clip(lr_bound*np.abs(param1/grad1),0,lr_bound)
    lr2=np.clip(lr_bound*np.abs(param2/grad2),0,lr_bound)
    print(f"lr1={lr1}")
    print(f"lr2={lr2}")
    param1-=lr1*grad1
    param2-=lr2*grad2
print(f"loss={loss_func([param1,param2],x_dense,y_dense)}")
for qb in range(-20,21):
    print(f"qb={qb}, y={y[32768+qb]}, my_func={f(qb,[param1,param2])}")

x_exp=np.concatenate((-10**(np.linspace(4,-2,1000)),np.array([0]),10**(np.linspace(-2,4,1000))))
plt.figure(figsize=(10,5))
plt.plot(x,y*y_sum,label="sz3_record",linestyle="None",marker="o",markersize=0.5)
plt.plot(x_exp,f(x_exp,[param1,param2])*y_sum,label="my_func",alpha=0.5)
plt.legend()
plt.xlabel("qb")
plt.xlim(x_min,x_max)
plt.ylabel("freq")
plt.yscale("log")
plt.ylim(0.1,None)
plt.tight_layout()
plt.savefig("fit_f_all.png",dpi=300)

plt.xlim(-100,100)
plt.savefig("fit_f_100.png",dpi=300)

plt.xlim(-10,10)
plt.savefig("fit_f_10.png",dpi=300)