import streamlit as st
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium
import searoute as sr
from fuzzywuzzy import process
import numpy as np

# Custom CSS for better UI
st.set_page_config(page_title="LNG Vessel Optimization", page_icon="🚢", layout="wide")
st.markdown("""
    <style>
        .main {padding: 0rem 1rem;}
        .stTabs [data-baseweb="tab-list"] {gap: 2px;}
        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 1rem;
            background-color: #f0f2f6;
        }
        .stTabs [aria-selected="true"] {
            background-color: #e0e2e6;
        }
    </style>
""", unsafe_allow_html=True)

# Load and Cache Data
@st.cache_data
def load_world_ports():
    return pd.read_csv("UpdatedPub150.csv")

@st.cache_data
def load_vessel_configs():
    # Sample vessel configurations - replace with actual database
    return {
        "174K": {
            "tank_capacity": 174000,
            "min_heel": 1500,
            "max_heel": 3000,
            "base_bog_rate": 0.15,
            "reliq_capacity": 2.5,
            "engine_efficiency": 0.45
        },
        "180K": {
            "tank_capacity": 180000,
            "min_heel": 1600,
            "max_heel": 3200,
            "base_bog_rate": 0.14,
            "reliq_capacity": 2.8,
            "engine_efficiency": 0.46
        }
    }

# Enhanced BOG Calculations
def calculate_bog_rate(base_rate, tank_pressure, tank_level, ambient_temp, wave_height, solar_radiation):
    """Enhanced BOG rate calculation including tank conditions"""
    pressure_factor = 1 + ((tank_pressure - 1013) / 1013) * 0.1
    level_factor = 1 + (1 - tank_level/100) * 0.05
    
    temp_factor = 1 + (ambient_temp - 19.5) / 100
    wave_factor = 1 + wave_height * 0.02
    solar_factors = {'Low': 1.0, 'Medium': 1.02, 'High': 1.05}
    
    total_factor = (pressure_factor * level_factor * temp_factor * 
                   wave_factor * solar_factors[solar_radiation])
    
    return base_rate * total_factor

def calculate_reliq_efficiency(ambient_temp, seawater_temp, load_percentage):
    """Calculate reliquefaction plant efficiency"""
    base_efficiency = 0.85
    temp_factor = 1 - (ambient_temp - 19.5) / 200
    seawater_factor = 1 - (seawater_temp - 15) / 150
    load_factor = 1 - abs(load_percentage - 85) / 200
    
    return base_efficiency * temp_factor * seawater_factor * load_factor

def calculate_economic_metrics(bog_generated, bog_required, lng_price, 
                            bunker_price, reliq_power, electricity_cost):
    """Calculate economic metrics for decision making"""
    reliq_cost = reliq_power * 24 * electricity_cost
    lng_value = bog_generated * lng_price
    fuel_savings = bog_required * bunker_price
    
    return {
        'reliq_cost': reliq_cost,
        'lng_value': lng_value,
        'fuel_savings': fuel_savings,
        'net_benefit': fuel_savings - reliq_cost
    }

def create_voyage_section(leg_type, world_ports_data, vessel_config, is_ballast=False):
    """Enhanced voyage section with optimization"""
    tabs = st.tabs([
        "Route Planning", 
        "Environmental Conditions", 
        "BOG Management",
        "Economic Analysis"
    ])
    
    # Route Planning Tab
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        with col1:
            voyage_from = st.text_input(f"{leg_type} From Port")
        with col2:
            voyage_to = st.text_input(f"{leg_type} To Port")
        with col3:
            if voyage_from and voyage_to:
                distance = route_distance(voyage_from, voyage_to, world_ports_data)
                st.number_input("Distance (NM)", value=distance, disabled=True)
            else:
                distance = 0
        
        col1, col2 = st.columns(2)
        with col1:
            speed = st.number_input("Speed (knots)", 1.0, 25.0, 15.0)
        with col2:
            consumption = st.number_input("LNG Consumption (m³/day)", 0.0, 500.0, 150.0)

    # Environmental Conditions Tab
    with tabs[1]:
        col1, col2, col3 = st.columns(3)
        with col1:
            ambient_temp = st.number_input("Ambient Temperature (°C)", -20.0, 45.0, 19.5)
            wave_height = st.number_input("Wave Height (m)", 0.0, 10.0, 1.0)
        with col2:
            seawater_temp = st.number_input("Seawater Temperature (°C)", -2.0, 32.0, 15.0)
            solar_radiation = st.selectbox("Solar Radiation", ['Low', 'Medium', 'High'])
        with col3:
            tank_pressure = st.number_input("Tank Pressure (mbar)", 1000.0, 1300.0, 1013.0)
            tank_level = st.number_input("Tank Level (%)", 0.0, 100.0, 98.0)

    # BOG Management Tab
    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            heel_qty = st.number_input(
                "Heel Quantity (m³)", 
                vessel_config['min_heel'],
                vessel_config['max_heel'],
                vessel_config['min_heel']
            )
            reliq_capacity = st.number_input(
                "Reliquefaction Capacity (t/day)",
                0.0,
                vessel_config['reliq_capacity'],
                vessel_config['reliq_capacity']
            )
        
        # Calculate and display BOG metrics
        voyage_days = distance / (speed * 24)
        bog_rate = calculate_bog_rate(
            vessel_config['base_bog_rate'],
            tank_pressure,
            tank_level,
            ambient_temp,
            wave_height,
            solar_radiation
        )
        
        bog_generated = heel_qty * bog_rate * voyage_days
        bog_required = consumption * voyage_days
        reliq_efficiency = calculate_reliq_efficiency(
            ambient_temp,
            seawater_temp,
            (bog_generated/reliq_capacity)*100
        )

        with col2:
            st.metric("Daily BOG Rate (%)", f"{bog_rate:.3f}")
            st.metric("BOG Generated (m³)", f"{bog_generated:.1f}")
            st.metric("BOG Required (m³)", f"{bog_required:.1f}")
            st.metric("Reliquefaction Efficiency", f"{reliq_efficiency:.1%}")

    # Economic Analysis Tab
    with tabs[3]:
        col1, col2 = st.columns(2)
        with col1:
            lng_price = st.number_input("LNG Price ($/mmBTU)", 0.0, 50.0, 15.0)
            bunker_price = st.number_input("Bunker Price ($/mt)", 0.0, 2000.0, 800.0)
            electricity_cost = st.number_input("Electricity Cost ($/kWh)", 0.0, 1.0, 0.15)

        # Calculate economics
        economics = calculate_economic_metrics(
            bog_generated,
            bog_required,
            lng_price,
            bunker_price,
            reliq_capacity * reliq_efficiency,
            electricity_cost
        )
        
        with col2:
            st.metric("Reliquefaction Cost ($/day)", f"${economics['reliq_cost']:.2f}")
            st.metric("LNG Value ($/day)", f"${economics['lng_value']:.2f}")
            st.metric("Fuel Savings ($/day)", f"${economics['fuel_savings']:.2f}")
            st.metric("Net Benefit ($/day)", f"${economics['net_benefit']:.2f}")

    return {
        'voyage_from': voyage_from,
        'voyage_to': voyage_to,
        'distance': distance,
        'speed': speed,
        'consumption': consumption,
        'heel_qty': heel_qty if is_ballast else None,
        'bog_generated': bog_generated if is_ballast else None,
        'bog_required': bog_required if is_ballast else None,
        'economics': economics if is_ballast else None
    }

def main():
    st.title("LNG Vessel Optimization Suite")
    
    # Vessel Configuration Selection
    vessel_configs = load_world_ports()
    vessel_type = st.selectbox("Select Vessel Type", list(vessel_configs.keys()))
    vessel_config = vessel_configs[vessel_type]
    
    st.markdown("---")
    
    # Create voyage sections
    laden_data = create_voyage_section("Laden", world_ports_data, vessel_config)
    st.markdown("---")
    ballast_data = create_voyage_section("Ballast", world_ports_data, vessel_config, True)
    
    # Map visualization (keeping existing functionality)
    st.markdown("---")
    st.subheader("Voyage Route Visualization")
    
    laden_ports = [laden_data['voyage_from'], laden_data['voyage_to']]
    ballast_ports = [ballast_data['voyage_from'], ballast_data['voyage_to']]
    
    if all(laden_ports + ballast_ports):
        route_map = plot_combined_route(laden_ports, ballast_ports, world_ports_data)
        st_folium(route_map, width=800, height=500)

if __name__ == "__main__":
    main()
