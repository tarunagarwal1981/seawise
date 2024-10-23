import streamlit as st

# Set page config at the very start
st.set_page_config(page_title="Seawise Calculators", layout="wide", page_icon="🚢")

# Import calculators
from calculators.cii_calculator import show_cii_calculator

# Add custom CSS to control sidebar width and main content
st.markdown("""
    <style>
    /* Previous CSS remains the same */
    
    /* Button styles */
    .stButton > button {
        background-color: #00AAFF !important;
        color: #0F1824 !important;
        font-family: 'Nunito', sans-serif !important;
        font-size: 12px !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        border-radius: 4px !important;
    }
    
    /* Button hover state */
    .stButton > button:hover {
        background-color: #0099EA !important;  /* Slightly darker shade for hover */
        color: #0F1824 !important;
    }
    
    /* Number input step buttons */
    .stNumberInput button {
        background-color: #00AAFF !important;
        color: #0F1824 !important;
    }
    
    /* Disabled button state */
    .stButton > button:disabled {
        background-color: #004C73 !important;  /* Darker shade for disabled state */
        color: #0F1824 !important;
        opacity: 0.7;
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
