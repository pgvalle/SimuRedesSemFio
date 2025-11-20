from scipy.stats import t
import os
import numpy as np
import matplotlib.pyplot as plt

FOLDER = "results"
CONFIDENCE = 95
ALPHA = 1 - CONFIDENCE / 100
QUANTILE = 1 - ALPHA / 2


# T = t.ppf(QUANTILE, df=RUNS - 1)

files = os.listdir(FOLDER)

for name in files:
    path = f"{FOLDER}/{name}"
    file = open(path, "r")
    content = file.read()

    tcpDict = {}
    current = ""

    for line in content.splitlines():
        values = line.split()
        # line with meta-info
        if len(values) > 1:
            _, _, tcp = values
            tcpDict[tcp] = []
            current = tcp
            continue
        
        sample = float(values[0]) 
        tcpDict[current].append(sample)

    for tcp, samples in tcpDict.items():
        print(tcp, samples)

    file.close()

            


throughputs = [1, 2, 1, 2.5]

# mean = np.mean(throughputs)
# err = np.std(throughputs, ddof=1) / np.sqrt(RUNS)
# off = T * err / np.sqrt(RUNS)
#
# print(f"mean={mean}")
# print("throughputs:")
# for throughput in throughputs:
#     print(throughput)
