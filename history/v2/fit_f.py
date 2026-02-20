import pickle
import numpy as np
from sz3_record import sz3_record_c
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from scipy.optimize import minimize

rel_eb=1e-4

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

def l(f):
    return -np.log2(f**(f**0.5))

def my_func(x,a1,w1,p1,a2,w2,p2,a3,w3,p3,a4,p4,a5,p5):
    ans=a1*np.exp(-((np.abs(x)/w1)**p1))
    ans+=a2*np.exp(-((np.abs(x)/w2)**p2))
    ans+=a3*np.exp(-((np.abs(x)/w3)**p3))
    ans+=a4*np.exp(-((np.abs(x)/0.5)**p4))
    ans+=a5*np.exp(-((np.abs(x)/1.5)**p5))
    return ans

def loss_func(param,x,y):
    y_pred=my_func(x,*param)
    loss=np.sum((l(y)-l(y_pred))**2)
    return loss

p0=[1.05e-1,2.19e-1,4.71e-1,
    2.20e-3,5.89e-1,4.05e-1,
    3.51e-8,1000,4e-1,
    8.40e-1, 1.35e7,
    1.48e-2, 1.33e7]
bounds=[(0,1),(0,None),(0,None),
        (0,1),(0,None),(0,None),
        (0,1),(0,None),(0,None),
        (0,1),(0,None),
        (0,1),(0,None)]
x_dense=[]
y_dense=[]
for i in range(x_min,x_max+1):
    for j in range(-4,5,1):
        x_dense.append(i+j/10)
        y_dense.append(y[i+32768])
x_dense=np.array(x_dense)
y_dense=np.array(y_dense)
print(f"loss={loss_func(p0,x_dense,y_dense)}")
res=minimize(lambda p:loss_func(p,x_dense,y_dense),p0,method="trust-constr",bounds=bounds)
if res.success:
    print(f"拟合成功，参数为：{res.x}")
else:
    print(f"拟合失败，参数为：{res.x}")
param=res.x
print(f"loss={loss_func(param,x_dense,y_dense)}")
for qb in range(-20,21):
    print(f"qb={qb}, y={y[32768+qb]}, my_func={my_func(qb,*param)}")

x_exp=np.concatenate((-10**(np.linspace(4,-2,1000)),np.array([0]),10**(np.linspace(-2,4,1000))))
plt.figure(figsize=(10,5))
plt.plot(x,y*y_sum,label="sz3_record",linestyle="None",marker="o",markersize=0.5)
plt.plot(x_exp,my_func(x_exp,*param)*y_sum,label="my_func",alpha=0.5)
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