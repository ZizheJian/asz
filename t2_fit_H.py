import numpy as np
import scipy

with open("results_cubic_prediction.csv","r") as f:
    lines=f.readlines()
    lines=[line.strip().split(",") for line in lines]
    eb_set=set()
    t2_set=set()
    val_name_set=set()
    for line in lines[1:]:
        t2_set.add(float(line[0]))
    for item in lines[0][1:]:
        item=item.strip().split("_")
        eb_set.add(item[0])
        val_name_set.add(item[1])
    eb_list=sorted(map(float,eb_set),reverse=True)
    t2_list=sorted(t2_set)
    val_name_list=sorted(list(val_name_set))
    data=np.zeros((len(eb_list),len(t2_list),len(val_name_list)))
    for line in lines[1:]:
        t2=float(line[0])
        t2_index=t2_list.index(t2)
        for i in range(1,len(line)):
            eb=float(lines[0][i].strip().split("_")[0])
            val_name=lines[0][i].strip().split("_")[1]
            eb_index=eb_list.index(eb)
            val_name_index=val_name_list.index(val_name)
            data[eb_index][t2_index][val_name_index]=float(line[i])


br=data[:,:,0].reshape(-1)
H1=data[:,:,1].reshape(-1)
H2=data[:,:,2].reshape(-1)
H3=data[:,:,3].reshape(-1)
H4=data[:,:,4].reshape(-1)
def loss(x):
    a1,a2,a3,a4,b=x
    br_pred=a1*H1+a2*H2+a3*H3+a4*H4+b
    if np.any(br_pred<=0):
        return np.inf
    return np.mean((np.log(br_pred)-np.log(br))**2)
res=scipy.optimize.minimize(loss,x0=[0.25,0.25,0.25,0.25,0])
print("Coefficients:",res.x)
print(np.sqrt(res.fun))