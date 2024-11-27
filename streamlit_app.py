import streamlit as st

# Set page config at the very start
st.set_page_config(page_title="Seawise Calculators", layout="wide", page_icon="🚢")

# Import calculators
from calculators.cii_calculator import show_cii_calculator
from calculators.lng_heel_management import show_lng_heel_calculator



# Add custom CSS to control sidebar width and main content
st.markdown("""
    <style>
    /* Import Nunito font */
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap');
    
    /* Global styles */
    .main > div {
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100%;
        background-color: #132337;
        font-family: 'Nunito', sans-serif !important;
        font-size: 14px;
        color: #F4F4F4;
    }
    
    /* Sidebar styles */
    .stSidebar > div {
        width: 270px;
        padding-left: 1rem;
        padding-right: 1rem;
        background-color: #132337;
        color: #F4F4F4;
    }
    
    /* Button styles */
    .stButton > button {
        background-color: #00AAFF !important;
        color: #0F1824 !important;
        font-family: 'Nunito', sans-serif !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 0.5rem 1rem !important;
    }
    
    .stButton > button:hover {
        background-color: #0095e0 !important;
        color: #0F1824 !important;
    }
    
    /* Main container styles */
    .block-container {
        max-width: 80% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        background-color: #132337;
    }
    
    /* App background */
    .stApp {
        background-color: #132337;
    }
    
    /* Text styles */
    p, label, span, div {
        font-family: 'Nunito', sans-serif !important;
        font-size: 12px !important;
        color: #F4F4F4 !important;
    }
    
    /* Header styles */
    h1, h2, h3, h4, h5, h6, .st-emotion-cache-10trblm {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
    }
    
    /* Radio buttons and navigation */
    .st-emotion-cache-16idsys {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
    }
    
    /* Input fields */
    .stTextInput > div > div {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Number input */
    .stNumberInput > div > div {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Data editor */
    .st-emotion-cache-1eqh1f1 {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
    }
    
    /* Metric cards */
    .metric-card {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Nunito', sans-serif !important;
        font-size: 14px !important;
        color: #F4F4F4 !important;
    }
    
    /* Sidebar navigation */
    section[data-testid="stSidebar"] {
        width: 270px !important;
        background-color: #132337;
    }
    
    /* Column layouts */
    [data-testid="column"] {
        width: 100% !important;
    }
    
    /* DataFrame */
    .stDataFrame {
        width: 100% !important;
    }
    
    /* Select boxes and dropdowns */
    .stSelectbox > div > div {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Radio buttons */
    .st-emotion-cache-1k5q1ln {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
    }

    /* Top bar styling */
    header {
        background-color: #132337 !important;
    }

    /* Top bar buttons */
    .st-emotion-cache-h5rgaw {
        background-color: #132337 !important;
    }

    /* Hide decoration */
    .decoration {
        background-color: #132337 !important;
    }

    /* Top bar icons/elements */
    .st-emotion-cache-1dp5vir {
        background-color: #132337 !important;
        color: #F4F4F4 !important;
    }

    /* View toolbar */
    .st-emotion-cache-r421ms {
        background-color: #132337 !important;
    }

    /* All top bar elements */
    .st-emotion-cache-1avcm0n, .st-emotion-cache-2door3 {
        background-color: #132337 !important;
        color: #F4F4F4 !important;
    }

    /* Main content area */
    .main .block-container {
        padding-top: 2rem !important;
        max-width: 95% !important;
    }

    /* Ensure all icons in header are white */
    header .st-emotion-cache-1dp5vir svg {
        color: #F4F4F4 !important;
    }

    /* Style the top right menu */
    .st-emotion-cache-v4z8rs {
        background-color: #132337 !important;
    }

    /* Additional button styles for hover states */
    .stButton > button:active {
        transform: scale(0.98);
    }
    </style>
    """, unsafe_allow_html=True)

# def main():
#     # Directly show the CII Calculator
#     show_cii_calculator()

# if __name__ == "__main__":
#     main()

def main():
    with st.sidebar:
        st.title("Navigation")
        # Add a unique key to the radio button
        calculator_choice = st.radio(
            "Select Calculator",
            ["CII Calculator", "Heel Calculator", "BOG Calculator"],
            label_visibility="collapsed",
            key="calculator_selector"  # Added unique key
        )
    
    if calculator_choice == "CII Calculator":
        show_cii_calculator()
    elif calculator_choice == "Heel Calculator":
        show_lng_heel_calculator()
    elif calculator_choice == "BOG Calculator":
        st.title("BOG Calculator - Coming Soon")

if __name__ == "__main__":
    main()
