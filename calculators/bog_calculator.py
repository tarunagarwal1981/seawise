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

# Functions for distance and plotting
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

def plot_route(ports, world_ports_data):
    """Plot route on a Folium map"""
    m = folium.Map(location=[0, 0], zoom_start=2)
    
    if len(ports) >= 2 and all(ports):
        coordinates = []
        for i in range(len(ports) - 1):
            try:
                start_port = world_port_index(ports[i], world_ports_data)
                end_port = world_port_index(ports[i+1], world_ports_data)
                start_coords = [float(start_port['Latitude']), float(start_port['Longitude'])]
                end_coords = [float(end_port['Latitude']), float(end_port['Longitude'])]
                
                folium.Marker(
                    start_coords,
                    popup=ports[i],
                    icon=folium.Icon(color='green' if i == 0 else 'blue')
                ).add_to(m)
                
                if i == len(ports) - 2:
                    folium.Marker(
                        end_coords,
                        popup=ports[i+1],
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
                st.error(f"Error plotting route for {ports[i]} to {ports[i+1]}: {str(e)}")
        
        if coordinates:
            m.fit_bounds(coordinates)
    
    return m

# Modified BOG Calculator Functions
def create_voyage_section(leg_type, world_ports_data):
    st.subheader(f"{leg_type} Leg Details")
    
    # User inputs for ports and calculate distance
    col1, col2, col3 = st.columns(3)
    with col1:
        voyage_from = st.text_input(f"From Port", key=f"{leg_type}_from")
    with col2:
        voyage_to = st.text_input(f"To Port", key=f"{leg_type}_to")
    with col3:
        if voyage_from and voyage_to:
            distance = route_distance(voyage_from, voyage_to, world_ports_data)
            st.number_input(f"Distance (NM)", value=distance, disabled=True, key=f"{leg_type}_distance")
        else:
            distance = 0
    
    # Plot the route map
    ports = [voyage_from, voyage_to] if voyage_from and voyage_to else []
    if ports:
        route_map = plot_route(ports, world_ports_data)
        st_folium(route_map, width=700, height=400)
    
    return {
        'voyage_from': voyage_from,
        'voyage_to': voyage_to,
        'distance': distance
    }

def show_bog_calculator():
    st.title("Enhanced BOG Calculator")
    st.markdown("""
    ### Features:
    1. Automated distance calculation based on port selection.
    2. Route visualization with interactive maps.
    3. Comprehensive weather and consumption impact calculations.
    """)
    
    world_ports_data = load_world_ports()
    
    st.markdown("---")
    laden_data = create_voyage_section("Laden", world_ports_data)
    st.markdown("---")
    ballast_data = create_voyage_section("Ballast", world_ports_data)
    st.markdown("---")
    
    # Placeholder for additional summary or calculations
    st.write("BOG and voyage calculations will go here.")

if __name__ == "__main__":
    st.set_page_config(
        page_title="BOG Calculator",
        page_icon="🚢",
        layout="wide"
    )
    show_bog_calculator()
