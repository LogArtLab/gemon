import csv
import matplotlib.pyplot as plt
from nodes import VariablePWLNode, IntegralWindowNode, MultiplyByConst, HigherThanNode, MinNode


def row_iterator(csv_path):
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)
        for row in reader:
            yield float(row[0]), float(row[1]), float(row[2])

csv_path = 'data/data.csv'
iterator = row_iterator(csv_path)

co2 = VariablePWLNode()
int_co2 = IntegralWindowNode(5)
mean_co2 = MultiplyByConst(1 / 5)
mean_co2_threshold = 422
mean_co2_h = HigherThanNode(mean_co2_threshold)

temp = VariablePWLNode()
int_temp = IntegralWindowNode(5)
mean_temp = MultiplyByConst(1 / 5)
mean_temperature_threshold = 0
mean_temp_h = HigherThanNode(mean_temperature_threshold)

and_spec = MinNode()

co2.to(int_co2.receive)
int_co2.to(mean_co2.receive)
mean_co2.to(mean_co2_h.receive)

temp.to(int_temp.receive)
int_temp.to(mean_temp.receive)
mean_temp.to(mean_temp_h.receive)

mean_co2_h.to(and_spec.receive_left)
mean_temp_h.to(and_spec.receive_right)

co2_obs = co2.observe()
temp_obs = temp.observe()
mean_co2_obs = mean_co2.observe()
mean_temp_obs = mean_temp.observe()
and_spec_obs = and_spec.observe()

############
# --- Font sizes ---
LABEL_FONT = 12
TITLE_FONT = 13
TICK_FONT = 11
LEGEND_FONT = 11

for row_tuple in iterator:
    time, co2_value, temp_value = row_tuple
    co2.receive(time, co2_value)
    temp.receive(time, temp_value)

# ---- Constants (adjust as needed) ----
LABEL_FONT = 12
TITLE_FONT = 13
TICK_FONT = 11
LEGEND_FONT = 11
FIG_WIDTH, FIG_HEIGHT = 10, 6  # inches
DPI = 800

# ---- Create figure & axes ----
fig, axs = plt.subplots(3, 1,
                        figsize=(FIG_WIDTH, FIG_HEIGHT),
                        sharex=True)  # share x‐axis if your x‐data are the same

# ---- CO2 panel ----
axs[0].plot(*co2_obs.get_points(),
            label='CO₂ (ppm)', color='black',
            marker='o', markersize=1.5, linestyle='-')
axs[0].plot(*mean_co2_obs.get_points(),
            color='red', label='Mean CO₂', linestyle='-')
axs[0].axhline(mean_co2_threshold,
               color='red', linestyle='--', linewidth=1,
               label=f'Mean CO₂ Threshold ({mean_co2_threshold:.0f})')
axs[0].set_title('Atmospheric CO₂ Observations', fontsize=TITLE_FONT)
axs[0].legend(fontsize=LEGEND_FONT, loc='upper left')
axs[0].tick_params(labelsize=TICK_FONT)
axs[0].grid(True)

# ---- Temperature panel ----
axs[1].plot(*temp_obs.get_points(),
            label='Temperature (°C)', color='black',
            marker='o', markersize=1.5, linestyle='-')
axs[1].plot(*mean_temp_obs.get_points(),
            color='red', label='Mean Temperature', linestyle='-')
axs[1].axhline(mean_temperature_threshold,
               color='red', linestyle='--', linewidth=1,
               label=f'Mean Temp Threshold ({mean_temperature_threshold:.0f})')
axs[1].set_title('Temperature Observations', fontsize=TITLE_FONT)
axs[1].legend(fontsize=LEGEND_FONT, loc='upper left')
axs[1].tick_params(labelsize=TICK_FONT)
axs[1].grid(True)

# ---- Combined φ_W panel ----
axs[2].plot(*and_spec_obs.get_points(),
            color='blue',
            label=(
              r'$\phi_W(5h,'
              f'{mean_co2_threshold:.0f},'
              f'{mean_temperature_threshold:.0f})$'
            ))
axs[2].set_title(r'$\phi_W$ Formula', fontsize=TITLE_FONT)
axs[2].legend(fontsize=LEGEND_FONT, loc='upper left')
axs[2].tick_params(labelsize=TICK_FONT)
axs[2].grid(True)

# ---- Finalize & export ----
axs[-1].set_xlabel('Time (h)', fontsize=LABEL_FONT)
plt.tight_layout()

# Export high‐res files for publication
plt.savefig('fig/figure_weather.pdf',
            dpi=DPI, bbox_inches='tight')
plt.savefig('fig/figure_weather.png',
            dpi=DPI, bbox_inches='tight')

# Optionally display in‐script
plt.show()