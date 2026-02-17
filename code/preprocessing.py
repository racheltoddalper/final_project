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

acs_gdf.to_file(script_dir / '../data/derived-data/income_tract.gpkg')

# Merge building and ordinance violation data with ACS income data
