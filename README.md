# Chicago Building Code Violations 

This project processes and visualizes data on building code violations in Chicago and how they vary with income. 

## Setup

```bash
conda create --name violations_analysis python=3.11
conda activate violations_analysis
pip install -r requirements.txt
```

## Project Structure

```
data/
  raw-data/           # Raw data files
    Building_Violations_2024-2026   # Chicage building violation-level data
    income_tract.csv  # ACS tract-level income and population data
    shapefiles        # tract shapefiles to merge with ACS data
  derived-data/       # Filtered data and output plots
    
code/
  preprocessing.py    # processes and merges tract geometries, tract - level income data, and violations data
  plot_fires.py       # plots static plots 
```

## Usage

1. Download data at this link and save to data/raw-data:

2. Render final writeup:
   ```bash
   quarto render final_project.qmd
   ```

3. Link to Streamlit app: https://finalproject-rachel.streamlit.app
