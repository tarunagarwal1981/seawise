import streamlit as st

# Function to calculate totals
def calculate_totals(consumption_rate, distance, speed):
    if speed > 0:
        time = distance / speed
        total = consumption_rate * time
        return round(total, 2)
    return 0

def show_lng_heel_calculator():
    # App title
    st.title("Voyage Fuel Consumption App")

    # Create two sections for Laden Leg and Ballast Leg
    st.subheader("Laden Leg Input")
    laden_voyage_from = st.text_input("Voyage From (Laden Leg)")
    laden_voyage_to = st.text_input("Voyage To (Laden Leg)")
    laden_departure = st.datetime_input("Date and Time of Departure (Laden Leg)")
    laden_eta = st.text_input("ETA (Laden Leg)")
    laden_distance = st.number_input("Distance (NM, Laden Leg)", min_value=0.0, step=0.1)
    laden_speed = st.number_input("Speed Required (Knots, Laden Leg)", min_value=0.0, step=0.1)
    laden_liquid_fuel = st.number_input("Liquid Fuel Consumption (MT/D, Laden Leg)", min_value=0.0, step=0.1)
    laden_lng_consumption = st.number_input("LNG Consumption (m³/D, Laden Leg)", min_value=0.0, step=0.1)
    laden_reliq = st.number_input("Reliquefaction Consumption (m³/D, Laden Leg)", min_value=0.0, step=0.1)
    laden_gcu = st.number_input("GCU Consumption (m³/D, Laden Leg)", min_value=0.0, step=0.1)

    # Calculate Laden Leg totals
    laden_total_liquid_fuel = calculate_totals(laden_liquid_fuel, laden_distance, laden_speed)
    laden_total_lng = calculate_totals(laden_lng_consumption, laden_distance, laden_speed)

    st.write(f"Total Liquid Fuel (MT, Laden Leg): {laden_total_liquid_fuel}")
    st.write(f"Total LNG (m³, Laden Leg): {laden_total_lng}")

    st.subheader("Ballast Leg Input")
    ballast_voyage_from = st.text_input("Voyage From (Ballast Leg)")
    ballast_voyage_to = st.text_input("Voyage To (Ballast Leg)")
    ballast_departure = st.datetime_input("Date and Time of Departure (Ballast Leg)")
    ballast_eta = st.text_input("ETA (Ballast Leg)")
    ballast_distance = st.number_input("Distance (NM, Ballast Leg)", min_value=0.0, step=0.1)
    ballast_speed = st.number_input("Speed Required (Knots, Ballast Leg)", min_value=0.0, step=0.1)
    ballast_liquid_fuel = st.number_input("Liquid Fuel Consumption (MT/D, Ballast Leg)", min_value=0.0, step=0.1)
    ballast_lng_consumption = st.number_input("LNG Consumption (m³/D, Ballast Leg)", min_value=0.0, step=0.1)
    ballast_reliq = st.number_input("Reliquefaction Consumption (m³/D, Ballast Leg)", min_value=0.0, step=0.1)
    ballast_gcu = st.number_input("GCU Consumption (m³/D, Ballast Leg)", min_value=0.0, step=0.1)

    # Calculate Ballast Leg totals
    ballast_total_liquid_fuel = calculate_totals(ballast_liquid_fuel, ballast_distance, ballast_speed)
    ballast_total_lng = calculate_totals(ballast_lng_consumption, ballast_distance, ballast_speed)

    st.write(f"Total Liquid Fuel (MT, Ballast Leg): {ballast_total_liquid_fuel}")
    st.write(f"Total LNG (m³, Ballast Leg): {ballast_total_lng}")

    # Summary
    st.subheader("Summary of Totals")
    st.write(f"Total Liquid Fuel for Voyage (MT): {laden_total_liquid_fuel + ballast_total_liquid_fuel}")
    st.write(f"Total LNG for Voyage (m³): {laden_total_lng + ballast_total_lng}")
