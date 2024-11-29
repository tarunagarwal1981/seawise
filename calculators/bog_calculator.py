import streamlit as st
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium
import searoute as sr
from fuzzywuzzy import process

# Load World Ports Data
@st.cache_data
def load_world_ports():
    """Load and cache world ports data"""
    return pd.read_csv("UpdatedPub150.csv")  # Replace with your CSV path

# Distance and Route Plotting Functions
def route_distance(origin, destination, world_ports_data):
    """Calculate route distance between two ports"""
    try:
        origin_port = world_port_index(origin, world_ports_data)
        destination_port = world_port_index(destination, world_ports_data)
        origin_coords = [float(origin_port['Longitude']), float(origin_port['Latitude'])]
        destination_coords = [float(destination_port['Longitude']), float(destination_port['Latitude'])]
        sea_route = sr.searoute(origin_coords, destination_coords, units="naut")
        return int(sea_route['properties']['length'])
    except Exception as e:
        st.error(f"Error calculating distance between {origin} and {destination}: {str(e)}")
        return 0

def world_port_index(port_to_match, world_ports_data):
    """Find best matching port from world ports data"""
    best_match = process.extractOne(port_to_match, world_ports_data['Main Port Name'])
    return world_ports_data[world_ports_data['Main Port Name'] == best_match[0]].iloc[0]

def plot_combined_route(laden_ports, ballast_ports, world_ports_data):
    """Plot combined route on a single Folium map"""
    m = folium.Map(location=[0, 0], zoom_start=2)
    all_ports = laden_ports + ballast_ports

    if len(all_ports) >= 2 and all(all_ports):
        coordinates = []
        for i in range(len(all_ports) - 1):
            try:
                start_port = world_port_index(all_ports[i], world_ports_data)
                end_port = world_port_index(all_ports[i + 1], world_ports_data)
                start_coords = [float(start_port['Latitude']), float(start_port['Longitude'])]
                end_coords = [float(end_port['Latitude']), float(end_port['Longitude'])]
                
                folium.Marker(
                    start_coords,
                    popup=all_ports[i],
                    icon=folium.Icon(color='green' if i == 0 else 'blue')
                ).add_to(m)
                
                if i == len(all_ports) - 2:
                    folium.Marker(
                        end_coords,
                        popup=all_ports[i + 1],
                        icon=folium.Icon(color='red')
                    ).add_to(m)
                
                route = sr.searoute(start_coords[::-1], end_coords[::-1])
                folium.PolyLine(
                    locations=[list(reversed(coord)) for coord in route['geometry']['coordinates']], 
                    color="red",
                    weight=2,
                    opacity=0.8
                ).add_to(m)
                
                coordinates.extend([start_coords, end_coords])
            except Exception as e:
                st.error(f"Error plotting route for {all_ports[i]} to {all_ports[i + 1]}: {str(e)}")
        
        if coordinates:
            m.fit_bounds(coordinates)
    
    return m

# BOG Calculation Functions
def calculate_temperature_effect(base_bog_rate, ambient_temp, reference_temp=19.5):
    """Calculate BOG rate adjustment for ambient temperature"""
    temp_difference = ambient_temp - reference_temp
    adjustment = (temp_difference / 10) * 0.025
    return base_bog_rate + adjustment

def calculate_sea_state_effect(base_bog_rate, wave_height):
    """Calculate BOG rate adjustment for sea state"""
    if wave_height < 1:
        return 0
    elif wave_height < 2:
        return 0.005
    elif wave_height < 4:
        return 0.01
    else:
        return 0.02

def calculate_solar_effect(base_bog_rate, solar_radiation):
    """Calculate BOG rate adjustment for solar radiation"""
    solar_factors = {'Low': 0.005, 'Medium': 0.015, 'High': 0.025}
    return solar_factors.get(solar_radiation, 0)

def calculate_adjusted_bog(cargo_volume, base_bog_rate, time, ambient_temp, wave_height, solar_radiation):
    """Calculate BOG with environmental adjustments"""
    if cargo_volume > 0 and base_bog_rate > 0 and time > 0:
        temp_adjusted_rate = calculate_temperature_effect(base_bog_rate, ambient_temp)
        sea_state_adjustment = calculate_sea_state_effect(base_bog_rate, wave_height)
        solar_adjustment = calculate_solar_effect(base_bog_rate, solar_radiation)
        
        total_rate = temp_adjusted_rate + sea_state_adjustment + solar_adjustment
        daily_bog = cargo_volume * (total_rate / 100)
        total_bog = daily_bog * time
        
        return round(total_bog, 2), round(total_rate, 4)
    return 0, 0

# Enhanced Voyage Section
def create_voyage_section(leg_type, world_ports_data):
    st.subheader(f"{leg_type} Leg Details")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        voyage_from = st.text_input(f"{leg_type} From Port", key=f"{leg_type}_from")
    with col2:
        voyage_to = st.text_input(f"{leg_type} To Port", key=f"{leg_type}_to")
    with col3:
        if voyage_from and voyage_to:
            distance = route_distance(voyage_from, voyage_to, world_ports_data)
            st.number_input(f"{leg_type} Distance (NM)", value=distance, disabled=True, key=f"{leg_type}_distance")
        else:
            distance = 0
    
    col1, col2 = st.columns(2)
    with col1:
        cargo_volume = st.number_input(f"{leg_type} Cargo Volume (m³)", min_value=0.0, step=100.0, key=f"{leg_type}_cargo_volume")
        bog_rate = st.number_input(f"{leg_type} Base BOG Rate (%)", min_value=0.0, max_value=100.0, value=0.15, step=0.01, key=f"{leg_type}_bog_rate")
    with col2:
        ambient_temp = st.number_input(f"{leg_type} Ambient Temperature (°C)", min_value=-20.0, max_value=45.0, value=19.5, step=0.5, key=f"{leg_type}_temp")
        wave_height = st.number_input(f"{leg_type} Wave Height (m)", min_value=0.0, max_value=10.0, value=1.0, step=0.5, key=f"{leg_type}_waves")
        solar_radiation = st.selectbox(f"{leg_type} Solar Radiation Level", options=['Low', 'Medium', 'High'], key=f"{leg_type}_solar")
    
    return {
        'voyage_from': voyage_from,
        'voyage_to': voyage_to,
        'distance': distance,
        'cargo_volume': cargo_volume,
        'bog_rate': bog_rate,
        'ambient_temp': ambient_temp,
        'wave_height': wave_height,
        'solar_radiation': solar_radiation
    }

# Main Function
def show_bog_calculator():
    st.title("Enhanced BOG Calculator with Combined Route Map")
    st.markdown("""
    ### Features:
    1. Single route map for Laden and Ballast legs.
    2. Automated distance calculation based on port selection.
    3. Comprehensive BOG calculations with weather adjustments.
    """)
    
    world_ports_data = load_world_ports()
    
    st.markdown("---")
    laden_data = create_voyage_section("Laden", world_ports_data)
    st.markdown("---")
    ballast_data = create_voyage_section("Ballast", world_ports_data)
    st.markdown("---")
    
    # Combine routes and plot map
    laden_ports = [laden_data['voyage_from'], laden_data['voyage_to']] if laden_data['voyage_from'] and laden_data['voyage_to'] else []
    ballast_ports = [ballast_data['voyage_from'], ballast_data['voyage_to']] if ballast_data['voyage_from'] and ballast_data['voyage_to'] else []
    
    route_map = plot_combined_route(laden_ports, ballast_ports, world_ports_data)
    st_folium(route_map, width=800, height=500)
    
    # BOG Calculations
    laden_bog, laden_rate = calculate_adjusted_bog(
        laden_data['cargo_volume'], laden_data['bog_rate'], laden_data['distance'] / 12,  # Assuming 12 knots avg speed
        laden_data['ambient_temp'], laden_data['wave_height'], laden_data['solar_radiation']
    )
    ballast_bog, ballast_rate = calculate_adjusted_bog(
        ballast_data['cargo_volume'], ballast_data['bog_rate'], ballast_data['distance'] / 12,
        ballast_data['ambient_temp'], ballast_data['wave_height'], ballast_data['solar_radiation']
    )
    
    st.markdown("### BOG Summary")
    st.write(f"Laden Leg: {laden_bog} m³ (Adjusted Rate: {laden_rate}%)")
    st.write(f"Ballast Leg: {ballast_bog} m³ (Adjusted Rate: {ballast_rate}%)")

if __name__ == "__main__":
    st.set_page_config(
        page_title="BOG Calculator",
        page_icon="🚢",
        layout="wide"
    )
    show_bog_calculator()
