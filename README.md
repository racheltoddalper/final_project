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
    fire.csv          # Historical fire perimeter data
    canadian_cpi.csv  # Canadian Consumer Price Index data
  derived-data/       # Filtered data and output plots
    fire_filtered.gpkg  # Fire data filtered to post-2015
    cpi_filtered.csv    # CPI data filtered to 2020 onwards
code/
  preprocessing.py    # Filters fire and CPI data
  plot_fires.py       # Plots fire perimeters
```

## Usage

1. Download data:

2. Run preprocessing to filter data:
   ```bash
   python code/preprocessing.py
   ```

3. Generate the fire perimeter plot:
   ```bash
   python code/plot_fires.py
   ```

4. Link to Streamlit app: https://finalproject-rachel.streamlit.app
