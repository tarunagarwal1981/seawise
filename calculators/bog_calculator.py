# calculators/bog_calculator.py

import streamlit as st
from datetime import datetime
import pandas as pd
import numpy as np

# Weather effect calculation 
def calculate_temperature_effect(base_bog_rate, ambient_temp, reference_temp=19.5):
    """
    Calculate BOG rate adjustment for ambient temperature
    Reference temperature is typically 19.5°C (average sea temperature)
    """
    temp_difference = ambient_temp - reference_temp
    # Approximately 0.025% increase per 10°C
    adjustment = (temp_difference / 10) * 0.025
    return base_bog_rate + adjustment

def calculate_sea_state_effect(base_bog_rate, wave_height):
    """
    Calculate BOG rate adjustment for sea state
    Wave height in meters
    """
    if wave_height < 1:
        return 0
    elif wave_height < 2:
        return 0.005  # 0.005% increase for moderate seas
    elif wave_height < 4:
        return 0.01   # 0.01% increase for rough seas
    else:
        return 0.02   # 0.02% increase for very rough seas

def calculate_solar_effect(base_bog_rate, solar_radiation):
    """
    Calculate BOG rate adjustment for solar radiation
    solar_radiation: Low, Medium, High
    """
    solar_factors = {
        'Low': 0.005,    # Cloudy/night
        'Medium': 0.015, # Partly cloudy
        'High': 0.025    # Full sun
    }
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

def calculate_totals(consumption_rate, distance, speed):
    """Calculate consumption totals and journey time"""
    if speed > 0:
        time = distance / speed  # time in hours
        time_days = time / 24    # convert to days
        total = consumption_rate * time_days
        return round(total, 2), time_days
    return 0, 0

def create_voyage_section(leg_type):
    """Create input section for voyage leg"""
    st.subheader(f"{leg_type} Leg Details")
    
    # Row 1: Basic voyage details from enhanced calculator
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        voyage_from = st.text_input(f"From", key=f"{leg_type}_from")
    with col2:
        voyage_to = st.text_input(f"To", key=f"{leg_type}_to")
    with col3:
        departure_date = st.date_input(f"Departure Date", key=f"{leg_type}_date")
    with col4:
        departure_time = st.time_input(f"Departure Time", key=f"{leg_type}_time")
    with col5:
        eta = st.text_input(f"ETA", key=f"{leg_type}_eta")

    # Row 2: Technical details
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        distance = st.number_input(
            f"Distance (NM)", 
            min_value=0.0, 
            step=0.1, 
            key=f"{leg_type}_distance"
        )
    with col2:
        speed = st.number_input(
            f"Speed (Knots)", 
            min_value=0.0, 
            step=0.1, 
            key=f"{leg_type}_speed"
        )
    with col3:
        liquid_fuel = st.number_input(
            "Liquid Fuel (MT/D)", 
            min_value=0.0, 
            step=0.1,
            key=f"{leg_type}_liquid_fuel"
        )
    with col4:
        lng_consumption = st.number_input(
            "LNG (m³/D)", 
            min_value=0.0, 
            step=0.1,
            key=f"{leg_type}_lng"
        )

    # Row 3: Additional consumption details
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        reliq = st.number_input(
            "Reliquefaction (m³/D)", 
            min_value=0.0, 
            step=0.1,
            key=f"{leg_type}_reliq"
        )
    with col2:
        gcu = st.number_input(
            "GCU (m³/D)", 
            min_value=0.0, 
            step=0.1,
            key=f"{leg_type}_gcu"
        )
    with col3:
        cargo_volume = st.number_input(
            "Cargo Volume (m³)",
            min_value=0.0,
            step=100.0,
            key=f"{leg_type}_cargo_volume"
        )
    with col4:
        bog_rate = st.number_input(
            "Base BOG Rate (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.15,
            step=0.01,
            key=f"{leg_type}_bog_rate",
            help="Typical values: 0.10% - 0.15% for modern vessels"
        )

    # Add weather section
    st.subheader(f"{leg_type} Weather Conditions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        ambient_temp = st.number_input(
            "Average Ambient Temperature (°C)",
            min_value=-20.0,
            max_value=45.0,
            value=19.5,
            step=0.5,
            key=f"{leg_type}_temp"
        )
    
    with col2:
        wave_height = st.number_input(
            "Significant Wave Height (m)",
            min_value=0.0,
            max_value=10.0,
            value=1.0,
            step=0.5,
            key=f"{leg_type}_waves"
        )
    
    with col3:
        solar_radiation = st.selectbox(
            "Solar Radiation Level",
            options=['Low', 'Medium', 'High'],
            key=f"{leg_type}_solar"
        )

    # Calculate all totals
    total_liquid_fuel, voyage_time = calculate_totals(liquid_fuel, distance, speed)
    total_lng, _ = calculate_totals(lng_consumption, distance, speed)
    total_reliq, _ = calculate_totals(reliq, distance, speed)
    total_gcu, _ = calculate_totals(gcu, distance, speed)
    total_bog, adjusted_rate = calculate_adjusted_bog(
        cargo_volume, bog_rate, voyage_time,
        ambient_temp, wave_height, solar_radiation
    )
    
    return {
        'voyage_from': voyage_from,
        'voyage_to': voyage_to,
        'departure': datetime.combine(departure_date, departure_time),
        'eta': eta,
        'distance': distance,
        'speed': speed,
        'total_liquid_fuel': total_liquid_fuel,
        'total_lng': total_lng,
        'total_reliq': total_reliq,
        'total_gcu': total_gcu,
        'total_bog': total_bog,
        'cargo_volume': cargo_volume,
        'base_bog_rate': bog_rate,
        'adjusted_bog_rate': adjusted_rate,
        'ambient_temp': ambient_temp,
        'wave_height': wave_height,
        'solar_radiation': solar_radiation
    }

def show_summary(laden_data, ballast_data):
    """Display comprehensive voyage summary"""
    st.header("Voyage Summary")
    
    summary_data = {
        'Metric': [
            'Total Distance (NM)', 
            'Liquid Fuel (MT)', 
            'LNG (m³)', 
            'Reliquefaction (m³)', 
            'GCU (m³)',
            'BOG Generation (m³)',
            'Base BOG Rate (%)',
            'Weather-Adjusted BOG Rate (%)'
        ],
        'Laden': [
            laden_data['distance'],
            laden_data['total_liquid_fuel'],
            laden_data['total_lng'],
            laden_data['total_reliq'],
            laden_data['total_gcu'],
            laden_data['total_bog'],
            laden_data['base_bog_rate'],
            laden_data['adjusted_bog_rate']
        ],
        'Ballast': [
            ballast_data['distance'],
            ballast_data['total_liquid_fuel'],
            ballast_data['total_lng'],
            ballast_data['total_reliq'],
            ballast_data['total_gcu'],
            ballast_data['total_bog'],
            ballast_data['base_bog_rate'],
            ballast_data['adjusted_bog_rate']
        ]
    }
    
    df = pd.DataFrame(summary_data)
    df['Total'] = df['Laden'] + df['Ballast']
    
    st.dataframe(df, use_container_width=True)

    # Route information
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        **Laden Leg Route:**  
        {laden_data['voyage_from']} → {laden_data['voyage_to']}  
        Departure: {laden_data['departure'].strftime('%Y-%m-%d %H:%M')} | ETA: {laden_data['eta']}
        Cargo Volume: {laden_data['cargo_volume']:,.0f} m³
        Weather: {laden_data['ambient_temp']}°C, {laden_data['wave_height']}m waves, {laden_data['solar_radiation']} radiation
        """)
    with col2:
        st.markdown(f"""
        **Ballast Leg Route:**  
        {ballast_data['voyage_from']} → {ballast_data['voyage_to']}  
        Departure: {ballast_data['departure'].strftime('%Y-%m-%d %H:%M')} | ETA: {ballast_data['eta']}
        Cargo Volume: {ballast_data['cargo_volume']:,.0f} m³
        Weather: {ballast_data['ambient_temp']}°C, {ballast_data['wave_height']}m waves, {ballast_data['solar_radiation']} radiation
        """)

def show_bog_calculator():
    st.title("Advanced BOG Calculator with Weather Effects")
    
    st.markdown("""
    ### Comprehensive BOG Calculation System
    This calculator includes:
    1. Complete voyage planning (laden and ballast legs)
    2. Consumption tracking (fuel, LNG, reliquefaction, GCU)
    3. Environmental impact on BOG generation:
       - Ambient temperature (baseline: 19.5°C)
       - Sea state (wave height)
       - Solar radiation levels
    
    The base BOG rate is automatically adjusted based on environmental conditions.
    """)
    
    st.markdown("---")
    laden_data = create_voyage_section("Laden")
    st.markdown("---")
    ballast_data = create_voyage_section("Ballast")
    st.markdown("---")
    show_summary(laden_data, ballast_data)

if __name__ == "__main__":
    st.set_page_config(
        page_title="Advanced BOG Calculator",
        page_icon="🚢",
        layout="wide"
    )
    show_bog_calculator()
