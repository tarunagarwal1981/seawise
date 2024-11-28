# calculators/bog_calculator.py

import streamlit as st
from datetime import datetime
import pandas as pd

def calculate_bog(cargo_volume, bog_rate, time):
    """Calculate BOG generation"""
    if cargo_volume > 0 and bog_rate > 0 and time > 0:
        daily_bog = cargo_volume * (bog_rate / 100)
        total_bog = daily_bog * time
        return round(total_bog, 2)
    return 0

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
    
    # Row 1: Basic voyage details
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
            "Daily BOG Rate (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.15,
            step=0.01,
            key=f"{leg_type}_bog_rate",
            help="Typical values: 0.10% - 0.15% for modern vessels"
        )

    # Calculate totals
    total_liquid_fuel, voyage_time = calculate_totals(liquid_fuel, distance, speed)
    total_lng, _ = calculate_totals(lng_consumption, distance, speed)
    total_reliq, _ = calculate_totals(reliq, distance, speed)
    total_gcu, _ = calculate_totals(gcu, distance, speed)
    total_bog = calculate_bog(cargo_volume, bog_rate, voyage_time)
    
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
        'cargo_volume': cargo_volume
    }

def show_summary(laden_data, ballast_data):
    """Display voyage summary"""
    st.header("Voyage Summary")
    
    summary_data = {
        'Metric': [
            'Total Distance (NM)', 
            'Liquid Fuel (MT)', 
            'LNG (m³)', 
            'Reliquefaction (m³)', 
            'GCU (m³)',
            'BOG Generation (m³)'
        ],
        'Laden': [
            laden_data['distance'],
            laden_data['total_liquid_fuel'],
            laden_data['total_lng'],
            laden_data['total_reliq'],
            laden_data['total_gcu'],
            laden_data['total_bog']
        ],
        'Ballast': [
            ballast_data['distance'],
            ballast_data['total_liquid_fuel'],
            ballast_data['total_lng'],
            ballast_data['total_reliq'],
            ballast_data['total_gcu'],
            ballast_data['total_bog']
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
        """)
    with col2:
        st.markdown(f"""
        **Ballast Leg Route:**  
        {ballast_data['voyage_from']} → {ballast_data['voyage_to']}  
        Departure: {ballast_data['departure'].strftime('%Y-%m-%d %H:%M')} | ETA: {ballast_data['eta']}
        Cargo Volume: {ballast_data['cargo_volume']:,.0f} m³
        """)

def show_bog_calculator():
    st.title("BOG Calculator")
    
    st.markdown("""
    ### BOG Estimation
    The calculator includes Boil-Off Gas (BOG) estimation based on:
    - Cargo volume
    - Daily BOG rate (default 0.15% which is typical for modern LNG carriers)
    - Journey duration (calculated from distance and speed)
    - Separate calculations for laden and ballast legs
    
    Additional features:
    - GCU and reliquefaction tracking
    - Fuel consumption monitoring
    - Complete voyage planning
    """)
    
    st.markdown("---")
    laden_data = create_voyage_section("Laden")
    st.markdown("---")
    ballast_data = create_voyage_section("Ballast")
    st.markdown("---")
    show_summary(laden_data, ballast_data)

if __name__ == "__main__":
    st.set_page_config(page_title="BOG Calculator", layout="wide")
    show_bog_calculator()
