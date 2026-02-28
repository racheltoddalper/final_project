# Dashboard code will go here. 


# to do: 
# fix tooltips on first two graphs
# remove categories: other and permits
# fix cropping of scatterplot
# add address to map tooltip
# consider adding a category for all

from altair.vegalite.v5.api import Chart
import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk
from pathlib import Path
import os
import altair as alt

st.set_page_config(layout="wide")

# Load Data
@st.cache_data
def load_data():
    BASE_DIR = Path(__file__).resolve().parents[1]
    data_path = BASE_DIR / "data" / "derived-data" / "Building_Violations_w_ACS.gpkg"
    gdf = gpd.read_file(data_path)
    gdf = gdf.rename(columns={
    "VIOLATION DATE": "violation_date",
    "VIOLATION DESCRIPTION": "violation_description",
    "VIOLATION STATUS": "violation_status"
    })
    gdf["violation_date"] = pd.to_datetime(gdf["violation_date"])
    gdf["violation_date"] = gdf["violation_date"].dt.strftime("%Y-%m-%d")
    #gdf["violation_date"] = pd.to_datetime(gdf["violation_date"])
    #gdf["year_month"] = gdf["violation_date"].dt.to_period("M").astype(str)

    return gdf

gdf = load_data()

# Sidebar Category Toggle
categories = sorted(gdf["violation_category"].dropna().unique())

selected_category = st.sidebar.selectbox(
    "Select Violation Category",
    categories
)


st.title("Chicago Building Violations from 2024-2026: {}".format(selected_category))

filtered = gdf[gdf["violation_category"] == selected_category].copy()

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

st.write("Number of violations shown:", len(filtered))

st.subheader("Violations per 1,000 vs Per Capita Income (Tract Level)")

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
    ),
    tooltip=[
        "income_quintile",
        "INSPECTION CATEGORY",
        alt.Tooltip("category_violations_per_1000:Q", format=".2f")
    ]
).properties(
    width=400,
    height=500
)

scatter = alt.Chart(tract_level).mark_circle(size=60, opacity=0.6).encode(
    x=alt.X("per_cap_inc:Q", title="Per Capita Income"),
    y=alt.Y("violations_per_1000:Q", title="Violations per 1,000 Residents"),
    tooltip=[
        "GEOID",
        "per_cap_inc",
        "violations_per_1000",
        "violations"
    ]
)

trendline = alt.Chart(tract_level).transform_regression(
    "per_cap_inc",
    "violations_per_1000"
).mark_line(size=3, color="black").encode(
    x="per_cap_inc:Q",
    y="violations_per_1000:Q"
)

chart = (scatter + trendline).properties(
    width=700,
    height=500
)

col1, col2 = st.columns(2)

with col1:
    st.altair_chart(chart)

with col2:
    st.altair_chart(bar_chart)

# Month filtering for Map Only 
#months = sorted(filtered["year_month"].dropna().unique().tolist())
#month_options = ["All Months"] + months

#selected_month = st.select_slider(
   # "Select Month for Map",
    #options=month_options,
    #value="All Months"
#)

#if selected_month == "All Months":
   # map_data = filtered
#else:
   # map_data = filtered[filtered["year_month"] == selected_month]

map_data = filtered

# PyDeck Layer
st.subheader("Interactive Map")
st.markdown("""
<div style="display: flex; gap: 30px; align-items: center;">
    <div><span style="color:rgb(255,0,0); font-size:20px;">●</span> OPEN</div>
    <div><span style="color:rgb(0,200,0); font-size:20px;">●</span> COMPLIED</div>
    <div><span style="color:rgb(150,150,150); font-size:20px;">●</span> Other</div>
</div>
""", unsafe_allow_html=True)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_data,
    get_position='[LONGITUDE, LATITUDE]',
    get_radius=50,   
    get_fill_color="""
    violation_status === 'OPEN'
        ? [255, 0, 0, 180]
        : violation_status === 'COMPLIED'
            ? [0, 200, 0, 180]
            : [150, 150, 150, 140]
""",
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=41.8781,
    longitude=-87.6298,
      zoom=10,
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={
    "html": "<b>Category:</b> {violation_category}<br/><b>Date:</b> {violation_date}<br/><b>Description:</b> {violation_description}",
    "style": {"backgroundColor": "steelblue", "color": "white"},
    },   
)

st.pydeck_chart(deck)
