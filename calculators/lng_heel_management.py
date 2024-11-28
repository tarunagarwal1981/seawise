import streamlit as st
from datetime import datetime
import pandas as pd

def calculate_totals(consumption_rate, distance, speed):
    if speed > 0:
        time = distance / speed
        total = consumption_rate * time
        return round(total, 2)
    return 0

def create_voyage_section(leg_type):
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
    col1, col2, _ = st.columns([1, 1, 2])
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

    # Calculate totals
    total_liquid_fuel = calculate_totals(liquid_fuel, distance, speed)
    total_lng = calculate_totals(lng_consumption, distance, speed)
    total_reliq = calculate_totals(reliq, distance, speed)
    total_gcu = calculate_totals(gcu, distance, speed)
    
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
        'total_gcu': total_gcu
    }

def show_summary(laden_data, ballast_data):
    st.header("Voyage Summary")
    
    # Create summary table
    summary_data = {
        'Metric': ['Total Distance (NM)', 'Liquid Fuel (MT)', 'LNG (m³)', 'Reliquefaction (m³)', 'GCU (m³)'],
        'Laden': [
            laden_data['distance'],
            laden_data['total_liquid_fuel'],
            laden_data['total_lng'],
            laden_data['total_reliq'],
            laden_data['total_gcu']
        ],
        'Ballast': [
            ballast_data['distance'],
            ballast_data['total_liquid_fuel'],
            ballast_data['total_lng'],
            ballast_data['total_reliq'],
            ballast_data['total_gcu']
        ]
    }
    
    df = pd.DataFrame(summary_data)
    df['Total'] = df['Laden'] + df['Ballast']
    
    # Display summary table
    st.dataframe(df, use_container_width=True)

    # Display compact route information
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        **Laden Leg Route:**  
        {laden_data['voyage_from']} → {laden_data['voyage_to']}  
        Departure: {laden_data['departure'].strftime('%Y-%m-%d %H:%M')} | ETA: {laden_data['eta']}
        """)
    with col2:
        st.markdown(f"""
        **Ballast Leg Route:**  
        {ballast_data['voyage_from']} → {ballast_data['voyage_to']}  
        Departure: {ballast_data['departure'].strftime('%Y-%m-%d %H:%M')} | ETA: {ballast_data['eta']}
        """)

def show_lng_heel_calculator():
    st.title("LNG Vessel Voyage Calculator")
    
    # Add a horizontal line for better section separation
    st.markdown("---")
    
    # Laden Leg Section
    laden_data = create_voyage_section("Laden")
    
    # Add a horizontal line for better section separation
    st.markdown("---")
    
    # Ballast Leg Section
    ballast_data = create_voyage_section("Ballast")
    
    # Add a horizontal line for better section separation
    st.markdown("---")
    
    # Summary Section
    show_summary(laden_data, ballast_data)

if __name__ == "__main__":
    st.set_page_config(
        page_title="LNG Vessel Voyage Calculator",
        page_icon="🚢",
        layout="wide"
    )
    show_lng_heel_calculator()
