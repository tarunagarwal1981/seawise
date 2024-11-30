import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
import searoute as sr
from fuzzywuzzy import process
import plotly.graph_objects as go

def calculate_daily_bog(initial_volume, days, bog_rate, ambient_temps, wave_heights, 
                       solar_radiation, tank_pressure, engine_consumption, reliq_capacity):
    """Calculate daily BOG with all factors including reliquefaction"""
    daily_volumes = []
    daily_bog_generated = []
    daily_bog_consumed = []
    daily_bog_reliquefied = []
    remaining_volume = initial_volume
    
    for day in range(int(days)):
        # Calculate day's BOG rate with all factors
        daily_rate = calculate_bog_rate(
            bog_rate, 
            tank_pressure,
            (remaining_volume / initial_volume) * 100,  # Tank level percentage
            ambient_temps[day],
            wave_heights[day],
            solar_radiation
        )
        
        # Calculate BOG generated
        bog_generated = remaining_volume * (daily_rate / 100)
        daily_bog_generated.append(bog_generated)
        
        # Calculate BOG consumed by engines
        bog_consumed = min(bog_generated, engine_consumption)
        daily_bog_consumed.append(bog_consumed)
        
        # Calculate BOG reliquefied
        bog_to_reliquify = bog_generated - bog_consumed
        bog_reliquefied = min(bog_to_reliquify, reliq_capacity)
        daily_bog_reliquefied.append(bog_reliquefied)
        
        # Update remaining volume
        remaining_volume = remaining_volume - bog_generated + bog_reliquefied
        daily_volumes.append(remaining_volume)
    
    return {
        'daily_volumes': daily_volumes,
        'daily_bog_generated': daily_bog_generated,
        'daily_bog_consumed': daily_bog_consumed,
        'daily_bog_reliquefied': daily_bog_reliquefied
    }

def calculate_economics(daily_data, lng_price, bunker_price, electricity_cost, power_consumption):
    """Calculate comprehensive economics"""
    total_bog_generated = sum(daily_data['daily_bog_generated'])
    total_bog_consumed = sum(daily_data['daily_bog_consumed'])
    total_bog_reliquefied = sum(daily_data['daily_bog_reliquefied'])
    
    # Convert to energy units and calculate costs
    lng_cost = total_bog_generated * lng_price
    fuel_savings = total_bog_consumed * bunker_price
    reliq_cost = total_bog_reliquefied * power_consumption * electricity_cost
    
    return {
        'lng_value_lost': lng_cost,
        'fuel_savings': fuel_savings,
        'reliq_cost': reliq_cost,
        'net_benefit': fuel_savings - reliq_cost
    }

def plot_daily_tracking(daily_data, voyage_days):
    """Create interactive plot for daily tracking"""
    days = list(range(int(voyage_days)))
    
    fig = go.Figure()
    
    # Add traces for each metric
    fig.add_trace(go.Scatter(x=days, y=daily_data['daily_volumes'],
                            name='Remaining Volume', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=days, y=daily_data['daily_bog_generated'],
                            name='BOG Generated', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=days, y=daily_data['daily_bog_consumed'],
                            name='BOG Consumed', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=days, y=daily_data['daily_bog_reliquefied'],
                            name='BOG Reliquefied', line=dict(color='purple')))
    
    fig.update_layout(
        title='Daily BOG Tracking',
        xaxis_title='Days',
        yaxis_title='Volume (m³)',
        hovermode='x unified'
    )
    
    return fig

def create_voyage_section(leg_type, world_ports_data, is_ballast=False):
    """Enhanced voyage section with comprehensive inputs"""
    st.subheader(f"{leg_type} Leg Details")
    
    tabs = st.tabs(["Cargo & Route", "Environmental", "Operations", "Economics", "Results"])
    
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        with col1:
            if not is_ballast:
                initial_cargo = st.number_input("Initial Cargo Volume (m³)", 0.0, 180000.0, 170000.0)
            else:
                initial_cargo = st.number_input("Heel Quantity (m³)", 1500.0, 3000.0, 2000.0)
        with col2:
            voyage_from = st.text_input(f"From Port", key=f"{leg_type}_from")
        with col3:
            voyage_to = st.text_input(f"To Port", key=f"{leg_type}_to")
        
        distance = route_distance(voyage_from, voyage_to, world_ports_data) if voyage_from and voyage_to else 0
        speed = st.number_input("Speed (knots)", 1.0, 25.0, 15.0)
        voyage_days = distance / (speed * 24) if speed > 0 else 0
        
    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            base_temp = st.number_input("Base Temperature (°C)", -20.0, 45.0, 19.5)
            temp_variation = st.number_input("Temperature Variation (±°C)", 0.0, 10.0, 2.0)
        with col2:
            base_waves = st.number_input("Base Wave Height (m)", 0.0, 10.0, 1.0)
            wave_variation = st.number_input("Wave Height Variation (±m)", 0.0, 5.0, 0.5)
        
        solar_radiation = st.selectbox("Solar Radiation", ['Low', 'Medium', 'High'])
        tank_pressure = st.number_input("Tank Pressure (mbar)", 1000.0, 1300.0, 1013.0)
        
    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            engine_consumption = st.number_input("Engine Gas Consumption (m³/day)", 0.0, 500.0, 150.0)
            reliq_capacity = st.number_input("Reliquefaction Capacity (m³/day)", 0.0, 50.0, 20.0)
        with col2:
            power_consumption = st.number_input("Power Consumption (kWh/m³)", 0.0, 1000.0, 800.0)
            
    with tabs[3]:
        col1, col2 = st.columns(2)
        with col1:
            lng_price = st.number_input("LNG Price ($/mmBTU)", 0.0, 50.0, 15.0)
            bunker_price = st.number_input("Bunker Price ($/mt)", 0.0, 2000.0, 800.0)
        with col2:
            electricity_cost = st.number_input("Electricity Cost ($/kWh)", 0.0, 1.0, 0.15)
            
    with tabs[4]:
        if voyage_days > 0:
            # Generate daily temperature and wave height profiles
            daily_temps = np.random.normal(base_temp, temp_variation, int(voyage_days))
            daily_waves = np.random.normal(base_waves, wave_variation, int(voyage_days))
            
            # Calculate daily BOG and volumes
            daily_data = calculate_daily_bog(
                initial_cargo, voyage_days, 0.15, daily_temps, daily_waves,
                solar_radiation, tank_pressure, engine_consumption, reliq_capacity
            )
            
            # Calculate economics
            economics = calculate_economics(
                daily_data, lng_price, bunker_price,
                electricity_cost, power_consumption
            )
            
            # Display results
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Final Cargo Volume", f"{daily_data['daily_volumes'][-1]:.1f} m³")
                st.metric("Total BOG Generated", f"{sum(daily_data['daily_bog_generated']):.1f} m³")
            with col2:
                st.metric("Net Cost Benefit", f"${economics['net_benefit']:,.2f}")
                st.metric("Total BOG Reliquefied", f"{sum(daily_data['daily_bog_reliquefied']):.1f} m³")
            
            # Plot daily tracking
            st.plotly_chart(plot_daily_tracking(daily_data, voyage_days))
            
    return {
        'voyage_from': voyage_from,
        'voyage_to': voyage_to,
        'distance': distance,
        'daily_data': daily_data if voyage_days > 0 else None,
        'economics': economics if voyage_days > 0 else None
    }

def show_bog_calculator():
    """Main function to show enhanced BOG calculator"""
    world_ports_data = load_world_ports()
    
    st.title("LNG Vessel Optimization Suite")
    st.markdown("### Comprehensive BOG and Economics Calculator")
    
    laden_data = create_voyage_section("Laden", world_ports_data)
    st.markdown("---")
    ballast_data = create_voyage_section("Ballast", world_ports_data, True)
    
    # Map visualization (keeping existing map functionality)
    st.markdown("---")
    st.subheader("Route Visualization")
    laden_ports = [laden_data['voyage_from'], laden_data['voyage_to']]
    ballast_ports = [ballast_data['voyage_from'], ballast_data['voyage_to']]
    
    if all(laden_ports + ballast_ports):
        route_map = plot_combined_route(laden_ports, ballast_ports, world_ports_data)
        st_folium(route_map, width=800, height=500)

if __name__ == "__main__":
    st.set_page_config(page_title="LNG Optimization Suite", page_icon="🚢", layout="wide")
    show_bog_calculator()
