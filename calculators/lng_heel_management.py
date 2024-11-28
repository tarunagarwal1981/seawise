import streamlit as st
from datetime import datetime
import pandas as pd

def calculate_totals(consumption_rate, distance, speed):
    if speed > 0:
        time = distance / speed
        total = consumption_rate * time
        return round(total, 2)
    return 0

def create_voyage_input(leg_type):
    """Create input fields for a voyage leg"""
    col1, col2 = st.columns(2)
    
    with col1:
        voyage_from = st.text_input(f"From", key=f"{leg_type}_from")
        departure_date = st.date_input(f"Departure Date", key=f"{leg_type}_date")
        distance = st.number_input(f"Distance (NM)", min_value=0.0, step=0.1, key=f"{leg_type}_distance")
        
    with col2:
        voyage_to = st.text_input(f"To", key=f"{leg_type}_to")
        departure_time = st.time_input(f"Departure Time", key=f"{leg_type}_time")
        speed = st.number_input(f"Speed (Knots)", min_value=0.0, step=0.1, key=f"{leg_type}_speed")
    
    eta = st.text_input(f"ETA", key=f"{leg_type}_eta")
    
    st.subheader("Consumption Rates")
    col1, col2 = st.columns(2)
    
    with col1:
        liquid_fuel = st.number_input(
            "Liquid Fuel (MT/D)", 
            min_value=0.0, 
            step=0.1,
            key=f"{leg_type}_liquid_fuel"
        )
        lng_consumption = st.number_input(
            "LNG (m³/D)", 
            min_value=0.0, 
            step=0.1,
            key=f"{leg_type}_lng"
        )
    
    with col2:
        reliq = st.number_input(
            "Reliquefaction (m³/D)", 
            min_value=0.0, 
            step=0.1,
            key=f"{leg_type}_reliq"
        )
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
    
    st.dataframe(df.style.format("{:.2f}"), use_container_width=True)
    
    # Display route information
    st.subheader("Route Information")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Laden Leg**")
        st.write(f"From: {laden_data['voyage_from']}")
        st.write(f"To: {laden_data['voyage_to']}")
        st.write(f"Departure: {laden_data['departure'].strftime('%Y-%m-%d %H:%M')}")
        st.write(f"ETA: {laden_data['eta']}")
        
    with col2:
        st.markdown("**Ballast Leg**")
        st.write(f"From: {ballast_data['voyage_from']}")
        st.write(f"To: {ballast_data['voyage_to']}")
        st.write(f"Departure: {ballast_data['departure'].strftime('%Y-%m-%d %H:%M')}")
        st.write(f"ETA: {ballast_data['eta']}")

def show_lng_heel_calculator():
    st.title("LNG Vessel Voyage Calculator")
    
    # Create tabs for Laden and Ballast legs
    tab1, tab2, tab3 = st.tabs(["Laden Leg", "Ballast Leg", "Summary"])
    
    with tab1:
        st.header("Laden Leg Details")
        laden_data = create_voyage_input("laden")
        
    with tab2:
        st.header("Ballast Leg Details")
        ballast_data = create_voyage_input("ballast")
        
    with tab3:
        show_summary(laden_data, ballast_data)

if __name__ == "__main__":
    st.set_page_config(
        page_title="LNG Vessel Voyage Calculator",
        page_icon="🚢",
        layout="wide"
    )
    show_lng_heel_calculator()
