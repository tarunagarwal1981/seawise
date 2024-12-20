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

# Enhanced vessel configurations with detailed technical specifications
def get_vessel_configs():
    """Get comprehensive vessel configuration data"""
    return {
        "MEGI": {
            "tank_capacity": 174000.0,
            "min_heel": 1500.0,
            "max_heel": 3000.0,
            "base_bog_rate": 0.14,  # 0.14% per day
            "reliq_capacity": 3.0,   # tons per hour
            "engine_efficiency": 0.78,  # 78% efficiency
            "daily_consumption": 100.0,  # tons per day
            "power_output": {
                "calm": 27.0,  # MW
                "adverse": 29.0  # MW
            },
            "reliq_power": {
                "min": 3.0,  # MW
                "max": 5.8   # MW
            },
            "emissions_reduction": 0.22,  # 22% lower than conventional
            "reliq_efficiency": 0.90,  # 90% BOG processing
            "power_consumption": 0.75  # kWh/kg BOG
        },
        "DFDE": {
            "tank_capacity": 180000.0,
            "min_heel": 1600.0,
            "max_heel": 3200.0,
            "base_bog_rate": 0.15,
            "reliq_capacity": 2.8,
            "engine_efficiency": 0.47,  # 47% thermal efficiency
            "daily_consumption": 130.0,  # tons per day
            "power_output": {
                "max": 40.0,  # MW at peak
                "nbog_laden": 20.0,  # MW from NBOG
                "nbog_ballast": 11.0  # MW from NBOG
            },
            "bog_rates": {
                "laden": 0.15,  # % per day
                "ballast": 0.06  # % per day
            }
        }
    }

# Enhanced BOG Calculation Functions
def calculate_enhanced_bog_rate(
    base_rate: float,
    tank_pressure: float,
    tank_level: float,
    ambient_temp: float,
    wave_height: float,
    solar_radiation: str,
    vessel_type: str,
    is_ballast: bool
) -> float:
    """Calculate BOG rate with all environmental and vessel-specific factors"""
    vessel_configs = get_vessel_configs()
    config = vessel_configs[vessel_type]
    
    # Base BOG adjustments based on vessel type and voyage type
    if vessel_type == "DFDE" and is_ballast:
        base_rate = config['bog_rates']['ballast']
    elif vessel_type == "DFDE":
        base_rate = config['bog_rates']['laden']
    
    # Environmental factors
    pressure_factor = 1.0 + ((tank_pressure - 1013.0) / 1013.0) * 0.1
    level_factor = 1.0 + (1.0 - tank_level/100.0) * 0.05
    temp_factor = 1.0 + (ambient_temp - 19.5) / 100.0
    wave_factor = 1.0 + wave_height * 0.02
    solar_factors = {'Low': 1.0, 'Medium': 1.02, 'High': 1.05}
    
    total_factor = (pressure_factor * level_factor * temp_factor * 
                   wave_factor * solar_factors[solar_radiation])
    
    return float(base_rate * total_factor)

def calculate_power_requirements(
    vessel_type: str,
    bog_generated: float,
    reliq_capacity: float,
    ambient_temp: float,
    wave_height: float
) -> dict:
    """Calculate power requirements for different systems"""
    vessel_configs = get_vessel_configs()
    config = vessel_configs[vessel_type]
    
    # Base power requirements - handle different vessel types
    if vessel_type == "MEGI":
        base_power = config['power_output']['calm']
        if wave_height > 3.0:
            base_power = config['power_output']['adverse']
    else:  # DFDE
        base_power = config['power_output']['nbog_laden']
        if wave_height > 3.0:
            base_power = config['power_output']['max']
    
    # Reliquefaction power - only for MEGI vessels
    if vessel_type == "MEGI" and 'reliq_power' in config:
        reliq_power = min(
            config['reliq_power']['min'] + 
            (bog_generated / reliq_capacity) * 
            (config['reliq_power']['max'] - config['reliq_power']['min']),
            config['reliq_power']['max']
        )
    else:
        reliq_power = 0.0
    
    # Engine power for BOG consumption
    engine_power = (bog_generated * config['engine_efficiency'] * 
                   (1.0 + (ambient_temp - 19.5) / 100.0))
    
    return {
        'base_power': float(base_power),
        'reliq_power': float(reliq_power),
        'engine_power': float(engine_power),
        'total_power': float(base_power + reliq_power + engine_power)
    }

def calculate_economic_metrics(
    vessel_type: str,
    power_requirements: dict,
    bog_generated: float,
    bog_reliquefied: float,
    lng_price: float,
    bunker_price: float,
    electricity_cost: float,
    voyage_days: float
) -> dict:
    """Calculate comprehensive economic metrics"""
    vessel_configs = get_vessel_configs()
    config = vessel_configs[vessel_type]
    
    # Daily costs
    reliq_power_cost = (power_requirements['reliq_power'] * 24 * 
                       electricity_cost * voyage_days)
    
    # LNG value
    lng_saved = bog_reliquefied * lng_price
    
    # Fuel savings
    fuel_savings = ((config['daily_consumption'] - 
                    power_requirements['engine_power']) * 
                   bunker_price * voyage_days)
    
    # Emissions reduction value (assuming carbon credit price)
    # Default emissions reduction for DFDE if not specified
    emissions_factor = config.get('emissions_reduction', 0.10)  # 10% default for DFDE
    emissions_reduction = (emissions_factor * 
                         config['daily_consumption'] * 
                         voyage_days * 30.0)  # $30 per ton CO2
    
    return {
        'reliq_cost': float(reliq_power_cost),
        'lng_value': float(lng_saved),
        'fuel_savings': float(fuel_savings),
        'emissions_value': float(emissions_reduction),
        'net_benefit': float(lng_saved + fuel_savings - 
                           reliq_power_cost + emissions_reduction)
    }
# Visualization Functions
def create_sankey_diagram(bog_data: dict) -> go.Figure:
    """Create Sankey diagram for BOG flow visualization"""
    labels = [
        "Generated BOG", "Reliquefaction", "Engine Consumption", 
        "GCU", "Liquid LNG", "Power Generation"
    ]
    
    source = [0, 0, 0, 1, 2]
    target = [1, 2, 3, 4, 5]
    value = [
        bog_data['bog_reliquefied'],
        bog_data['bog_consumed'],
        bog_data['bog_to_gcu'],
        bog_data['bog_reliquefied'],
        bog_data['bog_consumed']
    ]
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=labels,
            color=["blue", "green", "red", "yellow", "cyan", "orange"]
        ),
        link=dict(
            source=source,
            target=target,
            value=value
        )
    )])
    
    fig.update_layout(title_text="BOG Flow Distribution", font_size=12)
    return fig

def create_power_distribution_chart(power_data: dict) -> go.Figure:
    """Create pie chart for power distribution"""
    labels = ["Base Power", "Reliquefaction", "Engine Power"]
    values = [
        power_data['base_power'],
        power_data['reliq_power'],
        power_data['engine_power']
    ]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.3
    )])
    
    fig.update_layout(title_text="Power Distribution (MW)")
    return fig

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

def plot_daily_tracking_enhanced(daily_data: pd.DataFrame) -> go.Figure:
    """Create enhanced interactive plot for daily tracking"""
    fig = go.Figure()
    
    # Add traces with improved styling
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['remaining_volume'],
        name='Remaining Volume',
        line=dict(color='blue', width=2),
        fill='tonexty'
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['bog_generated'],
        name='BOG Generated',
        line=dict(color='red', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['bog_consumed'],
        name='BOG Consumed',
        line=dict(color='green', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['bog_reliquefied'],
        name='BOG Reliquefied',
        line=dict(color='purple', width=2)
    ))
    
    fig.update_layout(
        title='Daily BOG Tracking',
        xaxis_title='Days',
        yaxis_title='Volume (m³)',
        hovermode='x unified',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    
    return fig

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

def create_voyage_section_enhanced(
    leg_type: str, 
    world_ports_data: pd.DataFrame,
    vessel_config: dict, 
    is_ballast: bool = False
) -> dict:
    """
    Enhanced voyage section with comprehensive calculations
    Returns a dictionary containing all voyage data and calculations
    """
    # Initialize return data structure
    return_data = {
        'voyage_from': '',
        'voyage_to': '',
        'distance': 0.0,
        'voyage_days': 0.0,
        'initial_cargo': 0.0,
        'bog_rate': 0.0,
        'economics': None,
        'power_reqs': None,
        'bog_data': None,
        'total_bog_generated': 0.0
    }

    st.subheader(f"{leg_type} Leg Details")
    
    # Create tabs for organization
    tabs = st.tabs([
        "Cargo & Route",
        "Environmental",
        "BOG Management",
        "Power & Efficiency",
        "Economics",
        "Results"
    ])

    # Cargo & Route Tab
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        
        # Cargo Volume Input
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
            return_data['initial_cargo'] = initial_cargo

        # Port Selection
        with col2:
            voyage_from = st.text_input(
                "From Port", 
                key=f"{leg_type}_from"
            )
            return_data['voyage_from'] = voyage_from
        
        with col3:
            voyage_to = st.text_input(
                "To Port", 
                key=f"{leg_type}_to"
            )
            return_data['voyage_to'] = voyage_to

        # Calculate Distance and Days
        if voyage_from and voyage_to:
            distance = route_distance(voyage_from, voyage_to, world_ports_data)
            return_data['distance'] = distance
            
            speed = st.number_input(
                "Speed (knots)",
                min_value=1.0,
                max_value=25.0,
                value=15.0,
                step=0.1,
                key=f"{leg_type}_speed"
            )
            
            voyage_days = float(distance) / (float(speed) * 24.0) if speed > 0 else 0.0
            return_data['voyage_days'] = voyage_days
            st.metric("Estimated Voyage Days", f"{voyage_days:.1f}")

    # Environmental Tab
    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            ambient_temp = st.number_input(
                "Ambient Temperature (°C)",
                min_value=-20.0,
                max_value=45.0,
                value=19.5,
                step=0.5,
                key=f"{leg_type}_temp"
            )
            
            wave_height = st.number_input(
                "Wave Height (m)",
                min_value=0.0,
                max_value=10.0,
                value=1.0,
                step=0.1,
                key=f"{leg_type}_waves"
            )
        
        with col2:
            tank_pressure = st.number_input(
                "Tank Pressure (mbar)",
                min_value=1000.0,
                max_value=1300.0,
                value=1013.0,
                step=1.0,
                key=f"{leg_type}_pressure"
            )
            
            solar_radiation = st.selectbox(
                "Solar Radiation",
                options=['Low', 'Medium', 'High'],
                key=f"{leg_type}_solar"
            )

    # BOG Management Tab
    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            reliq_capacity = st.number_input(
                "Reliquefaction Capacity (tons/hour)",
                min_value=0.0,
                max_value=float(vessel_config['reliq_capacity']),
                value=float(vessel_config['reliq_capacity']),
                step=0.1,
                key=f"{leg_type}_reliq_cap"
            )
        
        with col2:
            engine_consumption = st.number_input(
                "Engine Gas Consumption (m³/day)",
                min_value=0.0,
                max_value=float(vessel_config['daily_consumption']),
                value=float(vessel_config['daily_consumption'] * 0.8),
                step=1.0,
                key=f"{leg_type}_consumption"
            )

    # Perform calculations if we have valid voyage days
    if voyage_days > 0:
        # Calculate BOG rate
        bog_rate = calculate_enhanced_bog_rate(
            vessel_config['base_bog_rate'],
            tank_pressure,
            100.0,  # Initial tank level
            ambient_temp,
            wave_height,
            solar_radiation,
            vessel_type="MEGI" if 'MEGI' in vessel_config else "DFDE",
            is_ballast=is_ballast
        )
        return_data['bog_rate'] = bog_rate

        # Calculate daily BOG generation
        daily_bog = initial_cargo * bog_rate / 100.0
        return_data['total_bog_generated'] = daily_bog * voyage_days

        # Calculate power requirements
        power_reqs = calculate_power_requirements(
            vessel_type="MEGI" if 'MEGI' in vessel_config else "DFDE",
            bog_generated=daily_bog,
            reliq_capacity=reliq_capacity,
            ambient_temp=ambient_temp,
            wave_height=wave_height
        )
        return_data['power_reqs'] = power_reqs

        # Calculate BOG distribution
        bog_data = {
            'bog_reliquefied': min(daily_bog, reliq_capacity * 24),
            'bog_consumed': min(daily_bog, engine_consumption),
            'bog_to_gcu': max(0, daily_bog - reliq_capacity * 24 - engine_consumption)
        }
        return_data['bog_data'] = bog_data

        # Calculate economics if prices are provided
        if 'Economics' in tabs:
            with tabs[4]:
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

                economics = calculate_economic_metrics(
                    vessel_type="MEGI" if 'MEGI' in vessel_config else "DFDE",
                    power_requirements=power_reqs,
                    bog_generated=daily_bog,
                    bog_reliquefied=bog_data['bog_reliquefied'],
                    lng_price=lng_price,
                    bunker_price=bunker_price,
                    electricity_cost=electricity_cost,
                    voyage_days=voyage_days
                )
                return_data['economics'] = economics

        # Display Results
        with tabs[5]:
            st.write("### Performance Metrics")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("BOG Rate (%/day)", f"{bog_rate:.3f}")
                st.metric("Total BOG Generated (m³)", f"{return_data['total_bog_generated']:.1f}")
            
            with col2:
                st.metric("Power Consumption (MW)", f"{power_reqs['total_power']:.1f}")
                st.metric("Reliquefaction Power (MW)", f"{power_reqs['reliq_power']:.1f}")
            
            if return_data.get('economics'):
                with col3:
                    st.metric("Net Benefit ($)", f"{return_data['economics']['net_benefit']:,.2f}")
                    st.metric("Emissions Value ($)", f"{return_data['economics']['emissions_value']:,.2f}")
            
            # Visualizations
            if return_data.get('bog_data'):
                st.write("### BOG Flow Distribution")
                st.plotly_chart(create_sankey_diagram(return_data['bog_data']), use_container_width=True)
                st.plotly_chart(create_power_distribution_chart(power_reqs), use_container_width=True)

    return return_data
    

def show_bog_calculator():
    """Main function to show enhanced BOG calculator"""
    st.title("LNG Vessel Optimization Suite")
    
    # Add introductory information
    with st.expander("About This Calculator"):
        st.markdown("""
        ### Comprehensive BOG and Economics Calculator
        This calculator provides detailed analysis of:
        - BOG generation and management
        - Power consumption optimization
        - Economic impact assessment
        - Environmental considerations
        
        Features:
        - Supports both MEGI and DFDE vessel types
        - Real-time BOG calculations
        - Economic analysis with multiple factors
        - Visualizations of BOG flow and power distribution
        """)
    
    try:
        # Load data and configurations
        world_ports_data = load_world_ports()
        vessel_configs = get_vessel_configs()
        
        # Vessel Configuration Section
        st.sidebar.title("Vessel Configuration")
        vessel_type = st.sidebar.selectbox(
            "Select Vessel Type",
            options=list(vessel_configs.keys())
        )
        vessel_config = vessel_configs[vessel_type]
        
        # Display vessel specifications
        with st.expander("Vessel Technical Specifications"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write("#### Capacity & Efficiency")
                st.write(f"Tank Capacity: {vessel_config['tank_capacity']:,} m³")
                st.write(f"Base BOG Rate: {vessel_config['base_bog_rate']}%")
                st.write(f"Engine Efficiency: {vessel_config['engine_efficiency']*100}%")
            
            with col2:
                st.write("#### Consumption & Power")
                st.write(f"Daily Consumption: {vessel_config['daily_consumption']:,} tons")
                st.write(f"Reliq Capacity: {vessel_config['reliq_capacity']} tons/hour")
                if 'emissions_reduction' in vessel_config:
                    st.write(f"Emissions Reduction: {vessel_config['emissions_reduction']*100}%")
            
            with col3:
                st.write("#### Operating Parameters")
                st.write(f"Min Heel: {vessel_config['min_heel']:,} m³")
                st.write(f"Max Heel: {vessel_config['max_heel']:,} m³")
                if 'power_output' in vessel_config:
                    if vessel_type == "MEGI":
                        st.write(f"Base Power: {vessel_config['power_output']['calm']} MW")
                    else:
                        st.write(f"Max Power: {vessel_config['power_output'].get('max', 40)} MW")
        
        st.markdown("---")
        
        # Create voyage sections
        laden_data = create_voyage_section_enhanced("Laden", world_ports_data, vessel_config)
        st.markdown("---")
        ballast_data = create_voyage_section_enhanced("Ballast", world_ports_data, vessel_config, True)
        
        # Map and Summary section
        if (laden_data.get('voyage_from') and laden_data.get('voyage_to') and 
            ballast_data.get('voyage_from') and ballast_data.get('voyage_to')):
            st.markdown("---")
            st.subheader("Route Visualization and Voyage Summary")
            
            # Route visualization
            laden_ports = [laden_data['voyage_from'], laden_data['voyage_to']]
            ballast_ports = [ballast_data['voyage_from'], ballast_data['voyage_to']]
            
            route_map = plot_combined_route(laden_ports, ballast_ports, world_ports_data)
            st_folium(route_map, width=800, height=500)
            
            # Overall voyage statistics
            if laden_data.get('economics') and ballast_data.get('economics'):
                st.markdown("### Total Voyage Analysis")
                
                col1, col2, col3, col4 = st.columns(4)
                
                # Distance metrics
                total_distance = laden_data['distance'] + ballast_data['distance']
                with col1:
                    st.metric(
                        "Total Distance", 
                        f"{total_distance:,.0f} NM",
                        help="Combined distance for laden and ballast voyages"
                    )
                
                # Economic metrics
                total_benefit = (laden_data['economics']['net_benefit'] + 
                               ballast_data['economics']['net_benefit'])
                with col2:
                    st.metric(
                        "Total Economic Benefit", 
                        f"${total_benefit:,.2f}",
                        help="Combined economic benefits including fuel savings and LNG value"
                    )
                
                # Environmental metrics
                total_emissions_value = (laden_data['economics']['emissions_value'] + 
                                       ballast_data['economics']['emissions_value'])
                with col3:
                    st.metric(
                        "Environmental Value", 
                        f"${total_emissions_value:,.2f}",
                        help="Value of emissions reduction based on carbon credits"
                    )
                
                # Total value metrics
                total_savings = total_benefit + total_emissions_value
                with col4:
                    st.metric(
                        "Total Value Generated", 
                        f"${total_savings:,.2f}",
                        help="Combined economic and environmental benefits"
                    )
                
                # Additional summary metrics
                st.markdown("### Detailed Analysis")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("#### BOG Management")
                    total_bog = (laden_data['total_bog_generated'] + 
                               ballast_data['total_bog_generated'])
                    st.metric("Total BOG Generated", f"{total_bog:,.1f} m³")
                    
                    if laden_data.get('bog_data') and ballast_data.get('bog_data'):
                        total_reliquefied = (laden_data['bog_data']['bog_reliquefied'] + 
                                           ballast_data['bog_data']['bog_reliquefied'])
                        st.metric("Total BOG Reliquefied", f"{total_reliquefied:,.1f} m³")
                
                with col2:
                    st.write("#### Power Consumption")
                    if laden_data.get('power_reqs') and ballast_data.get('power_reqs'):
                        avg_power = (laden_data['power_reqs']['total_power'] + 
                                   ballast_data['power_reqs']['total_power']) / 2
                        st.metric("Average Power Consumption", f"{avg_power:,.1f} MW")
                
                # Generate downloadable report
                if st.button("Generate Voyage Report"):
                    report_data = create_voyage_report(
                        laden_data, ballast_data, 
                        total_distance, total_benefit, 
                        total_emissions_value, total_savings
                    )
                    st.download_button(
                        label="Download Detailed Report",
                        data=report_data.to_csv().encode('utf-8'),
                        file_name='voyage_optimization_report.csv',
                        mime='text/csv',
                    )
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.info("Please check your inputs and try again.")

def create_voyage_report(laden_data, ballast_data, total_distance, 
                        total_benefit, total_emissions_value, total_savings):
    """Create a comprehensive voyage report"""
    report_data = {
        'Voyage Summary': {
            'Total Distance (NM)': f"{total_distance:,.0f}",
            'Total Economic Benefit ($)': f"{total_benefit:,.2f}",
            'Environmental Value ($)': f"{total_emissions_value:,.2f}",
            'Total Value Generated ($)': f"{total_savings:,.2f}"
        },
        'Laden Voyage': {
            'From': laden_data['voyage_from'],
            'To': laden_data['voyage_to'],
            'Distance (NM)': f"{laden_data['distance']:,.0f}",
            'BOG Rate (%/day)': f"{laden_data.get('bog_rate', 0):,.3f}",
            'Economic Benefit ($)': f"{laden_data['economics']['net_benefit']:,.2f}",
            'Environmental Value ($)': f"{laden_data['economics']['emissions_value']:,.2f}"
        },
        'Ballast Voyage': {
            'From': ballast_data['voyage_from'],
            'To': ballast_data['voyage_to'],
            'Distance (NM)': f"{ballast_data['distance']:,.0f}",
            'BOG Rate (%/day)': f"{ballast_data.get('bog_rate', 0):,.3f}",
            'Economic Benefit ($)': f"{ballast_data['economics']['net_benefit']:,.2f}",
            'Environmental Value ($)': f"{ballast_data['economics']['emissions_value']:,.2f}"
        }
    }
    
    return pd.DataFrame.from_dict(report_data, orient='index')

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="LNG Vessel Optimization Suite",
        page_icon="🚢",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Add custom CSS
    st.markdown("""
        <style>
        .main {padding: 0rem 1rem;}
        .stTabs [data-baseweb="tab-list"] {gap: 2px;}
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
    
    show_bog_calculator()

if __name__ == "__main__":
    main()
   
