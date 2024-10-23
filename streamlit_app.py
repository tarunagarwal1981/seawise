import streamlit as st

# Set page config at the very start
st.set_page_config(page_title="Seawise Calculators", layout="wide", page_icon="🚢")

# Import calculators
from calculators.cii_calculator import show_cii_calculator

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
        font-family: 'Nunito', sans-serif;
        font-size: 12px;
        color: #F4F4F4;
    }
    
    /* Sidebar styles */
    .stSidebar > div {
        width: 270px;
        padding-left: 1rem;
        padding-right: 1rem;
        background-color: #132337;
        font-family: 'Nunito', sans-serif;
        color: #F4F4F4;
    }
    
    section[data-testid="stSidebar"] {
        width: 270px !important;
        background-color: #132337;
    }
    
    /* Main container styles */
    .block-container {
        max-width: 95% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    
    /* Column styles */
    [data-testid="column"] {
        width: 100% !important;
    }
    
    /* DataFrame styles */
    .stDataFrame {
        width: 100% !important;
    }
    
    /* Generic text styles */
    p, label, .streamlit-expanderHeader {
        font-family: 'Nunito', sans-serif !important;
        font-size: 12px !important;
        color: #F4F4F4 !important;
    }
    
    /* Header styles */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
    }
    
    /* Navigation and radio button text */
    .st-emotion-cache-16idsys {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
    }
    
    /* Titles */
    .st-emotion-cache-10trblm {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
    }
    
    /* Adjust global background */
    .stApp {
        background-color: #132337;
    }
    
    /* Input fields */
    .stTextInput > div > div {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
    }
    
    /* Button text */
    .stButton > button {
        font-family: 'Nunito', sans-serif !important;
        font-size: 12px !important;
    }
    
    /* DataEditor text */
    .st-emotion-cache-1eqh1f1 {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
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
