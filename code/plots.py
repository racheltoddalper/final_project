# load in data and packages
import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely import wkt
import os
import numpy as np
import matplotlib.pyplot as plt

current_wd = os.getcwd()
print(f"Working directory is now: {current_wd}")
script_dir = Path(current_wd)

violation_level = gpd.read_file(script_dir / '../data/derived-data/Building_Violations_w_ACS.gpkg')
tract_month_level = pd.read_csv(script_dir / '../data/derived-data/tract_month_level_violations.csv')

violation_type_cols = [
    col for col in tract_month_level.columns
    if col not in ["GEOID", "year_month", "violations_count",
                   "population", "per_cap_inc",
                   "violations_per_1000"]
]

#### exploratory plots 
tract_level = (
    tract_month_level
    .groupby("GEOID")
    .agg({
        "violations_per_1000": "sum",
        "per_cap_inc": "first"
    })
    .reset_index()
)

plt.figure()

plt.scatter(
    tract_level["per_cap_inc"],
    tract_level["violations_per_1000"],
    alpha=0.4
)

plt.xlabel("Per Capita Income")
plt.ylabel("Avg Violations per 1,000")

plt.title("Average Violations vs Income (Tract Level)")

plt.show()

# income vs violations by type (aggregated to tract level)
tract_totals = (
    tract_month_level
    .groupby("GEOID")
    .agg({
        "violations_count": "sum",
        **{col: "sum" for col in violation_type_cols},
        "population": "first",
        "per_cap_inc": "first"
    })
    .reset_index()
)

median_income = tract_totals["per_cap_inc"].median()

for col in violation_type_cols:
    
    y_col = col
    
    plt.figure()
    plt.scatter(
        tract_totals["per_cap_inc"],
        tract_totals[y_col]
    )

    plt.axvline(median_income)
    
    plt.xlabel("Per Capita Income")
    plt.ylabel(col)
    plt.title(f"{col} vs Income (2024–2026 Total)")
    
    plt.show()

# potential seasonal trends
monthly_avg = (
    tract_month_level
    .groupby("year_month")["Heating / HVAC / Boilers_per_1000"]
    .mean()
    .reset_index(name="avg_violations")
)

plt.figure()

plt.bar(
    monthly_avg["year_month"],
    monthly_avg["avg_violations"]
)

plt.xlabel("Month")
plt.ylabel("Average Heat Related Violations Across Tracts")
plt.title("Average Monthly Violations per Tract (2024–2026)")

plt.xticks(rotation=45)

plt.show()

# distribution of violation types
# reason for violation (complaint vs regular)
# fine amount / case outcome