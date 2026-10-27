
import pandas as pd
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
csv_path = project_root / "data" / "processed" / "live_sensor_data.csv"

df = pd.read_csv(csv_path)

print("\n--- Dataset Overview ---")
print(f"File: {csv_path}")
print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns)}")

print("\n--- First 5 Readings ---")
print(df.head().to_string(index=False))

print("\n--- Missing Values ---")
print(df.isnull().sum())

axes = ["ax_g", "ay_g", "az_g"]

print("\n--- Acceleration Statistics ---")
print(df[axes].describe())

print("\n--- Unique Values Per Axis ---")
print(df[axes].nunique())

print("\n--- Number of Unique Sensor Readings ---")
print(df[axes].drop_duplicates().shape[0])
