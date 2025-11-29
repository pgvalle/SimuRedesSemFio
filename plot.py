import matplotlib
matplotlib.use('gtk3agg') # Keeping your backend setting

import matplotlib.pyplot as plt
import numpy as np
import csv

# --- CONFIGURATION ---
filename = 'results-99.csv'
target_delay = input('target delay: ')

# --- 1. LOAD AND FILTER DATA (Replacing Pandas) ---
filtered_data = []
found_variants = set()
found_bers = set()

# A dictionary to act as a fast lookup: (variant, ber) -> (mean, ci)
data_lookup = {}

with open(filename, 'r', newline='') as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        # Filter by delay immediately
        # Note: We strip whitespace just in case the CSV has spaces like ' 1ms'
        if row['delay'].strip() == target_delay:

            # Extract values
            variant = row['tcp']

            # Convert numeric strings to floats
            try:
                ber = float(row['ber'])
                mean_val = float(row['mean'])
                ci_val = float(row['off'])
            except ValueError:
                print(f'Skipping invalid row: {row}')
                continue

            # Store for plotting
            found_variants.add(variant)
            found_bers.add(ber)

            # Save to lookup table for easy access later
            data_lookup[(variant, ber)] = (mean_val, ci_val)

# Convert sets to sorted lists
variants = sorted(list(found_variants))
bers = sorted(list(found_bers))

# --- PLOTTING ---
# Setup the plot
x = np.arange(len(bers))  # the label locations
width = 0.1  # the width of the bars
multiplier = 0

fig, ax = plt.subplots(layout='constrained')

# Loop through each TCP variant
for variant in variants:
    means = []
    cis = []

    # For every BER on the X-axis, find the matching throughput for this variant
    for b in bers:
        # Look up the value in our dictionary.
        # Default to (0, 0) if this specific combo doesn't exist
        val = data_lookup.get((variant, b), (0.0, 0.0))
        means.append(val[0])
        cis.append(val[1])

    # Calculate bar offset
    offset = width * multiplier
    rects = ax.bar(x + offset, means, width, yerr=cis, label=variant, capsize=4)
    multiplier += 1

# --- STYLING ---
ax.set_ylabel('Throughput (Mbps)')
ax.set_title(f'TCP Performance with delay = {target_delay}')
# Center the x-ticks in the middle of the group of bars
ax.set_xticks(x + width * (len(variants) - 1) / 2)
# Format BER labels (using scientific notation often looks cleaner for BER)
ax.set_xticklabels([f'ber={100*d}%' for d in bers])
ax.legend(title='TCP Variant')
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Save and Show
plt.savefig(f'result_delay_{target_delay}.pdf')
plt.show()
