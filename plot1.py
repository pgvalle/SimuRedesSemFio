import matplotlib
matplotlib.use('gtk3agg') # Keeping your backend setting

import matplotlib.pyplot as plt
import numpy as np
import csv

filename = 'results.csv'
targetDelay = input('target delay: ')
targetOff = input('target confidence interval: ')

FONT_SIZE = 11.5
plt.rcParams['font.size'] = FONT_SIZE

filteredData = []
foundTCPs = set()
foundBERs = set()

dataLookup = {}

with open(filename, 'r', newline='') as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        if row['delay'].strip() == targetDelay:
            tcp = row['tcp']

            try:
                ber = float(row['ber'])
                mean = float(row['mean'])
                off = float(row[targetOff])
            except ValueError:
                print(f'Skipping invalid row: {row}')
                continue

            foundTCPs.add(tcp)
            foundBERs.add(ber)

            dataLookup[(tcp, ber)] = (mean, off)

tcps = sorted(list(foundTCPs))
bers = sorted(list(foundBERs))


groupDistance = 0.6
x = np.arange(len(bers)) * groupDistance
width = 0.1
multiplier = 0

fig, ax = plt.subplots(layout='constrained')

for tcp in tcps:
    means = []
    offs = []

    for ber in bers:
        val = dataLookup.get((tcp, ber), (0.0, 0.0))
        means.append(val[0])
        offs.append(val[1])

    offset = width * multiplier
    rects = ax.bar(x + offset, means, width, yerr=offs, label=tcp, capsize=4)
    multiplier += 1

ax.set_ylabel('Vazão (Kbps)')
ax.tick_params(axis='y')
ax.set_title(f'Desempenho com atraso = {targetDelay}')
ax.set_xticks(x + width * (len(tcps) - 1) / 2)
ax.set_xticklabels([f'BER={d}' for d in bers])
ax.legend(title='Versão TCP')
ax.grid(axis='y', linestyle='--', alpha=0.7)

plt.show()
