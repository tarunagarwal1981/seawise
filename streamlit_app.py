import streamlit as st

# Set page config at the very start
st.set_page_config(page_title="Seawise Calculators", layout="wide", page_icon="🚢")

# Import the calculator after set_page_config
from calculators.cii_calculator import show_cii_calculator

def main():
    st.sidebar.title("Navigation")
    
    calculator_choice = st.sidebar.radio(
        "Select Calculator",
        ["CII Calculator", "Heel Calculator", "BOG Calculator"]
    )
    
    # Main content area
    if calculator_choice == "CII Calculator":
        show_cii_calculator()
    elif calculator_choice == "Heel Calculator":
        st.title("Heel Calculator - Coming Soon")
    elif calculator_choice == "BOG Calculator":
        st.title("BOG Calculator - Coming Soon")

if __name__ == "__main__":
    main()
