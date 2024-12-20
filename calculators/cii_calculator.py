import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import urllib.parse
from datetime import date, timedelta
import folium
from streamlit_folium import st_folium
import searoute as sr
from fuzzywuzzy import process

# All database configuration, emission factors and vessel type mapping at module level
DB_CONFIG = {
    'host': 'aws-0-ap-south-1.pooler.supabase.com',
    'database': 'postgres',
    'user': 'postgres.conrxbcvuogbzfysomov',
    'password': 'wXAryCC8@iwNvj#',
    'port': '6543'
}

EMISSION_FACTORS = {
    'VLSFO': 3.151,
    'LSMGO': 3.206,
    'LNG': 2.75
}

VESSEL_TYPE_MAPPING = {
    'ASPHALT/BITUMEN TANKER': 'tanker',
    'BULK CARRIER': 'bulk_carrier',
    'CEMENT CARRIER': 'bulk_carrier',
    'CHEM/PROD TANKER': 'tanker',
    'CHEMICAL TANKER': 'tanker',
    'Chemical/Products Tanker': 'tanker',
    'Combination Carrier': 'combination_carrier',
    'CONTAINER': 'container_ship',
    'Container Ship': 'container_ship',
    'Container/Ro-Ro Ship': 'ro_ro_cargo_ship',
    'Crude Oil Tanker': 'tanker',
    'Gas Carrier': 'gas_carrier',
    'General Cargo Ship': 'general_cargo_ship',
    'LNG CARRIER': 'lng_carrier',
    'LPG CARRIER': 'gas_carrier',
    'LPG Tanker': 'gas_carrier',
    'OIL TANKER': 'tanker',
    'Products Tanker': 'tanker',
    'Refrigerated Cargo Ship': 'refrigerated_cargo_carrier',
    'Ro-Ro Ship': 'ro_ro_cargo_ship',
    'Vehicle Carrier': 'ro_ro_cargo_ship_vc'
}

def get_db_engine():
    """Create and return database engine"""
    encoded_password = urllib.parse.quote(DB_CONFIG['password'])
    db_url = f"postgresql+psycopg2://{DB_CONFIG['user']}:{encoded_password}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    return create_engine(db_url)

def get_vessel_data(engine, vessel_name, year):
    """Fetch vessel data from database"""
    query = text("""
    SELECT 
        t1."VESSEL_NAME" AS "Vessel",
        t1."VESSEL_IMO" AS "IMO",
        SUM("DISTANCE_TRAVELLED_ACTUAL") AS "total_distance",
        COALESCE((SUM("FUEL_CONSUMPTION_HFO") - SUM("FC_FUEL_CONSUMPTION_HFO")) * 3.114, 0) + 
        COALESCE((SUM("FUEL_CONSUMPTION_LFO") - SUM("FC_FUEL_CONSUMPTION_LFO")) * 3.151, 0) + 
        COALESCE((SUM("FUEL_CONSUMPTION_GO_DO") - SUM("FC_FUEL_CONSUMPTION_GO_DO")) * 3.206, 0) + 
        COALESCE((SUM("FUEL_CONSUMPTION_LNG") - SUM("FC_FUEL_CONSUMPTION_LNG")) * 2.75, 0) + 
        COALESCE((SUM("FUEL_CONSUMPTION_LPG") - SUM("FC_FUEL_CONSUMPTION_LPG")) * 3.00, 0) + 
        COALESCE((SUM("FUEL_CONSUMPTION_METHANOL") - SUM("FC_FUEL_CONSUMPTION_METHANOL")) * 1.375, 0) + 
        COALESCE((SUM("FUEL_CONSUMPTION_ETHANOL") - SUM("FC_FUEL_CONSUMPTION_ETHANOL")) * 1.913, 0) AS "CO2Emission",
        t2."deadweight" AS "capacity",
        t2."vessel_type",
        ROUND(CAST(SUM("DISTANCE_TRAVELLED_ACTUAL") * t2."deadweight" AS NUMERIC), 2) AS "Transportwork",
        CASE 
            WHEN ROUND(CAST(SUM("DISTANCE_TRAVELLED_ACTUAL") * t2."deadweight" AS NUMERIC), 2) <> 0 
            THEN ROUND(CAST((
                COALESCE((SUM("FUEL_CONSUMPTION_HFO") - SUM("FC_FUEL_CONSUMPTION_HFO")) * 3.114, 0) + 
                COALESCE((SUM("FUEL_CONSUMPTION_LFO") - SUM("FC_FUEL_CONSUMPTION_LFO")) * 3.151, 0) + 
                COALESCE((SUM("FUEL_CONSUMPTION_GO_DO") - SUM("FC_FUEL_CONSUMPTION_GO_DO")) * 3.206, 0) + 
                COALESCE((SUM("FUEL_CONSUMPTION_LNG") - SUM("FC_FUEL_CONSUMPTION_LNG")) * 2.75, 0) + 
                COALESCE((SUM("FUEL_CONSUMPTION_LPG") - SUM("FC_FUEL_CONSUMPTION_LPG")) * 3.00, 0) + 
                COALESCE((SUM("FUEL_CONSUMPTION_METHANOL") - SUM("FC_FUEL_CONSUMPTION_METHANOL")) * 1.375, 0) + 
                COALESCE((SUM("FUEL_CONSUMPTION_ETHANOL") - SUM("FC_FUEL_CONSUMPTION_ETHANOL")) * 1.913, 0)
            ) * 1000000 / (SUM("DISTANCE_TRAVELLED_ACTUAL") * t2."deadweight") AS NUMERIC), 2)
            ELSE NULL
        END AS "Attained_AER"
    FROM 
        "sf_consumption_logs" AS t1
    LEFT JOIN 
        "vessel_particulars" AS t2 ON t1."VESSEL_IMO" = t2."vessel_imo"
    WHERE 
        t1."VESSEL_NAME" = :vessel_name
        AND EXTRACT(YEAR FROM "REPORT_DATE") = :year
    GROUP BY 
        t1."VESSEL_NAME", t1."VESSEL_IMO", t2."deadweight", t2."vessel_type"
    """)
    
    try:
        return pd.read_sql(query, engine, params={'vessel_name': vessel_name, 'year': year})
    except Exception as e:
        st.error(f"Error executing SQL query: {str(e)}")
        return pd.DataFrame()

def calculate_reference_cii(capacity, ship_type):
    """Calculate reference CII based on capacity and ship type"""
    params = {
        'bulk_carrier': [{'capacity_threshold': 279000, 'a': 4745, 'c': 0.622}],
        'gas_carrier': [{'capacity_threshold': 65000, 'a': 144050000000, 'c': 2.071}],
        'tanker': [{'capacity_threshold': float('inf'), 'a': 5247, 'c': 0.61}],
        'container_ship': [{'capacity_threshold': float('inf'), 'a': 1984, 'c': 0.489}],
        'general_cargo_ship': [{'capacity_threshold': float('inf'), 'a': 31948, 'c': 0.792}],
        'refrigerated_cargo_carrier': [{'capacity_threshold': float('inf'), 'a': 4600, 'c': 0.557}],
        'lng_carrier': [{'capacity_threshold': 100000, 'a': 144790000000000, 'c': 2.673}],
    }
    
    ship_params = params.get(ship_type.lower())
    if not ship_params:
        raise ValueError(f"Unknown ship type: {ship_type}")
    
    a, c = ship_params[0]['a'], ship_params[0]['c']
    return a * (capacity ** -c)

def calculate_required_cii(reference_cii, year):
    """Calculate required CII based on reference CII and year"""
    reduction_factors = {2023: 0.95, 2024: 0.93, 2025: 0.91, 2026: 0.89}
    return reference_cii * reduction_factors.get(year, 1.0)

def calculate_cii_rating(attained_cii, required_cii):
    """Calculate CII rating based on attained and required CII"""
    if attained_cii <= required_cii:
        return 'A'
    elif attained_cii <= 1.05 * required_cii:
        return 'B'
    elif attained_cii <= 1.1 * required_cii:
        return 'C'
    elif attained_cii <= 1.15 * required_cii:
        return 'D'
    else:
        return 'E'

@st.cache_data
def load_world_ports():
    """Load and cache world ports data"""
    return pd.read_csv("UpdatedPub150.csv")

def calculate_segment_metrics(row, world_ports_data):
    """Calculate metrics for a single voyage segment"""
    if not all([row[0], row[1], row[2], row[3], row[4], row[5]]):  # Check if all required fields are filled
        return None
    
    try:
        distance = route_distance(row[0], row[1], world_ports_data)
        sea_time = distance / (row[3] * 24)  # speed in knots
        total_time = sea_time + row[2]  # port days
        co2_emissions = row[4] * sea_time * EMISSION_FACTORS[row[5]]  # fuel used * emission factor
        
        return {
            'from_port': row[0],
            'to_port': row[1],
            'distance': distance,
            'sea_time': sea_time,
            'port_time': row[2],
            'total_time': total_time,
            'speed': row[3],
            'fuel_used': row[4],
            'fuel_type': row[5],
            'co2_emissions': co2_emissions
        }
    except Exception as e:
        st.error(f"Error calculating segment metrics: {str(e)}")
        return None

def route_distance(origin, destination, world_ports_data):
    """Calculate route distance between two ports"""
    try:
        origin_port = world_port_index(origin, world_ports_data)
        destination_port = world_port_index(destination, world_ports_data)
        origin_coords = [float(origin_port['Longitude']), float(origin_port['Latitude'])]
        destination_coords = [float(destination_port['Longitude']), float(destination_port['Latitude'])]
        sea_route = sr.searoute(origin_coords, destination_coords, units="naut")
        return int(sea_route['properties']['length'])
    except Exception as e:
        st.error(f"Error calculating distance between {origin} and {destination}: {str(e)}")
        return 0

def world_port_index(port_to_match, world_ports_data):
    """Find best matching port from world ports data"""
    best_match = process.extractOne(port_to_match, world_ports_data['Main Port Name'])
    return world_ports_data[world_ports_data['Main Port Name'] == best_match[0]].iloc[0]

def plot_route(ports, world_ports_data):
    """Plot route on a Folium map"""
    m = folium.Map(location=[0, 0], zoom_start=2)
    
    if len(ports) >= 2 and all(ports):
        coordinates = []
        for i in range(len(ports) - 1):
            try:
                start_port = world_port_index(ports[i], world_ports_data)
                end_port = world_port_index(ports[i+1], world_ports_data)
                start_coords = [float(start_port['Latitude']), float(start_port['Longitude'])]
                end_coords = [float(end_port['Latitude']), float(end_port['Longitude'])]
                
                folium.Marker(
                    start_coords,
                    popup=ports[i],
                    icon=folium.Icon(color='green' if i == 0 else 'blue')
                ).add_to(m)
                
                if i == len(ports) - 2:
                    folium.Marker(
                        end_coords,
                        popup=ports[i+1],
                        icon=folium.Icon(color='red')
                    ).add_to(m)
                
                route = sr.searoute(start_coords[::-1], end_coords[::-1])
                folium.PolyLine(
                    locations=[list(reversed(coord)) for coord in route['geometry']['coordinates']], 
                    color="red",
                    weight=2,
                    opacity=0.8
                ).add_to(m)
                
                coordinates.extend([start_coords, end_coords])
            except Exception as e:
                st.error(f"Error plotting route for {ports[i]} to {ports[i+1]}: {str(e)}")
        
        if coordinates:
            m.fit_bounds(coordinates)
    
    return m

def calculate_projected_cii(current_data, voyage_calculations):
    """Calculate projected CII based on current data and planned voyage"""
    if not voyage_calculations:
        return None
    
    try:
        total_new_distance = sum(seg['distance'] for seg in voyage_calculations)
        total_new_co2 = sum(seg['co2_emissions'] for seg in voyage_calculations)
        
        current_distance = current_data.get('total_distance', 0)
        current_co2 = current_data.get('co2_emission', 0)
        capacity = current_data.get('capacity', 0)
        
        if capacity <= 0:
            raise ValueError("Invalid vessel capacity")
            
        total_distance = current_distance + total_new_distance
        total_co2 = current_co2 + total_new_co2
        
        projected_aer = (total_co2 * 1000000) / (total_distance * capacity)
        
        return {
            'projected_aer': projected_aer,
            'new_distance': total_new_distance,
            'new_co2': total_new_co2,
            'total_distance': total_distance,
            'total_co2': total_co2
        }
    except Exception as e:
        st.error(f"Error calculating projected CII: {str(e)}")
        return None

def show_cii_calculator():
    """Main function to show CII calculator interface"""
    
    st.markdown("""
    <style>
    /* Calculator specific styles */
    .stButton > button {
        background-color: #00AAFF !important;
        color: #0F1824 !important;
        font-family: 'Nunito', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }
    
    .metric-card {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Nunito', sans-serif !important;
        font-size: 12px !important;
        color: #F4F4F4 !important;
    }
    
    /* Calculator specific text */
    .st-emotion-cache-10trblm {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
    }
    
    .st-emotion-cache-16idsys {
        font-family: 'Nunito', sans-serif !important;
        color: #F4F4F4 !important;
    }

    /* Enhanced dropdown styling for data editor */
    .st-emotion-cache-1umgx7l select,
    .st-emotion-cache-1umgx7l option,
    .st-emotion-cache-1umgx7l,
    div[data-baseweb="select"] * {
        color: #132337 !important;
        opacity: 1 !important;
    }

    /* Specific styling for cells and dropdowns */
    .st-emotion-cache-1n76uvr {
        color: #132337 !important;
        opacity: 1 !important;
    }

    /* Ensure dropdowns and their options are dark */
    [data-testid="stDataFrameCell"] select,
    [data-testid="stDataFrameCell"] option,
    .stDataFrame select,
    .stDataFrame option,
    div[role="listbox"] * {
        color: #132337 !important;
        opacity: 1 !important;
        font-weight: 500 !important;
    }

    /* Styling for None/placeholder text */
    .st-emotion-cache-1umgx7l select option[value="None"],
    [data-testid="stDataFrameCell"] select option[value="None"] {
        color: #132337 !important;
        opacity: 1 !important;
    }

    /* Custom styling for select boxes */
    select.st-emotion-cache-1umgx7l,
    select.st-emotion-cache-1n76uvr {
        color: #132337 !important;
        opacity: 1 !important;
    }

     /* Custom placeholder above button */
    .placeholder-text {
        color: #132337 !important;
    }

    /* Table styles */
    .metrics-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
    }
    .metrics-table th, .metrics-table td {
        border: 1px solid #F4F4F4;
        padding: 0.5rem;
        text-align: center;
    }
    .metrics-table th {
        background-color: #6E6E6E;
        color: #F4F4F4;
        font-weight: 600;
    }

    /* Container for bottom alignment */
    .button-column {
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-end !important;
        padding-top: 29px !important;  /* Offset for missing label */
    }
    
    /* Hide default Streamlit label space */
    .st-emotion-cache-16idsys p {
        margin-bottom: 0px !important;
    }

    /* Force dark text in data editor cells */
    .stDataFrame div[role="cell"],
    .stDataFrame div[role="cell"] * {
        color: #132337 !important;
        opacity: 1 !important;
    }

    /* Additional selector for dropdown text */
    div[data-baseweb="select"] div[title],
    div[data-baseweb="select"] span {
        color: #132337 !important;
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'cii_data' not in st.session_state:
        st.session_state.cii_data = {}
    if 'port_table_data' not in st.session_state:
        st.session_state.port_table_data = []
    if 'voyage_calculations' not in st.session_state:
        st.session_state.voyage_calculations = []

    st.title('🚢 CII Calculator')

    # Load world ports data
    world_ports_data = load_world_ports()

    # User inputs for vessel and year
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        vessel_name = st.text_input("Enter Vessel Name")
        
    with col2:
        year = st.number_input('Year for CII Calculation', 
                              min_value=2023, 
                              max_value=date.today().year, 
                              value=date.today().year)

    with col3:
        st.markdown('<div class="button-column">', unsafe_allow_html=True)
        calculate_clicked = st.button(
            'Calculate Current CII', 
            use_container_width=True, 
            key='calculate_current_cii_button', 
            help='Calculate the current CII metrics based on the vessel and year input.'
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col6:
        st.markdown('<div class="button-column">', unsafe_allow_html=True)
        draft_voyage_clicked = st.button(
            'Draft Voyage', 
            use_container_width=True, 
            key='draft_voyage_button', 
            help='Auto-fill sample data for Draft Voyage calculation.'
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Draft Voyage Logic
    if draft_voyage_clicked:
        vessel_name = "TRAMMO MARYCAM"
        year = date.today().year
        engine = get_db_engine()
        df = get_vessel_data(engine, vessel_name, year)

        if not df.empty:
            vessel_type = df['vessel_type'].iloc[0]
            imo_ship_type = VESSEL_TYPE_MAPPING.get(vessel_type)
            capacity = df['capacity'].iloc[0]
            attained_aer = df['Attained_AER'].iloc[0]

            if imo_ship_type and attained_aer is not None:
                reference_cii = calculate_reference_cii(capacity, imo_ship_type)
                required_cii = calculate_required_cii(reference_cii, year)
                cii_rating = calculate_cii_rating(attained_aer, required_cii)
                
                st.session_state.cii_data = {
                    'attained_aer': round(attained_aer, 2),
                    'required_cii': round(required_cii, 2),
                    'cii_rating': cii_rating,
                    'total_distance': df['total_distance'].iloc[0],
                    'co2_emission': df['CO2Emission'].iloc[0],
                    'capacity': capacity,
                    'vessel_type': vessel_type,
                    'imo_ship_type': imo_ship_type
                }

                # Pre-fill Route Information
                st.session_state.port_table_data = [
                    ["Ras Laffan", "Milford Haven", 2.0, 20.0, 50.0, "LNG"],
                    ["Milford haven", "Rotterdam", 3.0, 15.0, 40.0, "LNG"]
                ]

                # Automatically trigger the calculation of Projected CII
                st.session_state.calculate_projected = True

    # Calculate current CII
    if calculate_clicked and vessel_name:
        engine = get_db_engine()
        df = get_vessel_data(engine, vessel_name, year)
        
        if not df.empty:
            vessel_type = df['vessel_type'].iloc[0]
            imo_ship_type = VESSEL_TYPE_MAPPING.get(vessel_type)
            capacity = df['capacity'].iloc[0]
            attained_aer = df['Attained_AER'].iloc[0]

            if imo_ship_type and attained_aer is not None:
                reference_cii = calculate_reference_cii(capacity, imo_ship_type)
                required_cii = calculate_required_cii(reference_cii, year)
                cii_rating = calculate_cii_rating(attained_aer, required_cii)
                
                st.session_state.cii_data = {
                    'attained_aer': round(attained_aer, 2),
                    'required_cii': round(required_cii, 2),
                    'cii_rating': cii_rating,
                    'total_distance': df['total_distance'].iloc[0],
                    'co2_emission': df['CO2Emission'].iloc[0],
                    'capacity': capacity,
                    'vessel_type': vessel_type,
                    'imo_ship_type': imo_ship_type
                }
            else:
                if imo_ship_type is None:
                    st.error(f"The vessel type '{vessel_type}' is not supported for CII calculations.")
                if attained_aer is None:
                    st.error("Unable to calculate Attained AER. Please check the vessel's data.")
        else:
            st.error(f"No data found for vessel {vessel_name} in year {year}")

    # Display current CII results if available
    if st.session_state.get('cii_data'):
        st.markdown("### Current CII Metrics")
        st.markdown("""
        <table class="metrics-table">
            <thead>
                <tr>
                    <th>Attained AER</th>
                    <th>Required CII</th>
                    <th>CII Rating</th>
                    <th>Total Distance (NM)</th>
                    <th>CO2 Emission (MT)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{:.2f}</td>
                    <td>{:.2f}</td>
                    <td>{}</td>
                    <td>{:,.0f}</td>
                    <td>{:,.1f}</td>
                </tr>
            </tbody>
        </table>
        """.format(
            st.session_state.cii_data['attained_aer'],
            st.session_state.cii_data['required_cii'],
            st.session_state.cii_data['cii_rating'],
            st.session_state.cii_data['total_distance'],
            st.session_state.cii_data['co2_emission']
        ), unsafe_allow_html=True)

    # Voyage Planning Section
    col1, col2 = st.columns([7, 1])

    with col1: 
        st.markdown("### Voyage Planning")  
    with col2:
        calculate_projected = st.button(
            'Calculate Projected CII', 
            disabled=not bool(st.session_state.cii_data),
            help="Current CII calculation required before projecting future CII",
            use_container_width=True,
            key="calculate_projected_cii_button"
        )

    if draft_voyage_clicked and st.session_state.get('calculate_projected'):
        calculate_projected = True

    # Split layout for table and map
    left_col, right_col = st.columns([6, 6])

    # Route information table
    with left_col:
        st.markdown("#### Route Information")
        
        port_data_df = pd.DataFrame(
            st.session_state.port_table_data,
            columns=["From Port", "To Port", "Port Days", "Speed (knots)", 
                    "Fuel Used (mT)", "Fuel Type"]
        )
        
        edited_df = st.data_editor(
        port_data_df,
        num_rows="dynamic",
        key="port_table_editor",
        column_config={
            "From Port": st.column_config.TextColumn(
                "From Port",
                help="Enter departure port name",
                required=True
            ),
            "To Port": st.column_config.TextColumn(
                "To Port",
                help="Enter arrival port name",
                required=True
            ),
            "Port Days": st.column_config.NumberColumn(
                "Port Days",
                help="Enter number of days in port",
                min_value=0,
                max_value=100,
                step=0.5,
                required=True
            ),
            "Speed (knots)": st.column_config.NumberColumn(
                "Speed (knots)",
                help="Enter vessel speed in knots",
                min_value=1,
                max_value=30,
                step=0.1,
                required=True
            ),
            "Fuel Used (mT)": st.column_config.NumberColumn(
                "Fuel Consumption (mT/d)",
                help="Enter total fuel consumption",
                min_value=0,
                step=0.1,
                required=True
            ),
            "Fuel Type": st.column_config.SelectboxColumn(
                "Fuel Type",
                help="Select fuel type",
                options=["VLSFO", "LSMGO", "LNG"],
                required=True,
                width="medium"
            )
        }
    )
        
        st.session_state.port_table_data = edited_df.values.tolist()

        # Display Projected CII Metrics table here
        if calculate_projected and st.session_state.port_table_data:
            voyage_calculations = []
            for row in st.session_state.port_table_data:
                segment_metrics = calculate_segment_metrics(row, world_ports_data)
                if segment_metrics:
                    voyage_calculations.append(segment_metrics)
            
            if voyage_calculations:
                projections = calculate_projected_cii(st.session_state.cii_data, voyage_calculations)
                
                if projections:
                    st.markdown("### Projected CII Metrics")
                    st.markdown("""
                    <table class="metrics-table">
                        <thead>
                            <tr>
                                <th>Projected AER</th>
                                <th>Projected CII Rating</th>
                                <th>Additional CO2 (MT)</th>
                                <th>Total Distance (NM)</th>
                                <th>Total CO2 (MT)</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>{:.2f}</td>
                                <td>{}</td>
                                <td>{:,.1f}</td>
                                <td>{:,.0f}</td>
                                <td>{:,.1f}</td>
                            </tr>
                        </tbody>
                    </table>
                    """.format(
                        round(projections['projected_aer'], 2),
                        calculate_cii_rating(projections['projected_aer'], st.session_state.cii_data['required_cii']),
                        projections['new_co2'],
                        projections['total_distance'],
                        projections['total_co2']
                    ), unsafe_allow_html=True)

    # Map display
    with right_col:
        if len(st.session_state.port_table_data) >= 1:
            ports = [row[0] for row in st.session_state.port_table_data if row[0]]
            if st.session_state.port_table_data[-1][1]:
                ports.append(st.session_state.port_table_data[-1][1])
            
            if len(ports) >= 2:
                m = plot_route(ports, world_ports_data)
            else:
                m = folium.Map(location=[0, 0], zoom_start=2)
        else:
            m = folium.Map(location=[0, 0], zoom_start=2)
        
        st_folium(m, width=None, height=400)

    st.markdown("""
        <style>
        div[data-testid="stButton"] button[kind="secondary"] {
            background-color: #00AAFF !important;
            color: #0F1824 !important;
            font-family: 'Nunito', sans-serif !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            border: none !important;
            border-radius: 4px !important;
            padding: 0.5rem 1rem !important;
        }
        </style>
    """, unsafe_allow_html=True)
