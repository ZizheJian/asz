import pickle
import numpy as np
from sz3_record import sz3_record_c
import matplotlib.pyplot as plt

rel_eb=1e-4
with open(f"sz3_record_{rel_eb:.0e}.pkl","rb") as f:
    sz3_record_list=pickle.load(f)

x=np.zeros([len(sz3_record_list),65536]).astype(float)
y=np.zeros(len(sz3_record_list)).astype(float)
for i in range(len(sz3_record_list)):
    freq_sum=sz3_record_list[i].freq.sum()
    x[i]=sz3_record_list[i].freq/freq_sum
    y[i]=sz3_record_list[i].cr

# def l_single(x,param):
#     temp1=(param[1]*x+param[2]).clip(0,1)
#     temp2=(-np.log2(temp1))**param[3]
#     return (param[0]*temp2+param[4]).clip(0,1)

# def l_single(x,param):
#     temp1=(param[1]*x+param[2]).clip(0,1)
#     temp2=-np.log2(temp1)
#     return (param[0]*temp2+param[3]).clip(0,1)

def l_single(x,param):
    temp1=x+param[1]
    temp2=-np.log2(temp1)*param[0]+param[2]
    temp3=(temp2+np.sqrt(temp2**2+param[3]*1e-4))/2
    return temp3

# def l(x,param):
#     temp1=(param[1]*x+param[2]).clip(0,1)
#     temp2=temp1**(x**(1/param[3]))
#     temp3=(-np.log2(temp2))**param[3]
#     return (param[0]*temp3+param[4]*x).clip(0,1)

# def l(x,param):
#     temp1=(param[1]*x+param[2]).clip(0,1)
#     temp2=temp1**x
#     temp3=-np.log2(temp2)
#     return (param[0]*temp3+param[3]*x).clip(0,1)

def l(x,param):
    temp1=(x+param[1])**x
    temp2=-np.log2(temp1)*param[0]+param[2]*x
    temp3=(temp2+np.sqrt(temp2**2+(x**2)*param[3]*1e-4))/2
    return temp3

def loss_func(param,x,y):
    y_pred=32/(l(x,param).sum(axis=1))
    return np.mean((y-y_pred)**2)

# param=np.array([0.696,2.155,0.298,0.697,-0.261]).astype(float)
# param=np.array([0.484,1.910,0.307,-0.060]).astype(float)
param=np.array([0.484,0.161,-0.512,0.937]).astype(float)
lr_bound=1e-4
for epid in range(1):
    grad=np.zeros_like(param)
    loss0=loss_func(param,x,y)
    print(f"epid={epid}, loss0={loss0}")
    for i in range(4):
        param[i]+=lr_bound
        loss1=loss_func(param,x,y)
        print(f"loss1={loss1}")
        param[i]-=lr_bound
        grad[i]=(loss1-loss0)/lr_bound
    print(param)
    print(grad)
    lr=np.clip(lr_bound*np.abs(1/grad),0,lr_bound)
    print(f"lr={lr}")
    param-=lr*grad

plt.figure(figsize=(5,5))
plt.plot(np.arange(-20,21),y)
plt.plot(np.arange(-20,21),32/(l(x,param).sum(axis=1)))
plt.xlabel("abs_eb_power")
plt.ylabel("cr")
plt.tight_layout()
plt.savefig(f"sz3_record_cr_{rel_eb:.0e}.png",dpi=300)

plt.figure(figsize=(5,5))
plt.plot(np.linspace(0,1,100),l_single(np.linspace(0,1,100),param))
plt.xlabel("f")
plt.xlim(0,1)
plt.ylabel("l(f)")
plt.ylim(0,None)
plt.tight_layout()
plt.savefig(f"l.png",dpi=300)

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

param1=np.array([[1.03e-1,2.18e-1,4.61e-1],
                 [2.12e-3,5.80e-1,4.10e-1],
                 [1.79e-6,    1e3,3.98e-1]])
param2=np.array([[8.38e-1, 1e1],
                 [1.46e-2, 1e1]])

plt.figure(figsize=(10,5))
plt.plot(np.linspace(-20,20,401),l_single(f(np.linspace(-20,20,401),[param1,param2]),param))
plt.xlabel("qb")
plt.ylabel("l(f(qb))")
plt.tight_layout()
plt.savefig(f"l(f).png",dpi=300)