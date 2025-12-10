import matplotlib
matplotlib.use('gtk3agg')

import matplotlib.pyplot as plt
import csv

filename = 'results.csv'
target_ber = 0.001
target_off_col = 'off95'

FONT_SIZE = 11.5
plt.rcParams['font.size'] = FONT_SIZE

# Data structure: {tcp_variant: [(delay_int, mean, error), ...]}
data = {}

with open(filename, 'r', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            ber = float(row['ber'])
            # Filter for BER = 1e-4 (0.0001)
            if abs(ber - target_ber) > 1e-9:
                continue
            
            tcp = row['tcp']
            delay_str = row['delay']
            
            # Parse delay "1ms" -> 1 (int) for correct sorting
            delay_val = int(delay_str.replace('ms', '').strip())
            
            mean = float(row['mean'])
            error = float(row[target_off_col])
            
            if tcp not in data:
                data[tcp] = []
            data[tcp].append((delay_val, mean, error))
            
        except ValueError:
            continue

# Setup Plot
plt.figure(figsize=(10, 6))
markers = ['o', 's', '^', 'D', 'v'] 

# Iterate through sorted TCP names for consistent coloring/ordering
for i, tcp in enumerate(sorted(data.keys())):
    values = data[tcp]
    # Sort by delay so the line connects points correctly from left to right
    values.sort(key=lambda x: x[0])
    
    delays = [v[0] for v in values]
    means = [v[1] for v in values]
    errors = [v[2] for v in values]
    
    plt.errorbar(delays, means, yerr=errors, label=tcp, 
                 marker=markers[i % len(markers)], capsize=4, linestyle='-')

plt.xlabel('Delay (ms)')
plt.ylabel('Average Throughput (Kbps)')
plt.title(f'TCP Throughput vs Delay (BER = {target_ber})')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)

# Ensure x-axis ticks match the specific delays in the data
all_delays = sorted(list(set(d for vals in data.values() for d, _, _ in vals)))
plt.xticks(all_delays, [f'{d}ms' for d in all_delays])
plt.show()
