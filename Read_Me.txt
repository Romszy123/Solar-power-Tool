This script is a Route Calculation System, a web-based application built with Dash and Plotly that allows users to estimate solar energy production along a defined journey route. The system integrates with the NASA POWER API to retrieve cloud cover data, dynamically computing solar output based on solar position and environmental attenuation.

User enters: 
    - Surface area of panels
    - kW production / m2 ( usual panel efficiency is 0.2)
    - Start date and time 
    - Vessel speed in km/h
    - Whether cloud attenuation is to be used or not

Map:
    - User draws the course to be followed by the vessel. 

Output:
    - A graph shows energy production over the duration of the journey. 
    - User can select a point on the graph and see the corresponding point on the map. 

Assumptions:
    - pvlib is used to determine the solar altitude at each segment of the journey. 
    - Solar production determined using a sinusoidal model dependent on sun's altitude at that location. Max altitude = factor 1 production. 
    - Cloud attenuation reduces power production in direct relation to cloud % cover once / day. 
    - Cloud cover retrieved from NASA POWER API.
    - Only historic cloud data available. If no cloud info available, cloud cover defaults to 0. 