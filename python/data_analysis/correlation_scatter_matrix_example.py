#-*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import Series, DataFrame
from pandas.tools.plotting import scatter_matrix

df = DataFrame(np.random.randn(1000, 4), columns=['a', 'b', 'c', 'd'])
corr_mat = df.corr()
print corr_mat

scatter_matrix(df, alpha=0.2, figsize=(16, 16), diagonal='kde')

plt.show()
#plt.savefig('features.png')
