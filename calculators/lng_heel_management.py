import streamlit as st

def show_lng_heel_calculator():
    st.title("LNG Heel Management Calculator")
    
    st.subheader("Input Parameters")
    
    # Input fields for LNG Heel Management
    tank_capacity = st.number_input("Tank Capacity (m³)", min_value=0.0, step=0.1)
    current_lng_volume = st.number_input("Current LNG Volume (m³)", min_value=0.0, step=0.1)
    heel_percentage = st.number_input("Required Heel Percentage (%)", min_value=0.0, max_value=100.0, step=0.1)
    boil_off_rate = st.number_input("Boil-off Rate (m³/day)", min_value=0.0, step=0.01)
    voyage_days = st.number_input("Voyage Duration (Days)", min_value=0.0, step=0.1)
    
    # Calculate heel requirements and losses
    if st.button("Calculate"):
        required_heel = (heel_percentage / 100) * tank_capacity
        lng_boil_off = boil_off_rate * voyage_days
        final_volume = max(0, current_lng_volume - lng_boil_off)
        is_heel_sufficient = final_volume >= required_heel

        st.subheader("Results")
        st.write(f"Required LNG Heel (m³): {required_heel:.2f}")
        st.write(f"Total Boil-off Loss (m³): {lng_boil_off:.2f}")
        st.write(f"Final LNG Volume After Voyage (m³): {final_volume:.2f}")
        st.write("Heel Sufficient: ", "✅ Yes" if is_heel_sufficient else "❌ No")
