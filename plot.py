import matplotlib
matplotlib.use('gtk3agg') # Keeping your backend setting

import matplotlib.pyplot as plt
import numpy as np
import csv

# --- CONFIGURATION ---
filename = 'results.csv'
targetDelay = input('target delay: ')
targetOff = input('target confidence interval: ')

# --- LOAD AND FILTER DATA ---
filteredData = []
foundTCPs = set()
foundBERs = set()

# A dictionary to act as a fast lookup: (tcp, ber) -> (mean, off)
dataLookup = {}

with open(filename, 'r', newline='') as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        # Filter by delay immediately
        # Note: We strip whitespace just in case the CSV has spaces like ' 1ms'
        if row['delay'].strip() == targetDelay:
            # Extract values
            tcp = row['tcp']

            # Convert numeric strings to floats
            try:
                ber = float(row['ber'])
                mean = float(row['mean'])
                off = float(row[targetOff])
            except ValueError:
                print(f'Skipping invalid row: {row}')
                continue

            # Store for plotting
            foundTCPs.add(tcp)
            foundBERs.add(ber)

            # Save to lookup table for easy access later
            dataLookup[(tcp, ber)] = (mean, off)

# Convert sets to sorted lists
tcps = sorted(list(foundTCPs))
bers = sorted(list(foundBERs))

# --- PLOTTING ---
# Setup the plot
groupDistance = 0.75
x = np.arange(len(bers)) * groupDistance # the label locations
width = 0.1  # the width of the bars
multiplier = 0

fig, ax = plt.subplots(layout='constrained')

# Loop through each TCP variant
for tcp in tcps:
    means = []
    offs = []

    # For every BER on the X-axis, find the matching throughput for this variant
    for ber in bers:
        # Look up the value in our dictionary.
        # Default to (0, 0) if this specific combo doesn't exist
        val = dataLookup.get((tcp, ber), (0.0, 0.0))
        means.append(val[0])
        offs.append(val[1])

    # Calculate bar offset
    offset = width * multiplier
    rects = ax.bar(x + offset, means, width, yerr=offs, label=tcp, capsize=4)
    multiplier += 1

# --- STYLING ---
ax.set_ylabel('Vazão (Kbps)')
ax.set_title(f'Desempenho com atraso = {targetDelay}')
# Center the x-ticks in the middle of the group of bars
ax.set_xticks(x + width * (len(tcps) - 1) / 2)
# Format BER labels (using scientific notation often looks cleaner for BER)
ax.set_xticklabels([f'ber={d}' for d in bers])
# ax.set_ylim(top=2600, bottom=50)
ax.legend(title='Versão TCP')
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Save and Show
# plt.savefig(f'result_delay_{targetDelay}_{targetOff}.pdf')
plt.show()
