# %%
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import matplotlib.backends.backend_pdf
import sys
# %%
# sys.argv = ['', '5', '1']
# %%
class RingBuf:
    data = 0
    idx = -1
    full = False
    dtype = float
    size = 0
    pushed = 0
    
    def __init__(self, dtype = float):
        self.dtype = dtype
        return

    def __init__(self, size, dtype = float):
        self.dtype = dtype
        self.size = size
        self.Initialize(size)
        return

    def Initialize(self, size):
        if (size < 1):
            raise ValueError("Buffer size can not be negative or zero.")
        self.size = size
        self.data = np.zeros(size, dtype = self.dtype)
        self.pushed = 0
        self.idx = -1
        self.full = False
        return

    def HasData(self):
        return self.size > 0

    def IsFull(self):
        return self.full

    def GetIndex(self):
        return self.idx

    def __getitem__(self, key):
        if not self.HasData():
            raise Exception("Buffer not initialized.")
        if isinstance(key, slice):
            indices = key.indices((self.size))
            stride = -1 if indices[2] == None else -indices[2]
            start = self.GetIndex() - indices[0]
            while start < 0:
                start = start + self.size
            stop = self.GetIndex() - indices[1]
            while stop < 0:
                stop = stop + self.size
            print(start, stop, stride)
            if stop >= start:
                out = np.concatenate((self.data[start::stride], self.data[-1:stop:stride]))
                return out
            else:
                out = self.data[start:stop:stride]
                return out

        if key < 0:
            raise Exception("Index cannot be negative.")
        if key >= self.size:
            key = key % self.size
        index = (self.idx - key + self.size) % self.size
        return self.data[index]
    
    def __setitem__(self, key, val):
        if not self.HasData():
            raise Exception("Buffer not initialized.")
        if key < 0:
            raise Exception("Index cannot be negative.")
        if key >= self.size:
            key = key % self.size
        index = (self.idx - key + self.size) % self.size
        self.data[index] = val
        return

    def push(self, data):
        if not self.HasData():
            raise Exception("Buffer not initialized.")
        if self.idx == self.size - 1:
            self.full = True
        self.idx = (self.idx + 1) % self.size
        self.data[self.idx] = data
        self.pushed += 1
        return

    def clear(self):
        if not self.HasData():
            return
        self.idx = -1
        self.full = False
        self.data = np.zeros(self.size, dtype = self.dtype)
        pushed = 0
        return
    
    def GetPushed(self):
        return self.pushed
    
    def GetSize(self):
        return self.size

# %%
class GaussFilter:
    gauss_coeff = 0 
    size = 0

    def __init__(self, size, sigma, dtype = float):
        if size < 2:
            raise Exception("Gaussian filter size cannot be < 2.")
        self.size = size
        xr = np.arange(size, dtype = dtype)
        self.gauss_coeff = np.exp(-xr*xr/sigma/sigma)
        return
    
    def ApplyFilter(self, buf: RingBuf):
        if not buf.HasData():
            raise Exception("Ring buffer not initialized")
        
        num = buf.GetPushed() if buf.GetPushed() <= self.size else self.size
        coeffs = np.sum(self.gauss_coeff[0:num])
        val = np.sum(self.gauss_coeff[0:buf.GetIndex()+1] * buf.data[buf.GetIndex()::-1])
        num -= buf.GetIndex()
        if buf.IsFull() and num > 0:
            val += np.sum(self.gauss_coeff[buf.GetIndex()+1:buf.GetIndex() + num] * buf.data[-1:buf.GetIndex():-1])
        return val / coeffs
# %%
buf = RingBuf(10)
dat = RingBuf(10)
ftr = GaussFilter(10, 2)
for i in range(15):
    buf.push(float(i))
    dat.push(i)
    buf[0] = ftr.ApplyFilter(buf)
plt.plot(np.flip(buf[:]))
plt.plot(np.flip(dat[:]))
plt.show()
# %%
if len(sys.argv) != 3:
    print("Invocation: %s <Order> <Cutoff Frequency>\n\n"%(sys.argv[0]))
    sys.exit(0)
# %%
order = int(sys.argv[1])
cutoff_freq = int(sys.argv[2])
# %%
mes_fname = 'data_mes_%d_%d.txt'%(order, cutoff_freq)
grad_fname = 'data_grad_%d_%d.txt'%(order, cutoff_freq)
pagewidth = 11 * 1.5
pageheight = 8.5 * 1.5
# %%
def Gauss(x, A, B, C):
    y = A*np.exp(-1*((x - C)/B)**2)
    return y
# %%
mesdata = np.loadtxt(mes_fname, delimiter = ',').transpose()
graddata = np.loadtxt(grad_fname, delimiter = ',').transpose()
# %%
pdf = matplotlib.backends.backend_pdf.PdfPages('stat_%d_%d.pdf'%(order, cutoff_freq))
# %%
def GetFitFromHist(n, bin, p0 = [1, 1, 0.1]):
    xbins_ftr = []
    for i in range(bin.shape[0] - 1):
        xbins_ftr.append(bin[i] + bin[i + 1])
    xbins_ftr = np.array(xbins_ftr) * 0.5
    par, cov = curve_fit(Gauss, xbins_ftr, n, p0 = p0)
    return (par, cov, (xbins_ftr.min(), xbins_ftr.max()))
# %%
pars = dict()
covs = dict()
xlims2 = dict()
# %%
fig, ax = plt.subplot_mosaic([['data', 'hist'], ['unbiased', 'hist']], constrained_layout = True, figsize = (pagewidth, pageheight))
# fig.subplots_adjust(hspace=0)
fig.suptitle("Measurement Statistics of Acquired Data for filter order %d, cutoff %d\n1: Data, 2: Measurement (white noise), 3: Filtered measurement"%(order, cutoff_freq))
ax['unbiased'].set_xlabel("Time (s)")
ax['data'].plot(mesdata[0], mesdata[1], color = 'k', label = "1")
ax['data'].plot(mesdata[0], mesdata[2], color = 'b', label = "2", ls = '', marker = 'x')
ax['data'].plot(mesdata[0], mesdata[3], color = 'r', label = "3", ls = '', marker = '+')
ax['data'].legend()
ax['data'].grid()
ax['data'].get_xaxis()
ax['unbiased'].plot(mesdata[0], mesdata[1] - mesdata[1], color = 'k', label = "1")
ax['unbiased'].plot(mesdata[0], mesdata[2] - mesdata[1], color = 'b', label = "2", ls = '', marker = 'x')
ax['unbiased'].plot(mesdata[0], mesdata[3] - mesdata[1], color = 'r', label = "3", ls = '', marker = '+')
ax['unbiased'].legend()
ax['unbiased'].grid()
nvals, xbins, _ = ax['hist'].hist(mesdata[3] - mesdata[1], bins = 25, color = 'r', align = 'mid', histtype = 'stepfilled', label = "Histogram of (3 - 1) data", alpha = 0.7)
par, cov, xlims = GetFitFromHist(nvals, xbins, p0 = [10, 0.1, 0])
pars['data_31'] = par
covs['data_31'] = cov
xlims2['data_31'] = xlims
xbins_ftr = np.linspace(xlims[0], xlims[1], 100, endpoint=True)
ax['hist'].plot(xbins_ftr, Gauss(xbins_ftr, par[0], par[1], par[2]), color = 'k', linewidth = 2, label = 'Histogram fit (3 - 1) data: A = %.3f, mu = %.3f, sig = %.3f'%(par[0], par[2], par[1]))
nvals, xbins, _ = ax['hist'].hist(mesdata[2] - mesdata[1], bins = 25, color = 'b', align = 'mid', histtype = 'stepfilled', alpha = 0.4, label = "Histogram of (2 - 1) data")
par, cov, xlims = GetFitFromHist(nvals, xbins, p0 = [10, 0.1, 0])
pars['data_21'] = par
covs['data_21'] = cov
xlims2['data_21'] = xlims
xbins_ftr = np.linspace(xlims[0], xlims[1], 100, endpoint=True)
ax['hist'].plot(xbins_ftr, Gauss(xbins_ftr, par[0], par[1], par[2]), color = 'b', linewidth = 2, label = 'Histogram fit (2 - 1) data: A = %.3f, mu = %.3f, sig = %.3f'%(par[0], par[2], par[1]))
ax['hist'].grid()
ax['hist'].legend()
pdf.savefig(fig)

# %%
fig, ax = plt.subplot_mosaic([['data', 'hist'], ['unbiased', 'hist']], constrained_layout = True, figsize = (pagewidth, pageheight))
# fig.subplots_adjust(hspace=0)
fig.suptitle("Measurement Statistics of gradient data for filter order %d, cutoff %d\n1: Gradient, 2: Gradient from unfiltered measurement, 3: Filtered gradient from filtered measurement"%(order, cutoff_freq))
ax['unbiased'].set_xlabel("Time (s)")
ax['data'].plot(graddata[0], graddata[1], color = 'k', label = "1")
ax['data'].plot(graddata[0], graddata[2], color = 'b', label = "2", ls = '', marker = 'x')
ax['data'].plot(graddata[0], graddata[4], color = 'r', label = "3", ls = '', marker = '+')
ax['data'].legend()
ax['data'].grid()
ax['data'].get_xaxis()
ax['unbiased'].plot(graddata[0], graddata[1] - graddata[1], color = 'k', label = "1")
ax['unbiased'].plot(graddata[0], graddata[2] - graddata[1], color = 'b', label = "2", ls = '', marker = 'x')
ax['unbiased'].plot(graddata[0], graddata[4] - graddata[1], color = 'r', label = "3", ls = '', marker = '+')
ax['unbiased'].legend()
ax['unbiased'].grid()
nvals, xbins, _ = ax['hist'].hist(graddata[4] - graddata[1], bins = 25, color = 'r', align = 'mid', histtype = 'stepfilled', label = "Histogram of (3 - 1) data", alpha = 0.7)
par, cov, xlims = GetFitFromHist(nvals, xbins, p0 = [10, 0.1, 0])
pars['grad_41'] = par
covs['grad_41'] = cov
xlims2['grad_41'] = xlims
xbins_ftr = np.linspace(xlims[0], xlims[1], 100, endpoint=True)
ax['hist'].plot(xbins_ftr, Gauss(xbins_ftr, par[0], par[1], par[2]), color = 'k', linewidth = 2, label = 'Histogram fit (3 - 1): A = %.3f, mu = %.3f, sig = %.3f'%(par[0], par[2], par[1]))
nvals, xbins, _ = ax['hist'].hist(graddata[2] - graddata[1], bins = 25, color = 'b', align = 'mid', histtype = 'stepfilled', alpha = 0.4, label = "Histogram of (2 - 1) data")
par, cov, xlims = GetFitFromHist(nvals, xbins, p0 = [10, 0.1, 0])
pars['grad_21'] = par
covs['grad_21'] = cov
xlims2['grad_21'] = xlims
xbins_ftr = np.linspace(xlims[0], xlims[1], 100, endpoint=True)
ax['hist'].plot(xbins_ftr, Gauss(xbins_ftr, par[0], par[1], par[2]), color = 'b', linewidth = 2, label = 'Histogram fit (2 - 1): A = %.3f, mu = %.3f, sig = %.3f'%(par[0], par[2], par[1]))
ax['hist'].grid()
ax['hist'].legend()
pdf.savefig(fig)

# %%
count = 1
fig = plt.figure(figsize=(11, 8.5))
fig.clf(True)
txt = ''
for key in pars.keys():
    txt += '%s:\nA = %e Sigma = %e Mu = %e\nCov[A] = %e Cov[Mu] = %eCov[Sigma] = %e\nXmin = %e Ymin = %e\n\n'%(key, pars[key][0], pars[key][1], pars[key][2], covs[key][0, 0], covs[key][1, 1], covs[key][2, 2], xlims2[key][0], xlims2[key][1])
fig.text(0.5, 0.5, txt, transform=fig.transFigure, ha="center")
pdf.savefig(fig)
# %%
pdf.close()

# %%

# %%
