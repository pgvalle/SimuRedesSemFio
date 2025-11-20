from scipy.stats import t
import numpy as np
import matplotlib.pyplot as plt

CONFIDENCE = 95
ALPHA = 1 - CONFIDENCE / 100
QUANTILE = 1 - a / 2
T = t.ppf(q, df=RUNS - 1)

throughputs = [1, 2, 1, 2.5]

mean = np.mean(throughputs)
err = np.std(throughputs, ddof=1) / np.sqrt(RUNS)
off = T * err / np.sqrt(RUNS)

print(f"mean={mean}")
print("throughputs:")
for throughput in throughputs:
    print(throughput)
