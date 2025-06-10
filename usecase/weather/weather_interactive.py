import csv

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
mean_co2_h = HigherThanNode(400)

temp = VariablePWLNode()
int_temp = IntegralWindowNode(5)
mean_temp = MultiplyByConst(1 / 5)
mean_temp_h = HigherThanNode(60)

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

import matplotlib.pyplot as plt

plt.ion()

# === Figure 1: CGM + TAR% + TBR% ===
fig, axs = plt.subplots(3, 1, figsize=(10, 8), sharex=True, gridspec_kw={'hspace': 0.35})
# locator = mdates.MinuteLocator(interval=1)
# formatter = mdates.DateFormatter('%M')
# --- Thresholds and rolling window ---
frame_idx = 0
for row_tuple in iterator:
    time, co2_value, temp_value = row_tuple
    co2.receive(time, co2_value)
    temp.receive(time, temp_value)

    axs[0].plot(*(co2_obs.get_points()),
                label='Co2', color='black', marker='o', markersize=3, linestyle='-')
    axs[0].plot(*(mean_co2_obs.get_points()), color='red', label='mean co2')
    axs[0].set_ylabel('Co2', fontsize=LABEL_FONT)
    axs[0].set_title('Co2', fontsize=TITLE_FONT)
    # axs[0].legend(fontsize=LEGEND_FONT)
    axs[0].tick_params(labelsize=TICK_FONT)
    axs[0].grid(True)

    # TAR %
    axs[1].plot(*(temp_obs.get_points()),  label='Temp', color='black', marker='o', markersize=3, linestyle='-')
    axs[1].plot(*(mean_temp_obs.get_points()), color='red', label='mean temp')
    axs[1].set_ylabel('Temp', fontsize=LABEL_FONT)
    axs[1].set_title('Temperature', fontsize=TITLE_FONT)
    # axs[1].legend(fontsize=LEGEND_FONT)
    axs[1].tick_params(labelsize=TICK_FONT)
    axs[1].grid(True)

    # # TBR %
    # axs[2].plot(*(mean_co2_obs.get_points()), color='blue', label='mean co2')
    # axs[2].set_ylabel('mean co2', fontsize=LABEL_FONT)
    # axs[2].set_title('mean co2', fontsize=TITLE_FONT)
    # axs[2].tick_params(labelsize=TICK_FONT)
    # axs[2].grid(True)
    #
    # # TBR %
    # axs[3].plot(*(mean_temp_obs.get_points()), color='blue', label='mean temp')
    # axs[3].set_ylabel('mean temp', fontsize=LABEL_FONT)
    # axs[3].set_title('mean temp', fontsize=TITLE_FONT)
    # axs[3].tick_params(labelsize=TICK_FONT)
    # axs[3].grid(True)

    # TBR %
    axs[2].plot(*(and_spec_obs.get_points()), color='blue', label='full')
    axs[2].set_ylabel('full', fontsize=LABEL_FONT)
    axs[2].set_title('full', fontsize=TITLE_FONT)
    # axs[2].legend(fontsize=LEGEND_FONT)
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
    plt.pause(0.2)
    # filename = os.path.join("fig/", f'plot_{frame_idx:04d}.png')
    # fig.savefig(filename)
    frame_idx += 1

plt.ioff()
plt.show()
