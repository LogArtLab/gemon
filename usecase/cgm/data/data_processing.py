import pandas as pd
from datetime import datetime

# Paths to data file
input_csv = '1011_0_20210622.csv'
output_csv = 'data.csv'

# 1) Read file
df = pd.read_csv(input_csv, parse_dates=['Date'], dayfirst=False)

# 2) Set a reference time
ref_time = datetime(2021, 6, 23, 0, 0, 0)
df['date_only'] = df['Date'].dt.date

# 3) Keep only two days of measurements
df_filtered = df[
    (df['date_only'] == pd.to_datetime('2021-06-23').date()) |
    (df['date_only'] == pd.to_datetime('2021-06-24').date())
    ].copy()

# 4) Transform date to minutes
df_filtered['minutes'] = (
        (df_filtered['Date'] - ref_time).dt.total_seconds() / 60.0
).astype(int)

# 5) Export only cgm
df_filtered = df_filtered[['minutes', 'CGM (mg / dl)']].copy()
df_filtered.columns = ['time', 'cgm']
df_filtered.to_csv(output_csv, index=False)

print(f"Data saved to: {output_csv}")
