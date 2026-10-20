import numpy as np
def pulse_f0(y,sr):
    y=y-y.mean();N=len(y)
    # normalized autocorrelation, YIN-style cumulative mean difference
    maxlag=int(sr/30);d=np.array([np.sum((y[:N-maxlag]-y[t:N-maxlag+t])**2) for t in range(maxlag)])
    cm=d.copy();cm[1:]=d[1:]*np.arange(1,maxlag)/np.maximum(np.cumsum(d[1:]),1e-12);cm[0]=1
    minlag=int(sr/700)
    for t in range(minlag,maxlag-1):
        if cm[t]<0.15 and cm[t]<cm[t+1]:return sr/t
    return sr/(minlag+np.argmin(cm[minlag:]))
