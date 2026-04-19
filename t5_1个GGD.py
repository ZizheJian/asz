import numpy as np
import matplotlib.pyplot as plt
from scipy.special import gamma,logsumexp
from scipy.optimize import minimize

with open("pred_err_0.4.bin","rb") as f:
    pred_err_vec=np.frombuffer(f.read(),dtype=np.float64)

def log_ggd_pdf(x,a,b):
    return np.log(b/(2*a*gamma(1/b)))-(np.abs(x)/a)**b

def ggd_pdf(x,a,b):
    return np.exp(log_ggd_pdf(x,a,b))

def negloglik(b,err):
    b=float(b[0])
    a=(np.mean(np.abs(err)**b)*b)**(1/b)
    ll=np.sum(log_ggd_pdf(err,a,b))

    print(f"a={a}")
    print(f"b={b}")
    print(f"logL={ll}")
    print()
    return -ll

b=0.5
bounds=[(0.1,4.0)]
res=minimize(negloglik,b,args=(pred_err_vec),method="Powell",bounds=bounds)
a=(np.mean(np.abs(pred_err_vec)**b)*b)**(1/b)

# t2=0.0
# a=0.0012815911497057566
# b=0.2595911423759815
# logL=-10418664.935781172

# t2=0.25
# a=5.6905212840287277e-05
# b=0.21577978609620627
# logL=3341505.4709079536

# t2=0.3125
# a=7.911708807702214e-07
# b=0.16780700195496057
# logL=11045320.011600297

# t2=0.4
# a=6.55369455210184e-05
# b=0.21676077218821405
# logL=2280002.3747829506

plot_range=(-0.25,0.25)
x=np.linspace(plot_range[0],plot_range[1],1001)
y=ggd_pdf(x,a,b)
plt.hist(pred_err_vec,bins=1001,weights=np.ones_like(pred_err_vec)*1001/(plot_range[1]-plot_range[0])/len(pred_err_vec),range=plot_range)
plt.plot(x,y)
plt.xlim(plot_range)
plt.ylim(0,None)
plt.savefig("pred_err_hist.png")



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