import numpy as np
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import dash_leaflet as dl
import plotly.graph_objects as go
from pvlib.solarposition import get_solarposition
from geopy.distance import geodesic
from datetime import datetime, timedelta
import pytz
import requests

# Initialize the Dash app
app = Dash(__name__)

# Define the layout of the web interface
app.layout = html.Div([
    html.H1("Solar Production Over a Journey", style={"textAlign": "center"}),

    html.Div([
        html.Label("Surface Area of Panels (m²):"),
        dcc.Input(id="surface_area", type="number", value=10, min=1, step=1),

        html.Label("kW Production per m²:"),
        dcc.Input(id="kw_per_m2", type="number", value=0.2, min=0.01, step=0.01),

        html.Label("Start Date and Time (YYYY-MM-DD HH:MM UTC):"),
        dcc.Input(id="start_date", type="text", value=str(datetime.now(pytz.UTC).strftime("%Y-%m-%d %H:%M"))),

        html.Label("Vessel Speed (km/h):"),
        dcc.Input(id="vessel_speed", type="number", value=20, min=1, step=1),

        html.Label("Enable Cloud Attenuation:"),
        dcc.Checklist(id="cloud_toggle", options=[{"label": "Apply Cloud Attenuation", "value": "on"}], value=[]),
    ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px", "marginBottom": "20px"}),

    html.Div([
        html.Label("Plot Route on Map:"),
        dl.Map(center=(0, 0), zoom=2, children=[
            dl.TileLayer(),
            dl.FeatureGroup(id="feature_group", children=[
                dl.EditControl(id="edit_control", draw={"polyline": True})
            ]),
            dl.Marker(id="map_marker", position=(0, 0))
        ], id="map", style={"height": "400px", "marginBottom": "20px"})
    ]),

    dcc.Graph(id="solar_graph", clickData=None),

    html.Div(id="total_output", style={"textAlign": "center", "marginTop": "20px", "fontSize": "20px"}),
])

# Function to fetch cloud cover data from NASA POWER API
def fetch_cloud_cover(lat, lon, date):
    formatted_date = date.replace("-", "")  # Convert YYYY-MM-DD to YYYYMMDD
    print(f"Fetching cloud cover for {date} at ({lat}, {lon})...")
    url = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=CLOUD_AMT&community=RE&longitude={lon}&latitude={lat}&start={formatted_date}&end={formatted_date}&format=JSON"
    print(f"Requesting URL: {url}")
    response = requests.get(url)
    
    if response.status_code == 200:
        try:
            data = response.json()
            if "properties" in data and "parameter" in data["properties"] and "CLOUD_AMT" in data["properties"]["parameter"]:
                cloud_cover = data["properties"]["parameter"]["CLOUD_AMT"].get(formatted_date, 0)
                print(f"Cloud cover for {date}: {cloud_cover}%")
                return cloud_cover / 100  # Convert to attenuation factor
            else:
                print(f"Unexpected JSON structure: {data}")
        except Exception as e:
            print(f"Error parsing JSON response: {e}")
    else:
        print(f"Failed to fetch cloud cover data for {date}. HTTP Status: {response.status_code}, Response: {response.text}")
    return 0  # Default to no attenuation if data fetch fails

# Callback to calculate solar production over the journey
@app.callback(
    [Output("solar_graph", "figure"),
     Output("total_output", "children")],
    [Input("edit_control", "geojson"),
     Input("surface_area", "value"),
     Input("kw_per_m2", "value"),
     Input("start_date", "value"),
     Input("vessel_speed", "value"),
     Input("cloud_toggle", "value")]
)
def update_solar_production(geojson, surface_area, kw_per_m2, start_date, vessel_speed, cloud_toggle):
    if not geojson or "features" not in geojson or not geojson["features"]:
        return go.Figure().update_layout(title="Invalid Inputs - Please Plot a Route"), "Total Output: Invalid Route"

    coordinates = geojson["features"][0]["geometry"]["coordinates"]
    route_positions = [(lat, lon) for lon, lat in coordinates]
    total_production = 0
    times, production_values = [], []
    current_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC)

    cloud_cover_cache = {}
    apply_cloud = "on" in cloud_toggle

    for i in range(len(route_positions) - 1):
        start, end = route_positions[i], route_positions[i + 1]
        segment_distance = geodesic(start, end).km
        segment_duration = timedelta(hours=segment_distance / vessel_speed)
        num_steps = max(2, int(segment_duration.total_seconds() / 600))

        lats = np.linspace(start[0], end[0], num_steps)
        lons = np.linspace(start[1], end[1], num_steps)
        times_segment = [current_time + timedelta(minutes=10 * j) for j in range(num_steps)]
        current_time += segment_duration

        for j in range(num_steps):
            date_key = times_segment[j].strftime("%Y-%m-%d")
            if date_key not in cloud_cover_cache:
                cloud_cover_cache[date_key] = fetch_cloud_cover(lats[j], lons[j], date_key)
            attenuation = 1 - cloud_cover_cache[date_key] if apply_cloud else 1

            solar_position = get_solarposition(pd.DatetimeIndex([times_segment[j]]), lats[j], lons[j])
            solar_altitude = solar_position["apparent_elevation"].values[0]
            if solar_altitude > 0:
                irradiance_factor = np.sin(np.radians(solar_altitude))
                segment_production = surface_area * kw_per_m2 * irradiance_factor * attenuation
                times.append(times_segment[j])
                production_values.append(segment_production)
                total_production += segment_production * (10 / 60)

    df = pd.DataFrame({"Time": times, "Production (kW)": production_values})
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Production (kW)"], mode="lines", name="Solar Production"))
    fig.update_layout(title="Solar Production Over Journey")
    
    return fig, f"Total Output: {total_production:.2f} kWh"

if __name__ == "__main__":
    app.run(debug=True)
