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

# Process ACS income data taken from https://data2.nhgis.org/main to get tract level population and per capita income
tracts = gpd.read_file(script_dir / "../data/raw-data/shapefiles/US_tract_2024.shp")
acs_data = pd.read_csv(script_dir / '../data/raw-data/income_tract.csv')

acs_gdf = tracts.merge(acs_data, on="GISJOIN", how="inner")
acs_gdf = acs_gdf.rename(columns={"AUO6E001": "population", "AUSYE001": "per_cap_inc"})
acs_subset = acs_gdf[["population", "per_cap_inc", "geometry", "GEOID"]]

# Merge building and ordinance violation data with ACS income data
violations_merged_gdf = gpd.sjoin(
    violations_gdf,
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
