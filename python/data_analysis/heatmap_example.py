#-*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import Series, DataFrame

def show_values(pc, fmt="%.6f", **kw):
    from itertools import izip
    pc.update_scalarmappable()
    ax = pc.get_axes()
    for p, color, value in izip(pc.get_paths(), pc.get_facecolors(), pc.get_array()):
        x, y = p.vertices[:-2, :].mean(0)
        if np.all(color[:3] > 0.5):
            color = (0.0, 0.0, 0.0)
        else:
            color = (1.0, 1.0, 1.0)
        ax.text(x, y, fmt % value, ha="center", va="center", color=color, **kw)

# set labels
xlabels = ['x1', 'x2', 'x3', 'x4', 'x5', 'x6']
ylabels = ['y1', 'y2', 'y3', 'y4', 'y5', 'y6']

#arr = np.loadtxt('test_data.txt')
arr = np.random.uniform(low=-1.0, high=1.0, size=(6,6))
print arr.shape

df = DataFrame(arr, index=xlabels, columns=ylabels)
print df

plt.figure(figsize=(8, 12))
plt.yticks(np.arange(0.5, len(df.index), 1), df.index)
plt.xticks(np.arange(0.5, len(df.columns), 1), df.columns, rotation=90)
plt.axis([0, arr.shape[0], 0, arr.shape[1]])
c = plt.pcolor(df, edgecolors='k', linewidths=1, cmap='RdBu', vmin=-1.1, vmax=1.1)

show_values(c)
plt.colorbar(c)
plt.tight_layout()
plt.autoscale()
plt.show()
