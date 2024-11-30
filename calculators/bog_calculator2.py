import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
import searoute as sr
from fuzzywuzzy import process
import plotly.graph_objects as go
import plotly.express as px

# Core Helper Functions
@st.cache_data
def load_world_ports():
    """Load and cache world ports data"""
    try:
        return pd.read_csv("UpdatedPub150.csv")
    except:
        return pd.DataFrame({
            'Main Port Name': ['SINGAPORE', 'ROTTERDAM', 'FUJAIRAH', 'YOKOHAMA', 'BUSAN'],
            'Latitude': [1.290270, 51.916667, 25.112225, 35.443708, 35.179554],
            'Longitude': [103.855836, 4.5, 56.336096, 139.638026, 129.075642]
        })

@st.cache_data
def get_vessel_configs():
    """Get vessel configuration data"""
    return {
        "174K": {
            "tank_capacity": 174000.0,
            "min_heel": 1500.0,
            "max_heel": 3000.0,
            "base_bog_rate": 0.15,
            "reliq_capacity": 2.5,
            "engine_efficiency": 0.45
        },
        "180K": {
            "tank_capacity": 180000.0,
            "min_heel": 1600.0,
            "max_heel": 3200.0,
            "base_bog_rate": 0.14,
            "reliq_capacity": 2.8,
            "engine_efficiency": 0.46
        }
    }

def world_port_index(port_to_match, world_ports_data):
    """Find best matching port from world ports data"""
    if not port_to_match:
        return None
    best_match = process.extractOne(port_to_match, world_ports_data['Main Port Name'])
    return world_ports_data[world_ports_data['Main Port Name'] == best_match[0]].iloc[0]

def route_distance(origin, destination, world_ports_data):
    """Calculate route distance between two ports"""
    try:
        origin_port = world_port_index(origin, world_ports_data)
        destination_port = world_port_index(destination, world_ports_data)
        
        if origin_port is None or destination_port is None:
            return 0.0

        origin_coords = [float(origin_port['Longitude']), float(origin_port['Latitude'])]
        destination_coords = [float(destination_port['Longitude']), float(destination_port['Latitude'])]
        
        sea_route = sr.searoute(origin_coords, destination_coords, units="naut")
        return float(sea_route['properties']['length'])
    except Exception as e:
        st.error(f"Error calculating distance: {str(e)}")
        return 0.0

# BOG Calculation Functions
def calculate_bog_rate(base_rate: float, tank_pressure: float, tank_level: float, 
                      ambient_temp: float, wave_height: float, solar_radiation: str) -> float:
    """Calculate BOG rate with all environmental factors"""
    pressure_factor = 1.0 + ((tank_pressure - 1013.0) / 1013.0) * 0.1
    level_factor = 1.0 + (1.0 - tank_level/100.0) * 0.05
    temp_factor = 1.0 + (ambient_temp - 19.5) / 100.0
    wave_factor = 1.0 + wave_height * 0.02
    solar_factors = {'Low': 1.0, 'Medium': 1.02, 'High': 1.05}
    
    total_factor = (pressure_factor * level_factor * temp_factor * 
                   wave_factor * solar_factors[solar_radiation])
    
    return float(base_rate * total_factor)

def calculate_daily_bog(initial_volume: float, days: float, base_bog_rate: float,
                       ambient_temps: list, wave_heights: list, solar_radiation: str,
                       tank_pressure: float, engine_consumption: float,
                       reliq_capacity: float, reliq_efficiency: float) -> pd.DataFrame:
    """Calculate daily BOG with incremental volume reduction"""
    daily_data = {
        'day': [],
        'remaining_volume': [],
        'bog_rate': [],
        'bog_generated': [],
        'bog_consumed': [],
        'bog_reliquefied': [],
        'tank_level': [],
        'temperature': [],
        'wave_height': []
    }
    
    remaining_volume = float(initial_volume)
    
    for day in range(int(days)):
        tank_level = (remaining_volume / initial_volume) * 100.0
        
        # Calculate daily BOG rate
        bog_rate = calculate_bog_rate(
            base_bog_rate,
            tank_pressure,
            tank_level,
            ambient_temps[day],
            wave_heights[day],
            solar_radiation
        )
        
        # Calculate BOG generated
        bog_generated = remaining_volume * (bog_rate / 100.0)
        
        # Calculate BOG consumed
        bog_consumed = min(bog_generated, engine_consumption)
        
        # Calculate BOG reliquefied
        bog_to_reliquify = bog_generated - bog_consumed
        bog_reliquefied = min(bog_to_reliquify, reliq_capacity) * reliq_efficiency
        
        # Update remaining volume
        remaining_volume = remaining_volume - bog_generated + bog_reliquefied
        
        # Store daily data
        daily_data['day'].append(float(day))
        daily_data['remaining_volume'].append(float(remaining_volume))
        daily_data['bog_rate'].append(float(bog_rate))
        daily_data['bog_generated'].append(float(bog_generated))
        daily_data['bog_consumed'].append(float(bog_consumed))
        daily_data['bog_reliquefied'].append(float(bog_reliquefied))
        daily_data['tank_level'].append(float(tank_level))
        daily_data['temperature'].append(float(ambient_temps[day]))
        daily_data['wave_height'].append(float(wave_heights[day]))
    
    return pd.DataFrame(daily_data)

def calculate_economics(daily_data: pd.DataFrame, lng_price: float,
                       bunker_price: float, electricity_cost: float,
                       power_consumption: float) -> dict:
    """Calculate comprehensive economics for the voyage"""
    total_bog_generated = float(daily_data['bog_generated'].sum())
    total_bog_consumed = float(daily_data['bog_consumed'].sum())
    total_bog_reliquefied = float(daily_data['bog_reliquefied'].sum())
    
    lng_cost = total_bog_generated * lng_price
    fuel_savings = total_bog_consumed * bunker_price
    reliq_cost = total_bog_reliquefied * power_consumption * electricity_cost * 24.0
    
    return {
        'lng_value_lost': float(lng_cost),
        'fuel_savings': float(fuel_savings),
        'reliq_cost': float(reliq_cost),
        'net_benefit': float(fuel_savings - reliq_cost),
        'total_bog_generated': total_bog_generated,
        'total_bog_consumed': total_bog_consumed,
        'total_bog_reliquefied': total_bog_reliquefied
    }
# Visualization Functions
def plot_combined_route(laden_ports, ballast_ports, world_ports_data):
    """Plot combined route on a single map"""
    m = folium.Map(location=[0, 0], zoom_start=2)
    all_ports = laden_ports + ballast_ports

    if len(all_ports) >= 2 and all(all_ports):
        coordinates = []
        for i in range(len(all_ports) - 1):
            try:
                start_port = world_port_index(all_ports[i], world_ports_data)
                end_port = world_port_index(all_ports[i + 1], world_ports_data)
                
                if start_port is None or end_port is None:
                    continue

                start_coords = [float(start_port['Latitude']), float(start_port['Longitude'])]
                end_coords = [float(end_port['Latitude']), float(end_port['Longitude'])]
                
                # Add port markers
                folium.Marker(
                    start_coords,
                    popup=all_ports[i],
                    icon=folium.Icon(color='green' if i == 0 else 'blue')
                ).add_to(m)
                
                if i == len(all_ports) - 2:
                    folium.Marker(
                        end_coords,
                        popup=all_ports[i + 1],
                        icon=folium.Icon(color='red')
                    ).add_to(m)
                
                # Add route line
                route = sr.searoute(start_coords[::-1], end_coords[::-1])
                folium.PolyLine(
                    locations=[list(reversed(coord)) for coord in route['geometry']['coordinates']], 
                    color="red",
                    weight=2,
                    opacity=0.8
                ).add_to(m)
                
                coordinates.extend([start_coords, end_coords])
            except Exception as e:
                st.error(f"Error plotting route: {str(e)}")
        
        if coordinates:
            m.fit_bounds(coordinates)
    
    return m

def plot_daily_tracking(daily_data: pd.DataFrame) -> go.Figure:
    """Create interactive plot for daily tracking"""
    fig = go.Figure()
    
    # Add traces for each metric
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['remaining_volume'],
        name='Remaining Volume',
        line=dict(color='blue')
    ))
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['bog_generated'],
        name='BOG Generated',
        line=dict(color='red')
    ))
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['bog_consumed'],
        name='BOG Consumed',
        line=dict(color='green')
    ))
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['bog_reliquefied'],
        name='BOG Reliquefied',
        line=dict(color='purple')
    ))
    
    fig.update_layout(
        title='Daily BOG Tracking',
        xaxis_title='Days',
        yaxis_title='Volume (m³)',
        hovermode='x unified'
    )
    
    return fig

def create_voyage_section(leg_type: str, world_ports_data: pd.DataFrame,
                         vessel_config: dict, is_ballast: bool = False) -> dict:
    """Create voyage section with comprehensive calculations"""
    st.subheader(f"{leg_type} Leg Details")
    
    tabs = st.tabs(["Cargo & Route", "Environmental", "Operations", "Economics", "Results"])
    
    # Cargo & Route Tab
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        with col1:
            if not is_ballast:
                initial_cargo = st.number_input(
                    "Initial Cargo Volume (m³)", 
                    min_value=0.0, 
                    max_value=float(vessel_config['tank_capacity']), 
                    value=float(vessel_config['tank_capacity'] * 0.98),
                    step=100.0,
                    key=f"{leg_type}_cargo"
                )
            else:
                initial_cargo = st.number_input(
                    "Heel Quantity (m³)", 
                    min_value=float(vessel_config['min_heel']),
                    max_value=float(vessel_config['max_heel']),
                    value=float(vessel_config['min_heel']),
                    step=100.0,
                    key=f"{leg_type}_heel"
                )
        
        with col2:
            voyage_from = st.text_input("From Port", key=f"{leg_type}_from")
        with col3:
            voyage_to = st.text_input("To Port", key=f"{leg_type}_to")
        
        distance = route_distance(voyage_from, voyage_to, world_ports_data)
        
        col1, col2 = st.columns(2)
        with col1:
            speed = st.number_input(
                "Speed (knots)", 
                min_value=1.0, 
                max_value=25.0, 
                value=15.0,
                step=0.1,
                key=f"{leg_type}_speed"
            )
        
        voyage_days = float(distance) / (float(speed) * 24.0) if speed > 0 else 0.0
        with col2:
            st.metric("Estimated Voyage Days", f"{voyage_days:.1f}")
    
    # Environmental Tab
    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            base_temp = st.number_input(
                "Base Temperature (°C)", 
                min_value=-20.0, 
                max_value=45.0, 
                value=19.5,
                step=0.5,
                key=f"{leg_type}_temp"
            )
            temp_variation = st.number_input(
                "Temperature Variation (±°C)", 
                min_value=0.0, 
                max_value=10.0, 
                value=2.0,
                step=0.1,
                key=f"{leg_type}_temp_var"
            )
        with col2:
            base_waves = st.number_input(
                "Base Wave Height (m)", 
                min_value=0.0, 
                max_value=10.0, 
                value=1.0,
                step=0.1,
                key=f"{leg_type}_waves"
            )
            wave_variation = st.number_input(
                "Wave Height Variation (±m)", 
                min_value=0.0, 
                max_value=5.0, 
                value=0.5,
                step=0.1,
                key=f"{leg_type}_wave_var"
            )
        
        solar_radiation = st.selectbox(
            "Solar Radiation",
            options=['Low', 'Medium', 'High'],
            key=f"{leg_type}_solar"
        )
        
        tank_pressure = st.number_input(
            "Tank Pressure (mbar)", 
            min_value=1000.0, 
            max_value=1300.0, 
            value=1013.0,
            step=1.0,
            key=f"{leg_type}_pressure"
        )
    
    # Operations Tab
    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            engine_consumption = st.number_input(
                "Engine Gas Consumption (m³/day)", 
                min_value=0.0, 
                max_value=500.0, 
                value=150.0,
                step=1.0,
                key=f"{leg_type}_consumption"
            )
            
            reliq_capacity = st.number_input(
                "Reliquefaction Capacity (m³/day)", 
                min_value=0.0, 
                max_value=float(vessel_config['reliq_capacity'] * 24),
                value=float(vessel_config['reliq_capacity'] * 24),
                step=1.0,
                key=f"{leg_type}_reliq"
            )
        
        with col2:
            power_consumption = st.number_input(
                "Power Consumption (kWh/m³)", 
                min_value=0.0, 
                max_value=1000.0, 
                value=800.0,
                step=1.0,
                key=f"{leg_type}_power"
            )
            
            reliq_efficiency = st.number_input(
                "Reliquefaction Efficiency (%)", 
                min_value=0.0, 
                max_value=100.0, 
                value=85.0,
                step=0.1,
                key=f"{leg_type}_efficiency"
            ) / 100.0
    
    # Economics Tab
    with tabs[3]:
        col1, col2 = st.columns(2)
        with col1:
            lng_price = st.number_input(
                "LNG Price ($/mmBTU)", 
                min_value=0.0, 
                max_value=50.0, 
                value=15.0,
                step=0.1,
                key=f"{leg_type}_lng_price"
            )
            
            bunker_price = st.number_input(
                "Bunker Price ($/mt)", 
                min_value=0.0, 
                max_value=2000.0, 
                value=800.0,
                step=1.0,
                key=f"{leg_type}_bunker"
            )
        
        with col2:
            electricity_cost = st.number_input(
                "Electricity Cost ($/kWh)", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.15,
                step=0.01,
                key=f"{leg_type}_electricity"
            )
    
    # Results Tab
    daily_data = None
    economics = None
    
    with tabs[4]:
        if voyage_days > 0:
            # Generate daily temperature and wave height profiles
            daily_temps = np.random.normal(base_temp, temp_variation, int(voyage_days))
            daily_waves = np.random.normal(base_waves, wave_variation, int(voyage_days))
            
            # Calculate daily BOG and volumes
            daily_data = calculate_daily_bog(
                initial_cargo,
                voyage_days,
                float(vessel_config['base_bog_rate']),
                daily_temps,
                daily_waves,
                solar_radiation,
                tank_pressure,
                engine_consumption,
                reliq_capacity,
                reliq_efficiency
            )
            
            # Calculate economics
            economics = calculate_economics(
                daily_data,
                lng_price,
                bunker_price,
                electricity_cost,
                power_consumption
            )
            
            # Display results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Final Cargo Volume", f"{daily_data['remaining_volume'].iloc[-1]:.1f} m³")
                st.metric("Total BOG Generated", f"{economics['total_bog_generated']:.1f} m³")
            
            with col2:
                st.metric("Total BOG Consumed", f"{economics['total_bog_consumed']:.1f} m³")
                st.metric("Total BOG Reliquefied", f"{economics['total_bog_reliquefied']:.1f} m³")
            
            with col3:
                st.metric("Net Cost Benefit", f"${economics['net_benefit']:,.2f}")
                st.metric("Reliquefaction Cost", f"${economics['reliq_cost']:,.2f}")
            
            # Plot daily tracking
            st.plotly_chart(plot_daily_tracking(daily_data), use_container_width=True)
            
            # Show detailed data table
            if st.checkbox("Show Detailed Daily Data", key=f"{leg_type}_show_data"):
                st.dataframe(daily_data.round(2))
    
    return {
        'voyage_from': voyage_from,
        'voyage_to': voyage_to,
        'distance': distance,
        'daily_data': daily_data,
        'economics': economics
    }

def show_bog_calculator():
    """Main function to show enhanced BOG calculator"""
    st.title("LNG Vessel Optimization Suite")
    st.markdown("### Comprehensive BOG and Economics Calculator")
    
    # Load data and configurations
    world_ports_data = load_world_ports()
    vessel_configs = get_vessel_configs()
    
    # Vessel selection
    vessel_type = st.selectbox("Select Vessel Type", list(vessel_configs.keys()))
    vessel_config = vessel_configs[vessel_type]
    
    # Display vessel specifications
    with st.expander("Vessel Specifications"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"Tank Capacity: {vessel_config['tank_capacity']} m³")
            st.write(f"Base BOG Rate: {vessel_config['base_bog_rate']}%")
            st.write(f"Engine Efficiency: {vessel_config['engine_efficiency']*100}%")
        with col2:
            st.write(f"Min Heel: {vessel_config['min_heel']} m³")
            st.write(f"Max Heel: {vessel_config['max_heel']} m³")
            st.write(f"Reliq Capacity: {vessel_config['reliq_capacity']} ton/hour")
    
    st.markdown("---")
    
    # Create voyage sections
    laden_data = create_voyage_section("Laden", world_ports_data, vessel_config)
    st.markdown("---")
    ballast_data = create_voyage_section("Ballast", world_ports_data, vessel_config, True)
    
    # Map visualization
    st.markdown("---")
    st.subheader("Route Visualization")
    
    laden_ports = [laden_data['voyage_from'], laden_data['voyage_to']]
    ballast_ports = [ballast_data['voyage_from'], ballast_data['voyage_to']]
    
    if all(laden_ports + ballast_ports):
        route_map = plot_combined_route(laden_ports, ballast_ports, world_ports_data)
        st_folium(route_map, width=800, height=500)
        
        # Display total voyage statistics
        if (laden_data['daily_data'] is not None and 
            ballast_data['daily_data'] is not None and 
            laden_data['economics'] is not None and 
            ballast_data['economics'] is not None):
            
            st.markdown("### Total Voyage Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_distance = float(laden_data['distance'] + ballast_data['distance'])
                st.metric("Total Distance", f"{total_distance:,.0f} NM")
            
            with col2:
                total_bog = (laden_data['economics']['total_bog_generated'] + 
                           ballast_data['economics']['total_bog_generated'])
                st.metric("Total BOG Generated", f"{total_bog:,.1f} m³")
            
            with col3:
                total_benefit = (laden_data['economics']['net_benefit'] + 
                               ballast_data['economics']['net_benefit'])
                st.metric("Total Voyage Benefit", f"${total_benefit:,.2f}")
            
            # Add downloadable report
            if st.button("Generate Voyage Report"):
                report_data = {
                    'Voyage Summary': {
                        'Total Distance (NM)': f"{total_distance:,.0f}",
                        'Total BOG Generated (m³)': f"{total_bog:,.1f}",
                        'Total Economic Benefit ($)': f"{total_benefit:,.2f}"
                    },
                    'Laden Voyage': {
                        'From': laden_data['voyage_from'],
                        'To': laden_data['voyage_to'],
                        'Distance (NM)': f"{laden_data['distance']:,.0f}",
                        'BOG Generated (m³)': f"{laden_data['economics']['total_bog_generated']:,.1f}",
                        'Economic Benefit ($)': f"{laden_data['economics']['net_benefit']:,.2f}"
                    },
                    'Ballast Voyage': {
                        'From': ballast_data['voyage_from'],
                        'To': ballast_data['voyage_to'],
                        'Distance (NM)': f"{ballast_data['distance']:,.0f}",
                        'BOG Generated (m³)': f"{ballast_data['economics']['total_bog_generated']:,.1f}",
                        'Economic Benefit ($)': f"{ballast_data['economics']['net_benefit']:,.2f}"
                    }
                }
                
                report_df = pd.DataFrame.from_dict(report_data, orient='index')
                st.download_button(
                    label="Download Report",
                    data=report_df.to_csv().encode('utf-8'),
                    file_name='voyage_report.csv',
                    mime='text/csv',
                )

def main():
    """Main application function"""
    st.set_page_config(
        page_title="LNG Vessel Optimization Suite",
        page_icon="🚢",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Add CSS for better styling
    st.markdown("""
        <style>
        .main {
            padding: 0rem 1rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 1rem;
            background-color: #f0f2f6;
        }
        .stTabs [aria-selected="true"] {
            background-color: #e0e2e6;
        }
        .stMetric {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Create sidebar for navigation
    st.sidebar.title("Navigation")
    calculator_choice = st.sidebar.radio(
        "Select Calculator",
        options=["BOG Calculator", "Heel Calculator"]
    )

    if calculator_choice == "BOG Calculator":
        show_bog_calculator()
    else:
        st.title("Heel Calculator")
        st.write("Under development...")

if __name__ == "__main__":
    main()
