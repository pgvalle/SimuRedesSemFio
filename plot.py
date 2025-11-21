import scipy.stats as sci
import os
import numpy as np
import matplotlib.pyplot as plt

CONFIDENCE = 95
ALPHA = 1 - CONFIDENCE / 100
QUANTILE = 1 - ALPHA / 2
FOLDER = "results"

def calculateConfidenceInterval(samples):
    n = len(samples)
    t = sci.t.ppf(QUANTILE, df=n-1)
    err = np.std(samples, ddof=1) / np.sqrt(n)
    off =  t * err
    return np.mean(samples), off

def readFile(path):
    file = open(path, "r")
    content = file.read()

    variants = []
    variantsSamples = []

    for line in content.splitlines():
        info = line.split()
        # line with meta-info
        if len(info) > 1:
            _, _, tcp = info
            variants.append(tcp)
            variantsSamples.append([])
            continue
        
        sample = double(info[0])
        variantsSamples[-1].append(sample)

    fig, ax = plt.subplots()


    file.close()

files = os.listdir(FOLDER)
"""
for name in files:
    path = f"{FOLDER}/{name}"
    file = open(path, "r")
    content = file.read()

    tcpVariants = {}
    tcp = ""

    for line in content.splitlines():
        info = line.split()
        # line with meta-info
        if len(info) > 1:
            _, _, tcp = info
            tcpVariants[tcp] = []
            continue
        
        sample = float(info[0]) 
        tcpVariants[tcp].append(sample)

    file.close()
"""

cats = ['A', 'B', 'C', 'D']
vals1 = [4, 7, 1, 8]
vals2 = [5, 6, 2, 9]

# Create a figure and an array of axes objects (in this case, 1 row, 2 columns)
fig, ax = plt.subplots(1, 2, figsize=(10, 4))

# --- First Subplot (ax[0]) ---
w = 0.4 # bar width
x = np.arange(len(cats))
ax[0].bar(x - w/2, vals1, width=w, label='Set 1')
ax[0].bar(x + w/2, vals2, width=w, label='Set 2')
ax[0].set_xticks(x)
ax[0].set_xticklabels(cats)
ax[0].set_ylabel('Values')
ax[0].set_title('Grouped Bar Chart 1')
ax[0].legend()

# --- Second Subplot (ax[1]) ---
ax[1].bar(x, vals2, width=w, color='orange', label='Set 2')
ax[1].set_xticks(x)
ax[1].set_xticklabels(cats)
ax[1].set_ylabel('Values')
ax[1].set_title('Grouped Bar Chart 2')
ax[1].legend()

# Adjust layout to prevent titles/labels from overlapping
plt.tight_layout()
plt.ion()
plt.show()

