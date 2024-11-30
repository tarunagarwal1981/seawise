# bog_calculator.py

import streamlit as st
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium
import searoute as sr
from fuzzywuzzy import process

# Helper Functions
@st.cache_data
def load_world_ports():
    """Load and cache world ports data"""
    return pd.read_csv("UpdatedPub150.csv")

def calculate_bog_rate(base_rate, tank_pressure, tank_level, ambient_temp, wave_height, solar_radiation):
    """Calculate BOG rate with all factors"""
    pressure_factor = 1 + ((tank_pressure - 1013) / 1013) * 0.1
    level_factor = 1 + (1 - tank_level/100) * 0.05
    temp_factor = 1 + (ambient_temp - 19.5) / 100
    wave_factor = 1 + wave_height * 0.02
    solar_factors = {'Low': 1.0, 'Medium': 1.02, 'High': 1.05}
    
    total_factor = (pressure_factor * level_factor * temp_factor * 
                   wave_factor * solar_factors[solar_radiation])
    
    return base_rate * total_factor

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
        st.error(f"Error calculating distance: {str(e)}")
        return 0

def world_port_index(port_to_match, world_ports_data):
    """Find best matching port from world ports data"""
    best_match = process.extractOne(port_to_match, world_ports_data['Main Port Name'])
    return world_ports_data[world_ports_data['Main Port Name'] == best_match[0]].iloc[0]

def plot_combined_route(laden_ports, ballast_ports, world_ports_data):
    """Plot combined route on a single map"""
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
                st.error(f"Error plotting route: {str(e)}")
        
        if coordinates:
            m.fit_bounds(coordinates)
    
    return m

def create_voyage_section(leg_type, world_ports_data, is_ballast=False):
    """Create voyage section with tabs"""
    st.subheader(f"{leg_type} Leg Details")
    
    tabs = st.tabs(["Route Planning", "Environmental", "BOG Management", "Economics"])
    
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        with col1:
            voyage_from = st.text_input(f"From Port", key=f"{leg_type}_from")
        with col2:
            voyage_to = st.text_input(f"To Port", key=f"{leg_type}_to")
        with col3:
            if voyage_from and voyage_to:
                distance = route_distance(voyage_from, voyage_to, world_ports_data)
                st.number_input("Distance (NM)", value=distance, disabled=True, key=f"{leg_type}_distance")
            else:
                distance = 0
                
        col1, col2 = st.columns(2)
        with col1:
            speed = st.number_input("Speed (knots)", 1.0, 25.0, 15.0, key=f"{leg_type}_speed")
        with col2:
            consumption = st.number_input("LNG Consumption (m³/day)", 0.0, 500.0, 150.0, key=f"{leg_type}_consumption")

    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            ambient_temp = st.number_input("Ambient Temperature (°C)", -20.0, 45.0, 19.5, key=f"{leg_type}_temp")
            wave_height = st.number_input("Wave Height (m)", 0.0, 10.0, 1.0, key=f"{leg_type}_wave")
            solar_radiation = st.selectbox("Solar Radiation", ['Low', 'Medium', 'High'], key=f"{leg_type}_solar")
        with col2:
            tank_pressure = st.number_input("Tank Pressure (mbar)", 1000.0, 1300.0, 1013.0, key=f"{leg_type}_pressure")
            tank_level = st.number_input("Tank Level (%)", 0.0, 100.0, 98.0, key=f"{leg_type}_level")

    with tabs[2]:
        if is_ballast:
            col1, col2 = st.columns(2)
            with col1:
                heel_qty = st.number_input("Heel Quantity (m³)", 1500.0, 3000.0, 2000.0, key=f"{leg_type}_heel")
                
            # Calculate BOG metrics
            voyage_days = distance / (speed * 24) if speed > 0 else 0
            bog_rate = calculate_bog_rate(0.15, tank_pressure, tank_level, ambient_temp, wave_height, solar_radiation)
            bog_generated = heel_qty * bog_rate * voyage_days
            bog_required = consumption * voyage_days

            with col2:
                st.metric("Daily BOG Rate (%)", f"{bog_rate:.3f}")
                st.metric("BOG Generated (m³)", f"{bog_generated:.1f}")
                st.metric("BOG Required (m³)", f"{bog_required:.1f}")
                
                if bog_generated >= bog_required:
                    st.success("✅ Sufficient BOG for voyage")
                else:
                    st.error("❌ Insufficient BOG - adjust heel quantity")

    with tabs[3]:
        if is_ballast:
            col1, col2 = st.columns(2)
            with col1:
                lng_price = st.number_input("LNG Price ($/mmBTU)", 0.0, 50.0, 15.0, key=f"{leg_type}_lng_price")
                bunker_price = st.number_input("Bunker Price ($/mt)", 0.0, 2000.0, 800.0, key=f"{leg_type}_bunker")
            
            # Economic calculations
            daily_cost = bog_rate * heel_qty * lng_price
            voyage_cost = daily_cost * voyage_days
            
            with col2:
                st.metric("Daily Cost ($)", f"{daily_cost:.2f}")
                st.metric("Voyage Cost ($)", f"{voyage_cost:.2f}")

    return {
        'voyage_from': voyage_from,
        'voyage_to': voyage_to,
        'distance': distance,
        'speed': speed,
        'bog_metrics': {
            'generated': bog_generated if is_ballast else None,
            'required': bog_required if is_ballast else None,
            'rate': bog_rate if is_ballast else None
        } if is_ballast else None
    }

def show_bog_calculator():
    """Main function to show BOG calculator"""
    world_ports_data = load_world_ports()
    
    st.title("LNG Vessel Voyage Calculator")
    st.markdown("---")
    
    # Create voyage sections
    laden_data = create_voyage_section("Laden", world_ports_data)
    st.markdown("---")
    ballast_data = create_voyage_section("Ballast", world_ports_data, True)
    st.markdown("---")
    
    # Map visualization
    st.subheader("Route Visualization")
    laden_ports = [laden_data['voyage_from'], laden_data['voyage_to']]
    ballast_ports = [ballast_data['voyage_from'], ballast_data['voyage_to']]
    
    if all(laden_ports + ballast_ports):
        route_map = plot_combined_route(laden_ports, ballast_ports, world_ports_data)
        st_folium(route_map, width=800, height=500)

if __name__ == "__main__":
    st.set_page_config(page_title="BOG Calculator", page_icon="🚢", layout="wide")
    show_bog_calculator()
