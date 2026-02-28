import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely import wkt
import os
import numpy as np

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

# create categories for violation description
desc = violations_gdf["VIOLATION DESCRIPTION"].str.upper()

conditions = [
    desc.str.contains("FIRE|SMOKE|CARB|EGRESS|EXIT|PANIC|SPRINKLER|CORRIDOR", na=False),
    
    desc.str.contains("WIRING|OUTLET|BREAKER|CONDUIT|CIRCUIT|GROUND|ELECTR|FEEDER", na=False),
    
    desc.str.contains("PLUMB|WATER|SEWER|DRAIN|PIPE|TRAP|WASTE|FLUSH|BACKWATER|FAUCET", na=False),
    
    desc.str.contains("HEAT|BOILER|FURNACE|VENT|BREECHING|RELIEF VALVE|HWH", na=False),
    
    desc.str.contains("ROOF|FOUNDATION|WALL|CHIMNEY|PORCH|BALCONY|PARAPET|LINTEL|STRUCTURAL", na=False),
    
    desc.str.contains("RAT|ROACH|MICE|INSECT|UNSANITARY|GARBAGE|DEBRIS|NUISANCE|PIGEON", na=False),
    
    desc.str.contains("WINDOW|DOOR|FLOOR|PAINT|SILL|SCREEN|LOCK|GLASS|CEILING", na=False),
    
    desc.str.contains("PERMIT|PLANS|REGISTER|CERTIFICATE|LICENSE|POST|APPROVAL|REGISTRATION|CONTRACTOR|C OF O", na=False)
]

choices = [
    "Fire & Life Safety",
    "Electrical",
    "Plumbing & Water",
    "Heating / HVAC / Boilers",
    "Structural / Building Envelope",
    "Sanitation / Pests / Waste",
    "Windows / Doors / Interior",
    "Permits / Administrative"
]

violations_merged_gdf["violation_category"] = np.select(conditions, choices, default="Other / Misc")

violations_merged_gdf.to_file(
    script_dir / '../data/derived-data/Building_Violations_w_ACS.gpkg',
    driver="GPKG"
)

ordinance_merged_gdf.to_file(
    script_dir / '../data/derived-data/Ordinance_Violations_w_ACS.gpkg',
    driver="GPKG"
)

# merge violations and ordinance
for df in [violations_merged_gdf, ordinance_merged_gdf]:
    df["ADDRESS"] = df["ADDRESS"].str.strip().str.upper()
    df["VIOLATION DESCRIPTION"] = df["VIOLATION DESCRIPTION"].str.strip().str.upper()

ordinance_merged_gdf["HEARING DATE"] = pd.to_datetime(ordinance_merged_gdf["HEARING DATE"])


violations_merged_gdf["VIOLATION DATE"] = pd.to_datetime(
    violations_merged_gdf["VIOLATION DATE"],
    errors="coerce"
)

ordinance_merged_gdf["VIOLATION DATE"] = pd.to_datetime(
    ordinance_merged_gdf["VIOLATION DATE"],
    errors="coerce"
)

violations_merged_gdf["VIOLATION DATE"] = violations_merged_gdf["VIOLATION DATE"].dt.date
ordinance_merged_gdf["VIOLATION DATE"] = ordinance_merged_gdf["VIOLATION DATE"].dt.date

ordinance_dedup = (
    ordinance_merged_gdf
    .sort_values("HEARING DATE")
    .drop_duplicates(
        subset=["ADDRESS", "VIOLATION DATE", "VIOLATION DESCRIPTION"],
        keep="last"
    )
)

ordinance_dedup["VIOLATION DESCRIPTION"] = (
    ordinance_dedup["VIOLATION DESCRIPTION"]
        .str.replace(r"^\S+\s+", "", regex=True)  
        .str.replace(r"\.$", "", regex=True)      
        .str.strip()
        .str.upper()
)

violations_ordinance_merged = violations_merged_gdf.merge(
    ordinance_dedup[
        ["ADDRESS",
         "VIOLATION DATE",
         "VIOLATION DESCRIPTION",
         "CASE DISPOSITION",
         "IMPOSED FINE"]
    ],
    on=["ADDRESS", "VIOLATION DATE", "VIOLATION DESCRIPTION"],
    how="left",
    validate="m:1"
)

# aggregate to tract - month level for number of violations per capita since 2024
violations_by_type = (
    violations_merged_gdf
    .groupby(["GEOID", "year_month", "violation_category"])
    .size()
    .reset_index(name="count")
)

violations_by_type_wide = (
    violations_by_type
    .pivot(index=["GEOID", "year_month"],
           columns="violation_category",
           values="count")
    .fillna(0)
    .reset_index()
)

total_violations = (
    violations_merged_gdf
    .groupby(["GEOID", "year_month"])
    .size()
    .reset_index(name="violations_count")
)

violations_tract_month = violations_by_type_wide.merge(
    total_violations,
    on=["GEOID", "year_month"],
    how="left"
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

category_cols = [
    col for col in violations_tract_month.columns
    if col not in ["GEOID", "year_month", "violations_count",
                   "population", "per_cap_inc",
                   "violations_per_1000"]
]

for col in category_cols:
    violations_tract_month[f"{col}_per_1000"] = (
        violations_tract_month[col] /
        violations_tract_month["population"] * 1000
    )

violations_tract_month.to_csv(
    script_dir / '../data/derived-data/tract_month_level_violations.csv',
    index=False
)

# Save spatial file version
violations_tract_month_gdf = tracts.merge(
    violations_tract_month,
    on="GEOID",
    how="left"
)

violations_tract_month_gdf.to_file(
    script_dir / '../data/derived-data/tract_month_level_violations.geojson',
    driver="GeoJSON"
)