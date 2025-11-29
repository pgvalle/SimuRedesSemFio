import scipy.stats as sci
import numpy as np
import sys

printEnabled = True

def interval(samples, confidence=0.95):
    alpha = 1 - confidence
    quantile = 1 - alpha / 2

    mean = np.mean(samples)

    n = len(samples)
    t = sci.t.ppf(quantile, df=n-1)
    offset = t * np.std(samples, ddof=1) / np.sqrt(n)

    return mean, offset

def myprint(*args, sep=' ', end='\n', file=sys.stdout, flush=False):
    if not printEnabled:
        return

    output_string = sep.join(str(arg) for arg in args)
    file.write(output_string + end)
    if flush:
        file.flush()
