from nodes import VariablePWLNode, IntegralWindowNode, MultiplyByConst, HigherThanNode, LowerThanNode, FilterNode

import csv

def row_iterator(csv_path):
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)
        for row in reader:
            yield float(row[0]),float(row[1])

csv_path = 'data/data.csv'
iterator = row_iterator(csv_path)


G = VariablePWLNode()
phi_AR = HigherThanNode(180)
phi_BR = LowerThanNode(70)

int_TAR = IntegralWindowNode(180)
int_TBR = IntegralWindowNode(180)
phi_TAR = MultiplyByConst(1 / 180)
phi_TBR = MultiplyByConst(1 / 180)

int_G = IntegralWindowNode(180)
mean_G = MultiplyByConst(1 / 180)

filter_G = FilterNode()
int_G_filtered = IntegralWindowNode(180)
mean_G_filtered = MultiplyByConst(1 / 180)

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
G.to(filter_G.receive_left)
phi_AR.to(filter_G.receive_right)
filter_G.to(int_G_filtered.receive)
int_G_filtered.to(mean_G_filtered.receive)

glucose = G.observe()
mean_glucose = mean_G.observe()
mean_glucose_filtered = mean_G_filtered.observe()
mean_TAR = phi_TAR.observe()
mean_TBR = phi_TBR.observe()

############
# --- Font sizes ---
LABEL_FONT = 12
TITLE_FONT = 13
TICK_FONT = 11
LEGEND_FONT = 11

import matplotlib.pyplot as plt
import os
import matplotlib.dates as mdates

plt.ion()

# === Figure 1: CGM + TAR% + TBR% ===
fig, axs = plt.subplots(3, 1, figsize=(10, 8), sharex=True, gridspec_kw={'hspace': 0.35})
# locator = mdates.MinuteLocator(interval=1)
# formatter = mdates.DateFormatter('%M')
# --- Thresholds and rolling window ---
TAR_threshold = 180
TBR_threshold = 70
frame_idx = 0
for row_tuple in iterator:
    time, g = row_tuple
    G.receive(time,g)

    axs[0].plot(*(glucose.get_points()),
                label='CGM', color='black', marker='o', markersize=3, linestyle='-')
    axs[0].axhline(TAR_threshold, color='red', linestyle='--', linewidth=1, label='TAR Threshold (180)')
    axs[0].axhline(TBR_threshold, color='blue', linestyle='--', linewidth=1, label='TBR Threshold (70)')
    axs[0].fill_between(glucose.get_points()[0], 70, 180, color='gray', alpha=0.1, label='TIR Range')
    axs[0].set_ylabel('Glucose (mg/dL)', fontsize=LABEL_FONT)
    axs[0].set_title('CGM Trace with Thresholds', fontsize=TITLE_FONT)
    #axs[0].legend(fontsize=LEGEND_FONT)
    axs[0].tick_params(labelsize=TICK_FONT)
    axs[0].grid(True)

    # TAR %
    axs[1].plot(*(mean_TAR.get_points()), color='red', label='TAR %')
    axs[1].set_ylabel('TAR (%)', fontsize=LABEL_FONT)
    axs[1].set_title('Time Above Range (>180 mg/dL)', fontsize=TITLE_FONT)
    #axs[1].legend(fontsize=LEGEND_FONT)
    axs[1].tick_params(labelsize=TICK_FONT)
    axs[1].grid(True)

    # TBR %
    axs[2].plot(*(mean_TBR.get_points()), color='blue', label='TBR %')
    axs[2].set_ylabel('TBR (%)', fontsize=LABEL_FONT)
    axs[2].set_title('Time Below Range (<70 mg/dL)', fontsize=TITLE_FONT)
    #axs[2].legend(fontsize=LEGEND_FONT)
    axs[2].tick_params(labelsize=TICK_FONT)
    axs[2].grid(True)

    # axs[2].xaxis.set_major_locator(locator)
    # axs[2].xaxis.set_major_formatter(formatter)



    # plt.plot(*(glucose.get_points()))
    # plt.plot(*(mean_glucose.get_points()))
    # plt.plot(*(mean_TAR.get_points()))
    # plt.plot(*(mean_TBR.get_points()))
    # plt.plot(*(mean_glucose_filtered.get_points()))
    # plt.ylabel('some numbers')
    plt.draw()
    plt.pause(0.5)
    #filename = os.path.join("fig/", f'plot_{frame_idx:04d}.png')
    #fig.savefig(filename)
    frame_idx+=1

plt.ioff()
plt.show()

