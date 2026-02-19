# load in data and packages
import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely import wkt
import os
import numpy as np

current_wd = os.getcwd()
print(f"Working directory is now: {current_wd}")
script_dir = Path(current_wd)

violation_level = gpd.read_file(script_dir / '../data/derived-data/Building_Violations_w_ACS.gpkg')
tract_month_level = pd.read_csv(script_dir / '../data/derived-data/tract_month_level_violations.csv')

#### exploratory plots 
import matplotlib.pyplot as plt

tract_level = (
    violations_tract_month
    .groupby("GEOID")
    .agg({
        "violations_per_1000": "mean",
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

# distribution of violation types

# top violations seasonally (e.g. heat in winter)
# number of violations per capita compared with income

# reason for violation (complaint vs regular)
# fine amount / case outcome