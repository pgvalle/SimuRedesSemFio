import matplotlib
matplotlib.use('gtk3agg')

import matplotlib.pyplot as plt
import csv

filename = 'results.csv'
target_ber = 0.0001
target_off_col = 'off95'

FONT_SIZE = 11.5
plt.rcParams['font.size'] = FONT_SIZE

data = {}

with open(filename, 'r', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            ber = float(row['ber'])
            if abs(ber - target_ber) > 1e-9:
                continue
            
            tcp = row['tcp']
            delay_str = row['delay']

            delay_val = int(delay_str.replace('ms', '').strip())
            
            mean = float(row['mean'])
            error = float(row[target_off_col])
            
            if tcp not in data:
                data[tcp] = []
            data[tcp].append((delay_val, mean, error))
            
        except ValueError:
            continue

plt.figure(figsize=(10, 6))
markers = ['o', 's', '^', 'D', 'v'] 

for i, tcp in enumerate(sorted(data.keys())):
    values = data[tcp]
    values.sort(key=lambda x: x[0])
    
    delays = [v[0] for v in values]
    means = [v[1] for v in values]
    errors = [v[2] for v in values]
    
    plt.errorbar(delays, means, yerr=errors, label=tcp, 
                 marker=markers[i % len(markers)], capsize=4, linestyle='-')

plt.xlabel('Atraso (ms)')
plt.ylabel('Vazão (Kbps)')
plt.title(f'Vazão vs Atraso (BER = {target_ber})')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)

# Ensure x-axis ticks match the specific delays in the data
all_delays = sorted(list(set(d for vals in data.values() for d, _, _ in vals)))
plt.xticks(all_delays, [f'{d}ms' for d in all_delays])
plt.show()
