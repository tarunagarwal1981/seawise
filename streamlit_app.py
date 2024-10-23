import streamlit as st

# Set page config at the very start
st.set_page_config(page_title="Seawise Calculators", layout="wide", page_icon="🚢")

# Import calculators
from calculators.cii_calculator import show_cii_calculator

# Add custom CSS to control sidebar width and main content
st.markdown("""
    <style>
    .main > div {
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100%;  /* Allow main content to use full width */
    }
    .stSidebar > div {
        width: 270px;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    section[data-testid="stSidebar"] {
        width: 270px !important;
    }
    /* Make main container use more width */
    .block-container {
        max-width: 95% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    /* Adjust the data editor and map container widths */
    [data-testid="column"] {
        width: 100% !important;
    }
    .stDataFrame {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    with st.sidebar:
        st.title("Navigation")
        calculator_choice = st.radio(
            "Select Calculator",
            ["CII Calculator", "Heel Calculator", "BOG Calculator"],
            label_visibility="collapsed"
        )
    
    if calculator_choice == "CII Calculator":
        show_cii_calculator()
    elif calculator_choice == "Heel Calculator":
        st.title("Heel Calculator - Coming Soon")
    elif calculator_choice == "BOG Calculator":
        st.title("BOG Calculator - Coming Soon")

if __name__ == "__main__":
    main()
