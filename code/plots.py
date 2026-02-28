# load in data and packages
from turtle import title

import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely import wkt
import os
import numpy as np
import matplotlib.pyplot as plt
import altair as alt

current_wd = os.getcwd()
print(f"Working directory is now: {current_wd}")
script_dir = Path(current_wd)

violations_gdf = gpd.read_file(script_dir / '../data/derived-data/Building_Violations_w_ACS.gpkg')
violations_gdf = violations_gdf.to_crs(epsg=4326)
tract_month_level = pd.read_csv(script_dir / '../data/derived-data/tract_month_level_violations.csv')

ordinance_gdf = gpd.read_file(script_dir / '../data/derived-data/Ordinance_Violations_w_ACS.gpkg')

violation_type_cols = [
    col for col in tract_month_level.columns
    if col not in ["GEOID", "year_month", "violations_count",
                   "population", "per_cap_inc",
                   "violations_per_1000"]
]

##### not category split chart -> FIGURE 1
filtered = violations_gdf

# Count violations by tract AND inspection category
category_counts = (
    filtered
    .groupby(["GEOID", "INSPECTION CATEGORY"])
    .size()
    .reset_index(name="category_count")
)

# Get total violations per tract
total_counts = (
    filtered
    .groupby("GEOID")
    .size()
    .reset_index(name="total_violations")
)

# Merge totals
category_counts = category_counts.merge(
    total_counts,
    on="GEOID",
    how="left"
)

# Calculate share within tract
category_counts["category_share"] = (
    category_counts["category_count"] /
    category_counts["total_violations"]
)

# Aggregate to tract level
tract_level = (
    filtered
    .groupby("GEOID")
    .agg(
        per_cap_inc=("per_cap_inc", "first"),
        population=("population", "first"),
        violations=("GEOID", "size")  
    )
    .reset_index()
)

# Calculate violations per 1,000 residents
tract_level["violations_per_1000"] = (
    tract_level["violations"] /
    tract_level["population"]
) * 1000

tract_categories = category_counts.merge(
    tract_level,
    on="GEOID",
    how="left"
)

tract_level["income_quintile"] = pd.qcut(
    tract_level["per_cap_inc"],
    5,
    labels=["Q1 (Lowest)", "Q2", "Q3", "Q4", "Q5 (Highest)"]
)

tract_categories = tract_categories.merge(
    tract_level[["GEOID", "income_quintile"]],
    on="GEOID",
    how="left"
)

# calculate population weighted mean
quintile_totals = (
    tract_level
    .groupby("income_quintile")
    .apply(lambda x: pd.Series({
        "weighted_avg_violations_per_1000":
            (x["violations_per_1000"] * x["population"]).sum() /
            x["population"].sum()
    }))
    .reset_index()
)

quintile_category_shares = (
    tract_categories
    .groupby(["income_quintile", "INSPECTION CATEGORY"])
    .apply(lambda x: pd.Series({
        "weighted_share":
            (x["category_share"] * x["population"]).sum() /
            x["population"].sum()
    }))
    .reset_index()
)

quintile_category_summary = quintile_category_shares.merge(
    quintile_totals,
    on="income_quintile",
    how="left"
)

quintile_category_summary["category_violations_per_1000"] = (
    quintile_category_summary["weighted_share"] *
    quintile_category_summary["weighted_avg_violations_per_1000"]
)

label_map = {
    "PERIODIC": "Periodic",
    "COMPLAINT": "Complaint",
    "PERMIT": "License Inspection"
}

quintile_category_summary["INSPECTION CATEGORY"] = (
    quintile_category_summary["INSPECTION CATEGORY"]
    .replace(label_map)
)

bar_chart = alt.Chart(quintile_category_summary).mark_bar().encode(
    x=alt.X(
        "income_quintile:N",
        title="Income Quintile",
        axis=alt.Axis(labelAngle=0)
    ),
    y=alt.Y(
        "category_violations_per_1000:Q",
        title="Violations per 1,000 Residents"
    ),
    color=alt.Color(
        "INSPECTION CATEGORY:N",
        title="Inspection Category"
    )
).properties(
    width=400,
    height=500,
    title="Violations per 1,000 Residents by Income Quintile"
)
bar_chart
bar_chart.save("Violations_by_Income.png", scale_factor=3)

##### Heatmap --> FIGURE 2
filtered = violations_gdf[
    ~violations_gdf["violation_category"].isin(
        ["Permits / Administrative", "Other / Misc"]
    )
].copy()

# Aggregate total violations per tract
tract_level = (
    filtered
    .groupby("GEOID")
    .agg(
        per_cap_inc=("per_cap_inc", "first"),
        population=("population", "first"),
        total_violations=("GEOID", "size")
    )
    .reset_index()
)

# Income quintiles
tract_level["income_quintile"] = pd.qcut(
    tract_level["per_cap_inc"],
    5,
    labels=["Q1 (Lowest)", "Q2", "Q3", "Q4", "Q5 (Highest)"]
)

tract_category = (
    filtered
    .groupby(["GEOID", "violation_category"])
    .size()
    .reset_index(name="category_count")
)

tract_category = tract_category.merge(
    tract_level[["GEOID", "population", "income_quintile"]],
    on="GEOID",
    how="left"
)

tract_category["category_violations_per_1000"] = (
    tract_category["category_count"] /
    tract_category["population"]
) * 1000

heatmap_data = (
    tract_category
    .groupby(["income_quintile", "violation_category"])
    .apply(lambda x: pd.Series({
        "weighted_violations_per_1000":
            (x["category_violations_per_1000"] * x["population"]).sum()
            / x["population"].sum()
    }))
    .reset_index()
)

quintile_order = ["Q1 (Lowest)", "Q2", "Q3", "Q4", "Q5 (Highest)"]

heatmap = alt.Chart(heatmap_data).mark_rect().encode(
    x=alt.X(
        "income_quintile:N",
        sort=quintile_order,
        title="Income Quintile",
        axis=alt.Axis(labelAngle=0)
    ),
    y=alt.Y(
        "violation_category:N",
        title="Violation Category"
    ),
    color=alt.Color(
        "weighted_violations_per_1000:Q",
        title="Violations per 1,000",
        scale=alt.Scale(scheme="blues")
    )
).properties(
    width=500,
    height=350,
    title="Violations per 1,000 by Income Quintile and Category"
)

heatmap
heatmap.save("Heatmap_by_Income.png", scale_factor=3)

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