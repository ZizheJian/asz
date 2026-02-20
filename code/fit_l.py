import pickle
import numpy as np
from sz3_record import sz3_record_c
import matplotlib.pyplot as plt
from fit_f import f_c

class l_c():
    def __init__(self,k:int):
        self.k=4
        self.param=np.array([0.484,0.161,-0.512,0.937]).astype(float)
        if k!=self.k:
            raise ValueError(f"Expected k={self.k}, got k={k}")
    def l_single(self,x):
        temp1=x+self.param[1]
        temp2=-np.log2(temp1)*self.param[0]+self.param[2]
        temp3=(temp2+np.sqrt(temp2**2+self.param[3]*1e-4))/2
        return temp3
    def l(self,x):
        temp1=(x+self.param[1])**x
        temp2=-np.log2(temp1)*self.param[0]+self.param[2]*x
        temp3=(temp2+np.sqrt(temp2**2+(x**2)*self.param[3]*1e-4))/2
        return temp3
    def loss_func(self,x,y):
        y_pred=32/(self.l(x).sum(axis=1))
        return np.mean((y-y_pred)**2)

if __name__=="__main__":
    data_name="Pf01.bin"
    rel_eb=1e-4
    with open(f"sz3_record/{data_name}_{rel_eb:.0e}.pkl","rb") as file:
        sz3_record_list=pickle.load(file)

    x=np.zeros([len(sz3_record_list),65536]).astype(float)
    y=np.zeros(len(sz3_record_list)).astype(float)
    for i in range(len(sz3_record_list)):
        freq_sum=sz3_record_list[i].freq.sum()
        x[i]=sz3_record_list[i].freq/freq_sum
        y[i]=sz3_record_list[i].cr

    l=l_c(4)

    lr_bound=1e-4
    for epid in range(1):
        grad=np.zeros_like(l.param)
        loss0=l.loss_func(x,y)
        print(f"epid={epid}, loss0={loss0}")
        for i in range(4):
            l.param[i]+=lr_bound
            loss1=l.loss_func(x,y)
            print(f"loss1={loss1}")
            l.param[i]-=lr_bound
            grad[i]=(loss1-loss0)/lr_bound
        print(l.param)
        print(grad)
        lr=np.clip(lr_bound*np.abs(1/grad),0,lr_bound)
        print(f"lr={lr}")
        l.param-=lr*grad

    plt.figure(figsize=(5,5))
    plt.plot(np.arange(-20,21),y)
    plt.plot(np.arange(-20,21),32/(l.l(x).sum(axis=1)))
    plt.xlabel("abs_eb_power")
    plt.ylabel("cr")
    plt.tight_layout()
    plt.savefig(f"{data_name}_{rel_eb:.0e}_cr.png",dpi=300)

    plt.figure(figsize=(5,5))
    plt.plot(np.linspace(0,1,100),l.l_single(np.linspace(0,1,100)))
    plt.xlabel("f")
    plt.xlim(0,1)
    plt.ylabel("l(f)")
    plt.ylim(0,None)
    plt.tight_layout()
    plt.savefig(f"{data_name}_{rel_eb:.0e}_l.png",dpi=300)

    with open(f"f/{data_name}_{rel_eb:.0e}.pkl","rb") as file:
        f:f_c=pickle.load(file)

    plt.figure(figsize=(10,5))
    plt.plot(np.linspace(-20,20,401),l.l_single(f.f(np.linspace(-20,20,401))))
    plt.xlabel("qb")
    plt.ylabel("l(f(qb))")
    plt.tight_layout()
    plt.savefig(f"{data_name}_{rel_eb:.0e}_l(f).png",dpi=300)

    with open(f"l/{data_name}_{rel_eb:.0e}.pkl","wb") as file:
        pickle.dump(l,file)