from datetime import datetime

import pandas as pd

# Paths to data file
co2_path = "ICOS_ATC_L2_L2-2024.1_HPB_131.0_CTS.CO2"
mto_path = "ICOS_ATC_L2_L2-2024.1_HPB_131.0_CTS.MTO"

# 1) Read CO₂ file
#   - Skip the 47 header lines
#   - Columns are semicolon‐separated
#   - We only need: Year, Month, Day, Hour, Minute, and co2
co2_cols = [
    "Year", "Month", "Day", "Hour", "Minute", "co2"
]
co2_df = pd.read_csv(
    co2_path,
    sep=";",
    skiprows=46,
    usecols=co2_cols
)

# 1.1) keep only 2022

co2_df = co2_df[co2_df.Year == 2022]

# 2) Construct a pandas datetime from Year–Month–Day–Hour–Minute
co2_df["TIMESTAMP"] = pd.to_datetime(
    co2_df[["Year", "Month", "Day", "Hour", "Minute"]]
)

# Keep only TIMESTAMP and co2 columns
co2_df = co2_df[["TIMESTAMP", "co2"]]

# 3) Read meteorology (MTO) file
#   - Skip the 35 header lines
#   - Columns are semicolon‐separated
#   - We only need: Year, Month, Day, Hour, Minute, and AT (air temperature)
mto_cols = [
    "Year", "Month", "Day", "Hour", "Minute", "AT"
]
mto_df = pd.read_csv(
    mto_path,
    sep=";",
    skiprows=35,
    usecols=mto_cols
)

# 4) Construct a pandas datetime from Year–Month–Day–Hour–Minute
mto_df["TIMESTAMP"] = pd.to_datetime(
    mto_df[["Year", "Month", "Day", "Hour", "Minute"]]
)
# Keep only TIMESTAMP and AT columns
mto_df = mto_df[["TIMESTAMP", "AT"]]

# 5) Merge the two DataFrames on TIMESTAMP (hourly)
merged = pd.merge(
    co2_df,
    mto_df,
    on="TIMESTAMP",
    how="inner"
)

# 6) Sort by TIMESTAMP to ensure chronological order
merged = merged.sort_values("TIMESTAMP").reset_index(drop=True)

ref_time = datetime(2022, 1, 1, 0, 0, 0)

# 7) Transform date to hours
merged['time'] = (
        (merged['TIMESTAMP'] - ref_time).dt.total_seconds() / 3600
).astype(int)

merged = merged[["time", "co2", "AT"]]

merged = merged[(merged["time"]<15*24) & (merged["co2"]>-700) & (merged["AT"]>-700)]

# 8) Save the result to CSV
output_path = "data.csv"
merged.to_csv(output_path, index=False)
print(f"Data saved to: {output_path}")