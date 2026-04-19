# 用一个GGD拟合一个二进制文件

import numpy as np
import matplotlib.pyplot as plt
from scipy.special import gamma,logsumexp
from scipy.optimize import minimize

with open("pred_err.bin","rb") as f:
    pred_err_vec=np.frombuffer(f.read(),dtype=np.float64)

print(f"len={len(pred_err_vec)}")
print(f"mean={pred_err_vec.mean()}")
print(f"var={pred_err_vec.var()}")

# print(f"p(err=0)={np.mean(pred_err_vec==0)}")
# print(f"p(abs(err)<1e-6)={np.mean(np.abs(pred_err_vec)<1e-6)}")
# print(f"p(abs(err)<1e-5)={np.mean(np.abs(pred_err_vec)<1e-5)}")
# print(f"p(abs(err)<1e-4)={np.mean(np.abs(pred_err_vec)<1e-4)}")
# print(f"p(abs(err)<1e-3)={np.mean(np.abs(pred_err_vec)<1e-3)}")
# print(f"p(abs(err)<1e-2)={np.mean(np.abs(pred_err_vec)<1e-2)}")
# print(f"p(abs(err)<1e-1)={np.mean(np.abs(pred_err_vec)<1e-1)}")

# pred_err_vec=pred_err_vec[pred_err_vec!=0]

# print(f"np.quantile(np.abs(pred_err_vec),[0.5,0.9,0.99,0.999,0.9999])={np.quantile(np.abs(pred_err_vec),[0.5,0.9,0.99,0.999,0.9999])}")

# x_range=2
# plt.figure()
# plt.hist(pred_err_vec,bins=501,weights=np.ones_like(pred_err_vec)*501/(x_range*len(pred_err_vec)),range=(-x_range/2,x_range/2))
# plt.xlim(-x_range/2,x_range/2)
# plt.savefig("pred_err_hist.png")

# e1=np.mean(np.abs(pred_err_vec))
# e2=np.mean(pred_err_vec**2)
# e4=np.mean(pred_err_vec**4)
# e6=np.mean(pred_err_vec**6)
# e8=np.mean(pred_err_vec**8)
# e10=np.mean(pred_err_vec**10)
# e12=np.mean(pred_err_vec**12)
# print(f"e1={e1}")
# print(f"e2={e2}")
# print(f"e4={e4}")
# print(f"e6={e6}")
# print(f"e8={e8}")
# print(f"e10={e10}")
# print(f"e12={e12}")

# def pdf(x,p0,a0,b0,p1,a1,b1):
#     ret=p0*(b0/(2*a0*gamma(1/b0)))*np.exp(-(np.abs(x)/a0)**b0)+p1*(b1/(2*a1*gamma(1/b1)))*np.exp(-(np.abs(x)/a1)**b1)
#     return ret

# x=np.linspace(-1000-range/2,-1000+range/2,501)
# y=np.array([pdf(xi,p0,a0,b0,p1,a1,b1) for xi in x])
# y[x==0]+=(1-p0-p1)*501/range
# plt.figure()
# plt.plot(x,y)
# plt.xlim(-range/2,range/2)
# plt.ylim(0,None)
# plt.savefig("pred_err_pdf.png")

# print(np.mean((1400<np.abs(pred_err_vec)) & (np.abs(pred_err_vec)<1600))/400)
# print(pdf(1500,p0,a0,b0,p1,a1,b1))

def ggd_logpdf(x,a,b):
    return np.log(b/(2*a*gamma(1/b)))-(np.abs(x)/a)**b

def pdf(theta,x,k,x_range):
    pp=theta[0:k]
    aa=theta[k:2*k]
    b=theta[2*k:3*k]
    p=np.zeros(k)
    a=np.zeros(k)
    for j in range(0,k):
        if j==0:
            p[j]=pp[j]
            a[j]=aa[j]
        else:
            p[j]=(1-p[:j].sum())*pp[j]
            a[j]=a[j-1]+aa[j]
    ret=np.zeros_like(x)
    for j in range(k):
        ret+=p[j]*np.exp(ggd_logpdf(x,a[j],b[j]))
    ret[x==0]+=(1-p.sum())*501/x_range
    return ret

def negloglik(theta,err,k):
    pp=theta[0:k]
    aa=theta[k:2*k]
    b=theta[2*k:3*k]
    p=np.zeros(k)
    a=np.zeros(k)
    for j in range(0,k):
        if j==0:
            p[j]=pp[j]
            a[j]=aa[j]
        else:
            p[j]=(1-p[:j].sum())*pp[j]
            a[j]=a[j-1]+aa[j]
    err_nz=err[err!=0]
    nz_num=len(err_nz)
    z_num=len(err)-nz_num

    ll=0
    if z_num>0:
        ll+=z_num*np.log(1-p.sum())

    if nz_num>0:
        terms=[]
        for j in range(k):
            terms.append(np.log(p[j])+ggd_logpdf(err_nz,a[j],b[j]))
        ll+=logsumexp(np.vstack(terms),axis=0).sum()
    print(f"pp={pp}")
    print(f"aa={aa}")
    print(f"p0={1-p.sum()}")
    print(f"p={p}")
    print(f"a={a}")
    print(f"b={b}")
    print(f"logL={ll}")
    print()
    return -ll    

k=3
theta0=np.zeros(3*k)
# theta0[0:k]=0.9/k
# theta0[k:2*k]=2**np.linspace(-3,10,k)
# theta0[2*k:3*k]=np.linspace(0.5,2.0,k)
theta0[0:k]=np.array([0.84,0.84,0.84])
theta0[k:2*k]=np.array([0.015625,0.25136834,4.2])
theta0[2*k:3*k]=np.array([0.5,0.5,0.5])
bounds=[]
bounds.extend([(0,1)]*k)
bounds.extend([(2**-6,2**11)]*k)
bounds.extend([(0.1,4.0)]*k)
res=minimize(negloglik,theta0,args=(pred_err_vec,k),method="Powell",bounds=bounds)

# x=np.linspace(-x_range/2,x_range/2,501)
# y=pdf(theta0,x,k,x_range)
# plt.figure()
# plt.plot(x,y)
# plt.xlim(-x_range/2,x_range/2)
# plt.ylim(0,None)
# plt.savefig("pred_err_pdf.png")

# pp=[0.85057302 0.9726468 ]
# aa=[0.015625   0.25136834]
# p0=0.004087305516004891
# p=[0.85057302 0.14533967]
# a=[0.015625   0.26699334]
# b=[0.52724301 0.45935216]
# logL=2960111.67159765

# pp=[0.81858474 0.95555128 0.50913625]
# aa=[0.01672577 0.24446781 6.66168007]
# p0=0.003958166062935864
# p=[0.81858474 0.17335158 0.00410551]
# a=[0.01672577 0.26119359 6.92287366]
# b=[0.54274705 0.5180608  0.42516365]
# logL=3118197.1894878694