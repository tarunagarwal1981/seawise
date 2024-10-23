import streamlit as st
from src.calculators.cii_calculator import show_cii_calculator

def main():
    st.sidebar.title("Navigation")
    
    # Radio button for calculator selection
    calculator_choice = st.sidebar.radio(
        "Select Calculator",
        ["CII Calculator", "Heel Calculator", "BOG Calculator"]
    )
    
    # Display selected calculator
    if calculator_choice == "CII Calculator":
        show_cii_calculator()
    elif calculator_choice == "Heel Calculator":
        st.title("Heel Calculator - Coming Soon")
    elif calculator_choice == "BOG Calculator":
        st.title("BOG Calculator - Coming Soon")

if __name__ == "__main__":
    main()
