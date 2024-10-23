import streamlit as st

def show_cii_calculator():
    st.title("CII Calculator")
    # Your CII calculator code here

def main():
    st.sidebar.title("Navigation")
    
    calculator_choice = st.sidebar.radio(
        "Select Calculator",
        ["CII Calculator", "Heel Calculator", "BOG Calculator"]
    )
    
    if calculator_choice == "CII Calculator":
        show_cii_calculator()
    elif calculator_choice == "Heel Calculator":
        st.title("Heel Calculator - Coming Soon")
    elif calculator_choice == "BOG Calculator":
        st.title("BOG Calculator - Coming Soon")

if __name__ == "__main__":
    main()
