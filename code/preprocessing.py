import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely import wkt
import os

current_wd = os.getcwd()
print(f"Working directory is now: {current_wd}")
script_dir = Path(current_wd)

# Process building violations 
raw_violations = script_dir / '../data/raw-data/Building_Violations_2024-2026.csv'
output_violations = script_dir / '../data/derived-data/Building_Violations_2024-2026.gpkg'

violations_df = pd.read_csv(raw_violations)
violations_gdf = gpd.GeoDataFrame(
    violations_df,
    geometry=gpd.points_from_xy(
        violations_df['LONGITUDE'],
        violations_df['LATITUDE']
    ),
    crs="EPSG:4326"   
)

violations_gdf = violations_gdf.to_crs("ESRI:102003")
violations_gdf.to_file(output_violations)

# Process ordinance violations:
raw_ordinance = script_dir / '../data/raw-data/Ordinance_Violations_(Buildings)_2024-2026.csv'
output_ordinance = script_dir / '../data/derived-data/Ordinance_Violations_2024-2026.gpkg'

ordinance_df = pd.read_csv(raw_ordinance)
ordinance_gdf = gpd.GeoDataFrame(
    ordinance_df,
    geometry=gpd.points_from_xy(
        ordinance_df['LONGITUDE'],
        ordinance_df['LATITUDE']
    ),
    crs="EPSG:4326"   
)

ordinance_gdf = ordinance_gdf.to_crs("ESRI:102003")
ordinance_gdf.to_file(output_ordinance)

# Process ACS income data taken from https://data2.nhgis.org/main to get tract level population and per capita income
tracts = gpd.read_file(script_dir / "../data/raw-data/shapefiles/US_tract_2024.shp")
acs_data = pd.read_csv(script_dir / '../data/raw-data/income_tract.csv')

acs_gdf = tracts.merge(acs_data, on="GISJOIN", how="inner")
acs_gdf = acs_gdf.rename(columns={"AUO6E001": "population", "AUSYE001": "per_cap_inc"})
acs_subset = acs_gdf[["population", "per_cap_inc", "geometry", "GEOID"]]

acs_subset.to_file(script_dir / '../data/derived-data/income_tract.gpkg')

# Merge building and ordinance violation data with ACS income data
violations_merged_gdf = gpd.sjoin(
    violations_gdf,
    acs_subset,
    how="left",
    predicate="within"
)

ordinance_merged_gdf = gpd.sjoin(
    ordinance_gdf,
    acs_subset,
    how="left",
    predicate="within"
)

violations_merged_gdf.to_file(
    script_dir / '../data/derived-data/Building_Violations_w_ACS.gpkg',
    driver="GPKG"
)

ordinance_merged_gdf.to_file(
    script_dir / '../data/derived-data/Ordinance_Violations_w_ACS.gpkg',
    driver="GPKG"
)

# aggregate to tract - month level for number of violations per capita since 2024
violations_merged_gdf["VIOLATION DATE"] = pd.to_datetime(
    violations_merged_gdf["VIOLATION DATE"],
    errors="coerce"
)
violations_merged_gdf["year"] = violations_merged_gdf["VIOLATION DATE"].dt.year
violations_merged_gdf["month"] = violations_merged_gdf["VIOLATION DATE"].dt.month
violations_merged_gdf["year_month"] = violations_merged_gdf["VIOLATION DATE"].dt.to_period("M")

violations_tract_month = (
    violations_merged_gdf
    .groupby(["GEOID", "year_month"])
    .size()
    .reset_index(name="violations_count")
)

tract_characteristics = (
    violations_merged_gdf[["GEOID", "population", "per_cap_inc"]]
    .drop_duplicates()
)

tract_characteristics = tract_characteristics[
    tract_characteristics["per_cap_inc"] > 0
]

violations_tract_month = violations_tract_month.merge(
    tract_characteristics,
    on="GEOID",
    how="inner"
)

violations_tract_month["violations_per_1000"] = (
    violations_tract_month["violations_count"] /
    violations_tract_month["population"] * 1000
)

violations_tract_month.to_csv(
    script_dir / '../data/derived-data/tract_month_level_violations.csv',
    index=False
)

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
