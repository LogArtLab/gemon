
import csv

import matplotlib.pyplot as plt

from nodes import VariablePWLNode, IntegralWindowNode, MultiplyByConst, HigherThanNode, LowerThanNode, FilterNode


def remove_zeros(points):
    return [a for a, b in zip(points[0], points[1]) if b < 0.00001], [b for a, b in zip(points[0], points[1]) if
                                                                      b < 0.0001]


def get_data_iterator(csv_path):
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)
        for row in reader:
            yield float(row[0]), float(row[1])


data_path = 'data/data.csv'
data_iterator = get_data_iterator(data_path)

G = VariablePWLNode()
phi_AR = HigherThanNode(180)
phi_BR = LowerThanNode(70)

int_TAR = IntegralWindowNode(180)
int_TBR = IntegralWindowNode(180)
phi_TAR = MultiplyByConst(1 / 180)
phi_TBR = MultiplyByConst(1 / 180)

int_G = IntegralWindowNode(180)
mean_G = MultiplyByConst(1 / 180)

filter_G_AR = FilterNode()
int_G_filtered_AR = IntegralWindowNode(180)
mean_G_filtered_AR = MultiplyByConst(1 / 180)

filter_G_BR = FilterNode()
int_G_filtered_BR = IntegralWindowNode(180)
mean_G_filtered_BR = MultiplyByConst(1 / 180)

## 1
G.to(phi_AR.receive)
phi_AR.to(int_TAR.receive)
int_TAR.to(phi_TAR.receive)

## 2
G.to(phi_BR.receive)
phi_BR.to(int_TBR.receive)
int_TBR.to(phi_TBR.receive)

## 3
G.to(int_G.receive)
int_G.to(mean_G.receive)

## 4
G.to(filter_G_AR.receive_left)
phi_AR.to(filter_G_AR.receive_right)
filter_G_AR.to(int_G_filtered_AR.receive)
int_G_filtered_AR.to(mean_G_filtered_AR.receive)

## 5
G.to(filter_G_BR.receive_left)
phi_BR.to(filter_G_BR.receive_right)
filter_G_BR.to(int_G_filtered_BR.receive)
int_G_filtered_BR.to(mean_G_filtered_BR.receive)

glucose = G.observe()
mean_glucose = mean_G.observe()
mean_glucose_filtered_AR = mean_G_filtered_AR.observe()
mean_glucose_filtered_BR = mean_G_filtered_BR.observe()
mean_TAR = phi_TAR.observe()
mean_TBR = phi_TBR.observe()

############
# --- Font sizes ---
LABEL_FONT = 12
TITLE_FONT = 13
TICK_FONT = 11
LEGEND_FONT = 11
FIG_WIDTH, FIG_HEIGHT = 10, 6  # inches
DPI = 800


plt.ion()
# === Figure 1: CGM + TAR% + TBR% ===
fig, axs = plt.subplots(4, 1, figsize=(FIG_WIDTH, FIG_HEIGHT), sharex=True, gridspec_kw={'hspace': 0.35})
TAR_threshold = 180
TBR_threshold = 70

for ax in axs:
    ax.set_xlim(0, 3000)
axs[0].set_ylim(0,400)
axs[1].set_ylim(-0.1,1.2)
axs[2].set_ylim(-2,350)
axs[3].set_ylim(-1,40)

for row_tuple in data_iterator:
    time, g = row_tuple
    G.receive(time, g)

    axs[0].plot(*(glucose.get_points()),
                label='CGM', color='black', marker='o', markersize=3, linestyle='-')
    axs[0].axhline(TAR_threshold, color='red', linestyle='--', linewidth=1, label='TAR Threshold (180)')
    axs[0].axhline(TBR_threshold, color='blue', linestyle='--', linewidth=1, label='TBR Threshold (70)')
    axs[0].fill_between(glucose.get_points()[0], 70, 180, color='gray', alpha=0.1, label='TIR Range')
    axs[0].set_title('CGM Trace with Thresholds', fontsize=TITLE_FONT)
    axs[0].tick_params(labelsize=TICK_FONT)
    axs[0].grid(True)

    # TAR %
    axs[1].plot(*(mean_TAR.get_points()), color='red', label='$\psi_{TAR}$', linestyle='--')
    axs[1].plot(*(mean_TBR.get_points()), color='blue', label='$\psi_{TBR}$', linestyle='--')
    axs[1].set_title('Time Above Range (>180 mg/dL) and Time Below Range (<70 mg/dL)', fontsize=TITLE_FONT)
    axs[1].tick_params(labelsize=TICK_FONT)
    axs[1].grid(True)

    # TBR %
    points = remove_zeros(mean_glucose_filtered_AR.get_points())
    axs[2].scatter(*(points), color='k', label='$\psi_{\mu GBR} = und$', s=30, marker="s")
    axs[2].plot(*(mean_glucose_filtered_AR.get_points()), color='red', label='$\psi_{\mu GAR}$')
    axs[2].set_title('Mean Glucose conditional to level above 180 mg/dL', fontsize=TITLE_FONT)
    axs[2].tick_params(labelsize=TICK_FONT)
    axs[2].grid(True)

    # TBR %
    points = remove_zeros(mean_glucose_filtered_BR.get_points())
    axs[3].scatter(*(points), color='k', label='$\psi_{\mu GBR} = und$', s=30, marker="s")
    axs[3].plot(*(mean_glucose_filtered_BR.get_points()), color='blue', label='$\psi_{\mu GBR}$')
    axs[3].set_title('Mean Glucose conditional to level below 70 mg/dL', fontsize=TITLE_FONT)
    axs[3].tick_params(labelsize=TICK_FONT)
    axs[3].grid(True)
    plt.draw()
    plt.pause(0.1)

plt.ioff()
plt.show()
