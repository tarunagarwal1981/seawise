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
from plotly.subplots import make_subplots

# Data Loading Functions
@st.cache_data
def load_world_ports():
    """Load and cache world ports data"""
    try:
        return pd.read_csv("UpdatedPub150.csv")
    except Exception as e:
        st.warning("Using default port data as port database could not be loaded.")
        # Provide comprehensive default data
        return pd.DataFrame({
            'Main Port Name': [
                'SINGAPORE', 'ROTTERDAM', 'FUJAIRAH', 'YOKOHAMA', 'BUSAN',
                'QATARGAS', 'SABINE PASS', 'ZEEBRUGGE', 'DALIAN', 'BARCELONA'
            ],
            'Latitude': [
                1.290270, 51.916667, 25.112225, 35.443708, 35.179554,
                25.900000, 29.732000, 51.333333, 38.921700, 41.345800
            ],
            'Longitude': [
                103.855836, 4.500000, 56.336096, 139.638026, 129.075642,
                51.516700, -93.860000, 3.200000, 121.638600, 2.183300
            ]
        })

@st.cache_data
def get_port_distances():
    """Load cached port distances"""
    try:
        return pd.read_csv("port_distances.csv")
    except Exception as e:
        st.warning("Port distance database not available. Using calculated distances.")
        return None

def world_port_index(port_to_match, world_ports_data):
    """Find best matching port from world ports data"""
    if not port_to_match:
        return None
    try:
        best_match = process.extractOne(port_to_match, world_ports_data['Main Port Name'])
        return world_ports_data[world_ports_data['Main Port Name'] == best_match[0]].iloc[0]
    except Exception as e:
        st.error(f"Error matching port: {str(e)}")
        return None

def route_distance(origin, destination, world_ports_data):
    """Calculate route distance between two ports"""
    try:
        # Check port distance database first
        port_distances = get_port_distances()
        if port_distances is not None:
            distance = port_distances.get((origin, destination))
            if distance is not None:
                return float(distance)

        # Calculate using searoute if not found in database
        origin_port = world_port_index(origin, world_ports_data)
        destination_port = world_port_index(destination, world_ports_data)
        
        if origin_port is None or destination_port is None:
            return 0.0

        origin_coords = [float(origin_port['Longitude']), float(origin_port['Latitude'])]
        destination_coords = [float(destination_port['Longitude']), float(destination_port['Latitude'])]
        
        try:
            sea_route = sr.searoute(origin_coords, destination_coords, units="naut")
            return float(sea_route['properties']['length'])
        except Exception as e:
            st.warning(f"Error calculating route: {str(e)}. Using great circle distance.")
            # Fallback to great circle distance
            return calculate_gc_distance(
                origin_port['Latitude'], origin_port['Longitude'],
                destination_port['Latitude'], destination_port['Longitude']
            )
    except Exception as e:
        st.error(f"Error calculating distance: {str(e)}")
        return 0.0

def calculate_gc_distance(lat1, lon1, lat2, lon2):
    """Calculate great circle distance between two points"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 3440.065  # Earth radius in nautical miles
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def calculate_heel_requirements(
    tank_capacity: float,
    voyage_days: float,
    daily_consumption: float,
    safety_factor: float = 1.2
) -> dict:
    """
    Calculate minimum and maximum heel requirements
    
    Parameters:
    - tank_capacity: Total tank capacity in m³
    - voyage_days: Duration of voyage in days
    - daily_consumption: Expected daily consumption in m³
    - safety_factor: Safety margin multiplier (default 1.2)
    
    Returns:
    - Dictionary with min_heel, max_heel, and recommended_heel
    """
    # Minimum heel for tank cooling (0.8% of tank capacity)
    min_cooling_heel = tank_capacity * 0.008
    
    # Minimum heel for voyage consumption
    min_consumption_heel = daily_consumption * voyage_days * safety_factor
    
    # Maximum heel (typically 2% of tank capacity)
    max_heel = tank_capacity * 0.02
    
    min_heel = max(min_cooling_heel, min_consumption_heel)
    
    return {
        'min_heel': min_heel,
        'max_heel': max_heel,
        'recommended_heel': (min_heel + max_heel) / 2
    }

def calculate_engine_efficiency(
    vessel_type: str,
    load_factor: float,
    ambient_temp: float,
    base_efficiency: float
) -> float:
    """
    Calculate actual engine efficiency based on operating conditions
    
    Parameters:
    - vessel_type: "MEGI" or "DFDE"
    - load_factor: Engine load as fraction (0.0 to 1.0)
    - ambient_temp: Ambient temperature in °C
    - base_efficiency: Base engine efficiency from vessel config
    
    Returns:
    - Actual efficiency as float
    """
    # Load factor adjustment (engines are less efficient at partial load)
    load_adjustment = 1.0 - (1.0 - load_factor) * 0.1
    
    # Temperature adjustment
    temp_adjustment = 1.0 - abs(ambient_temp - 25) / 100
    
    return base_efficiency * load_adjustment * temp_adjustment

def calculate_base_power(
    vessel_size: float,
    speed: float,
    wave_height: float,
    wind_speed: float = 15.0  # Default moderate wind
) -> float:
    """
    Calculate base power requirement
    
    Parameters:
    - vessel_size: Vessel capacity in m³
    - speed: Vessel speed in knots
    - wave_height: Wave height in meters
    - wind_speed: Wind speed in knots
    
    Returns:
    - Base power requirement in MW
    """
    # Basic power requirement (approximation)
    basic_power = (vessel_size / 1000) * (speed / 10) ** 3
    
    # Sea state adjustment
    sea_factor = 1.0 + (wave_height / 5.0) * 0.2
    
    # Wind adjustment
    wind_factor = 1.0 + (wind_speed / 20.0) * 0.1
    
    return basic_power * sea_factor * wind_factor

@st.cache_data
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
            "thermal_efficiency": 0.47, # 47% thermal efficiency
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
            "power_consumption": 0.75,  # kWh/kg BOG
            "specifications": {
                "propulsion": "ME-GI Engine",
                "reliquefaction": "Partial Reliquefaction",
                "fuel_type": "Dual Fuel"
            }
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
            "thermal_efficiency": 0.47,  # 47% thermal efficiency
            "bog_rates": {
                "laden": 0.15,  # % per day
                "ballast": 0.06  # % per day
            },
            "specifications": {
                "propulsion": "Dual Fuel Diesel Electric",
                "reliquefaction": "None",
                "fuel_type": "Dual Fuel"
            }
        }
    }

    
    # Calculate heel requirements for each vessel type
    for vessel_type, config in base_configs.items():
        heel_reqs = calculate_heel_requirements(
            tank_capacity=config['tank_capacity'],
            voyage_days=15.0,  # Typical voyage duration
            daily_consumption=config['daily_consumption']
        )
        config.update({
            "min_heel": heel_reqs['min_heel'],
            "max_heel": heel_reqs['max_heel'],
            "recommended_heel": heel_reqs['recommended_heel']
        })
        
        # Calculate power requirements
        if vessel_type == "MEGI":
            config["power_output"] = {
                "calm": calculate_base_power(config['tank_capacity'], 19.0, 1.0),
                "adverse": calculate_base_power(config['tank_capacity'], 19.0, 4.0)
            }
            config["reliq_power"] = {
                "min": 3.0,
                "max": 5.8
            }
        else:
            config["power_output"] = {
                "max": calculate_base_power(config['tank_capacity'], 19.0, 4.0),
                "nbog_laden": calculate_base_power(config['tank_capacity'], 19.0, 1.0) * 0.8,
                "nbog_ballast": calculate_base_power(config['tank_capacity'], 19.0, 1.0) * 0.5
            }
    
    return base_configs

def display_vessel_specs(vessel_config):
    """Display vessel specifications in an organized manner"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("#### Capacity Specifications")
        st.write(f"Tank Capacity: {vessel_config['tank_capacity']:,} m³")
        st.write(f"Base BOG Rate: {vessel_config['base_bog_rate']}%/day")
        st.write(f"Engine Efficiency: {vessel_config['engine_efficiency']*100:.1f}%")
        st.write(f"Thermal Efficiency: {vessel_config['thermal_efficiency']*100:.1f}%")
    
    with col2:
        st.write("#### Operating Parameters")
        st.write(f"Daily Consumption: {vessel_config['daily_consumption']:,} tons")
        st.write(f"Reliq Capacity: {vessel_config.get('reliq_capacity', 'N/A')} tons/hour")
        if 'emissions_reduction' in vessel_config:
            st.write(f"Emissions Reduction: {vessel_config['emissions_reduction']*100:.1f}%")
    
    with col3:
        st.write("#### Technical Specifications")
        st.write(f"Propulsion: {vessel_config['specifications']['propulsion']}")
        st.write(f"Reliquefaction: {vessel_config['specifications']['reliquefaction']}")
        st.write(f"Fuel Type: {vessel_config['specifications']['fuel_type']}")

def show_calculator_info():
    """Display calculator information"""
    st.markdown("""
    ### Advanced BOG and Vessel Performance Calculator
    
    This calculator provides comprehensive analysis for LNG vessel operations:
    
    * BOG Generation & Management
        - Real-time BOG rate calculations
        - Environmental factor adjustments
        - Tank pressure optimization
        
    * Power System Analysis
        - Engine efficiency calculations
        - Reliquefaction power requirements
        - Overall power consumption optimization
        
    * Economic Assessment
        - Voyage cost analysis
        - Fuel savings calculations
        - Environmental benefit valuation
        
    * Operational Optimization
        - Heel quantity optimization
        - Speed and consumption analysis
        - Weather impact considerations
        
    * Environmental Impact
        - Emissions reduction calculations
        - Carbon credit valuations
        - Environmental compliance metrics
    """)

def calculate_enhanced_bog_rate(
    base_rate: float,
    tank_pressure: float,
    tank_level: float,
    ambient_temp: float,
    wave_height: float,
    solar_radiation: str,
    vessel_type: str,
    is_ballast: bool,
    tank_age: float = 5.0  # Default tank age in years
) -> dict:
    """
    Calculate comprehensive BOG rate with all environmental and vessel-specific factors
    
    Returns detailed breakdown of all factors affecting BOG rate
    """
    vessel_configs = get_vessel_configs()
    config = vessel_configs[vessel_type]
    
    # Base BOG adjustments based on vessel type and voyage type
    if vessel_type == "DFDE" and is_ballast:
        base_rate = config['bog_rates']['ballast']
    elif vessel_type == "DFDE":
        base_rate = config['bog_rates']['laden']
    
    # Tank aging effect (0.5% increase per year)
    aging_factor = 1.0 + (tank_age * 0.005)
    
    # Environmental factors
    pressure_factor = 1.0 + ((tank_pressure - 1013.0) / 1013.0) * 0.1
    level_factor = 1.0 + (1.0 - tank_level/100.0) * 0.05
    temp_factor = 1.0 + (ambient_temp - 19.5) / 100.0
    
    # Enhanced wave effect calculation
    wave_factor = 1.0 + (wave_height ** 1.5) * 0.01  # Non-linear relationship
    
    # Enhanced solar radiation effect
    solar_factors = {
        'Low': 1.0,
        'Medium': 1.02,
        'High': 1.05
    }
    
    # Calculate total factor and final BOG rate
    total_factor = (pressure_factor * level_factor * temp_factor * 
                   wave_factor * solar_factors[solar_radiation] * aging_factor)
    
    final_bog_rate = float(base_rate * total_factor)
    
    return {
        'final_rate': final_bog_rate,
        'factors': {
            'base_rate': base_rate,
            'aging_factor': aging_factor,
            'pressure_factor': pressure_factor,
            'level_factor': level_factor,
            'temp_factor': temp_factor,
            'wave_factor': wave_factor,
            'solar_factor': solar_factors[solar_radiation]
        }
    }

def calculate_power_requirements(
    vessel_type: str,
    bog_generated: float,
    reliq_capacity: float,
    ambient_temp: float,
    wave_height: float,
    speed: float,
    wind_speed: float = 15.0
) -> dict:
    """
    Calculate comprehensive power requirements for all systems
    """
    vessel_configs = get_vessel_configs()
    config = vessel_configs[vessel_type]
    
    # Calculate base power using enhanced method
    base_power = calculate_base_power(
        vessel_size=config['tank_capacity'],
        speed=speed,
        wave_height=wave_height,
        wind_speed=wind_speed
    )
    
    # Calculate engine efficiency
    load_factor = 0.8  # Typical optimal load
    engine_eff = calculate_engine_efficiency(
        vessel_type=vessel_type,
        load_factor=load_factor,
        ambient_temp=ambient_temp,
        base_efficiency=config['engine_efficiency']  # Changed from base_efficiency
    )
    
    # Calculate reliquefaction power
    if vessel_type == "MEGI" and 'reliq_power' in config:
        reliq_power = min(
            config['reliq_power']['min'] + 
            (bog_generated / reliq_capacity) * 
            (config['reliq_power']['max'] - config['reliq_power']['min']),
            config['reliq_power']['max']
        )
        
        # Adjust for ambient temperature
        reliq_power *= (1.0 + (ambient_temp - 19.5) / 100.0)
    else:
        reliq_power = 0.0
    
    # Calculate engine power from BOG consumption
    engine_power = (bog_generated * engine_eff * 
                   (1.0 + (ambient_temp - 19.5) / 100.0))
    
    # Calculate auxiliary power requirements
    auxiliary_power = base_power * 0.1  # Approximately 10% of base power
    
    total_power = base_power + reliq_power + auxiliary_power
    
    return {
        'base_power': float(base_power),
        'reliq_power': float(reliq_power),
        'engine_power': float(engine_power),
        'auxiliary_power': float(auxiliary_power),
        'total_power': float(total_power),
        'efficiency': {
            'engine': float(engine_eff),
            'reliq': float(config.get('reliq_efficiency', 0.0))
        }
    }


def calculate_economic_metrics(
    vessel_type: str,
    power_requirements: dict,
    bog_generated: float,
    bog_reliquefied: float,
    lng_price: float,
    bunker_price: float,
    electricity_cost: float,
    voyage_days: float,
    carbon_price: float = 30.0
) -> dict:
    """
    Calculate comprehensive economic metrics including detailed breakdowns
    """
    vessel_configs = get_vessel_configs()
    config = vessel_configs[vessel_type]
    
    # Detailed power costs
    power_costs = {
        'reliq': power_requirements['reliq_power'] * 24 * electricity_cost * voyage_days,
        'auxiliary': power_requirements['auxiliary_power'] * 24 * electricity_cost * voyage_days
    }
    
    # LNG value calculations
    lng_metrics = {
        'saved': bog_reliquefied * lng_price,
        'lost': (bog_generated - bog_reliquefied) * lng_price
    }
    
    # Fuel savings calculations
    fuel_metrics = {
        'consumption_savings': (config['daily_consumption'] - 
                              power_requirements['engine_power']) * bunker_price * voyage_days,
        'efficiency_savings': power_requirements['efficiency']['engine'] * 
                            bunker_price * voyage_days
    }
    
    # Emissions calculations
    emissions_factor = config.get('emissions_reduction', 0.10)
    emissions_savings = (emissions_factor * config['daily_consumption'] * 
                        voyage_days * carbon_price)
    
    # Total calculations
    total_costs = sum(power_costs.values())
    total_savings = (lng_metrics['saved'] + sum(fuel_metrics.values()) + 
                    emissions_savings)
    
    return {
        'power_costs': power_costs,
        'lng_metrics': lng_metrics,
        'fuel_metrics': fuel_metrics,
        'emissions_value': float(emissions_savings),
        'total_costs': float(total_costs),
        'total_savings': float(total_savings),
        'net_benefit': float(total_savings - total_costs)
    }

def calculate_daily_bog_profile(
    initial_volume: float,
    voyage_days: float,
    vessel_type: str,
    ambient_temps: list,
    wave_heights: list,
    solar_radiation: str,
    tank_pressure: float,
    tank_age: float = 5.0
) -> pd.DataFrame:
    """
    Calculate detailed daily BOG profile with all factors
    """
    daily_data = []
    remaining_volume = initial_volume
    
    for day in range(int(voyage_days)):
        # Calculate tank level percentage
        tank_level = (remaining_volume / initial_volume) * 100.0
        
        # Get BOG rate for current conditions
        bog_calc = calculate_enhanced_bog_rate(
            base_rate=0.0,  # Will be set by function based on vessel type
            tank_pressure=tank_pressure,
            tank_level=tank_level,
            ambient_temp=ambient_temps[day],
            wave_height=wave_heights[day],
            solar_radiation=solar_radiation,
            vessel_type=vessel_type,
            is_ballast=initial_volume < initial_volume * 0.5,
            tank_age=tank_age
        )
        
        # Calculate daily BOG
        bog_volume = remaining_volume * (bog_calc['final_rate'] / 100.0)
        
        # Store daily data
        daily_data.append({
            'day': day,
            'remaining_volume': remaining_volume,
            'tank_level': tank_level,
            'bog_rate': bog_calc['final_rate'],
            'bog_volume': bog_volume,
            'temperature': ambient_temps[day],
            'wave_height': wave_heights[day],
            'pressure_factor': bog_calc['factors']['pressure_factor'],
            'level_factor': bog_calc['factors']['level_factor'],
            'temp_factor': bog_calc['factors']['temp_factor'],
            'wave_factor': bog_calc['factors']['wave_factor']
        })
        
        # Update remaining volume
        remaining_volume -= bog_volume
    
    return pd.DataFrame(daily_data)

def create_sankey_diagram(bog_data: dict, power_data: dict) -> go.Figure:
    """
    Create enhanced Sankey diagram showing BOG and power flow
    """
    # Define all nodes in the system
    labels = [
        "Generated BOG",          # 0
        "Reliquefaction",        # 1
        "Engine Consumption",     # 2
        "GCU",                   # 3
        "Liquid LNG",            # 4
        "Power Generation",      # 5
        "Base Power",            # 6
        "Auxiliary Power",       # 7
        "Total Power Output"     # 8
    ]
    
    # Define flow connections
    source = [0, 0, 0, 1, 2, 6, 7, 5]
    target = [1, 2, 3, 4, 5, 8, 8, 8]
    value = [
        bog_data['bog_reliquefied'],
        bog_data['bog_consumed'],
        bog_data['bog_to_gcu'],
        bog_data['bog_reliquefied'],
        bog_data['bog_consumed'],
        power_data['base_power'],
        power_data['auxiliary_power'],
        power_data['engine_power']
    ]
    
    # Color scheme
    node_colors = [
        "blue",    # Generated BOG
        "green",   # Reliquefaction
        "red",     # Engine Consumption
        "yellow",  # GCU
        "cyan",    # Liquid LNG
        "orange",  # Power Generation
        "purple",  # Base Power
        "brown",   # Auxiliary Power
        "gray"     # Total Power Output
    ]
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=labels,
            color=node_colors
        ),
        link=dict(
            source=source,
            target=target,
            value=value
        )
    )])
    
    fig.update_layout(
        title_text="BOG and Power Flow Distribution",
        font_size=12,
        height=600
    )
    
    return fig

def create_daily_profile_chart(daily_data: pd.DataFrame) -> go.Figure:
    """
    Create enhanced daily profile chart with multiple metrics
    """
    fig = go.Figure()
    
    # Add volume trace
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['remaining_volume'],
        name='Remaining Volume (m³)',
        line=dict(color='blue', width=2),
        fill='tonexty'
    ))
    
    # Add BOG rate trace
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['bog_rate'],
        name='BOG Rate (%/day)',
        line=dict(color='red', width=2),
        yaxis='y2'
    ))
    
    # Add temperature effect
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['temp_factor'],
        name='Temperature Effect',
        line=dict(color='orange', dash='dash'),
        yaxis='y3'
    ))
    
    # Layout with multiple y-axes
    fig.update_layout(
        title='Daily BOG Profile with Environmental Effects',
        xaxis=dict(title='Days'),
        yaxis=dict(
            title='Volume (m³)',
            titlefont=dict(color='blue'),
            tickfont=dict(color='blue')
        ),
        yaxis2=dict(
            title='BOG Rate (%/day)',
            titlefont=dict(color='red'),
            tickfont=dict(color='red'),
            overlaying='y',
            side='right'
        ),
        yaxis3=dict(
            title='Factor Magnitude',
            titlefont=dict(color='orange'),
            tickfont=dict(color='orange'),
            overlaying='y',
            side='right',
            position=0.85
        ),
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

def create_economic_summary_chart(economics: dict) -> go.Figure:
    """
    Create waterfall chart for economic analysis
    """
    measure = ["relative", "relative", "relative", "relative", "total"]
    
    fig = go.Figure(go.Waterfall(
        name="Economic Analysis",
        orientation="v",
        measure=measure,
        x=["LNG Saved", "Fuel Savings", "Emissions Value", "Power Costs", "Net Benefit"],
        y=[
            economics['lng_metrics']['saved'],
            economics['fuel_metrics']['consumption_savings'],
            economics['emissions_value'],
            -economics['total_costs'],
            economics['net_benefit']
        ],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "red"}},
        increasing={"marker": {"color": "green"}},
        totals={"marker": {"color": "blue"}}
    ))
    
    fig.update_layout(
        title="Economic Impact Breakdown",
        showlegend=False,
        height=500
    )
    
    return fig

def plot_vessel_efficiency_chart(
    vessel_type: str,
    power_data: dict,
    daily_data: pd.DataFrame
) -> go.Figure:
    """
    Create efficiency analysis chart using subplots
    """
    # Create figure with secondary y-axis
    fig = go.Figure()

    # Add power distribution as pie chart
    fig.add_trace(go.Pie(
        labels=["Base", "Reliquefaction", "Engine", "Auxiliary"],
        values=[
            power_data['base_power'],
            power_data['reliq_power'],
            power_data['engine_power'],
            power_data['auxiliary_power']
        ],
        name="Power Distribution",
        showlegend=True
    ))

    # Update layout
    fig.update_layout(
        title=f"{vessel_type} Vessel Efficiency Analysis",
        height=500,
        grid=dict(rows=1, columns=2),
        annotations=[
            dict(
                text="Power Distribution",
                showarrow=False,
                x=0.25,
                y=1.1
            )
        ]
    )

    # Optional: Add tank level trace to the right side
    if 'tank_level' in daily_data.columns:
        fig.add_trace(
            go.Scatter(
                x=daily_data['day'],
                y=daily_data['tank_level'],
                name="Tank Level (%)",
                yaxis="y2"
            )
        )
        
        # Update layout to accommodate second y-axis
        fig.update_layout(
            yaxis2=dict(
                title="Tank Level (%)",
                overlaying="y",
                side="right"
            ),
            xaxis=dict(
                domain=[0.6, 1.0]
            ),
            showlegend=True
        )

    return fig

def create_stacked_efficiency_chart(daily_data: pd.DataFrame) -> go.Figure:
    """
    Create stacked area chart for efficiency metrics
    """
    fig = go.Figure()
    
    # Add efficiency metrics
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['pressure_factor'],
        name='Pressure Effect',
        mode='lines',
        stackgroup='one',
        groupnorm='percent'
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['temp_factor'],
        name='Temperature Effect',
        mode='lines',
        stackgroup='one'
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['wave_factor'],
        name='Wave Effect',
        mode='lines',
        stackgroup='one'
    ))
    
    # Update layout
    fig.update_layout(
        title="Efficiency Factors Over Time",
        xaxis_title="Days",
        yaxis_title="Contribution (%)",
        hovermode='x unified',
        showlegend=True
    )
    
    return fig

def plot_combined_metrics(
    daily_data: pd.DataFrame,
    power_data: dict,
    economics: dict
) -> go.Figure:
    """
    Create comprehensive metrics visualization
    """
    fig = go.Figure()
    
    # Add BOG metrics
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=daily_data['bog_rate'],
        name='BOG Rate',
        line=dict(color='red')
    ))
    
    # Add power metrics
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=[power_data['total_power']] * len(daily_data),
        name='Power Consumption',
        line=dict(color='blue', dash='dash')
    ))
    
    # Add economic metrics
    cumulative_benefit = np.cumsum(
        [economics['net_benefit'] / len(daily_data)] * len(daily_data)
    )
    fig.add_trace(go.Scatter(
        x=daily_data['day'],
        y=cumulative_benefit,
        name='Cumulative Benefit',
        line=dict(color='green'),
        yaxis='y2'
    ))
    
    # Update layout
    fig.update_layout(
        title="Combined Performance Metrics",
        xaxis_title="Days",
        yaxis_title="BOG Rate (%) / Power (MW)",
        yaxis2=dict(
            title="Cumulative Benefit ($)",
            overlaying='y',
            side='right'
        ),
        hovermode='x unified',
        showlegend=True
    )
    
    return fig

def create_voyage_section_enhanced(
    leg_type: str, 
    world_ports_data: pd.DataFrame,
    vessel_config: dict, 
    is_ballast: bool = False
) -> dict:
    """Enhanced voyage section with comprehensive calculations"""
    # Initialize return data with default values
    return_data = {
        'voyage_from': '',
        'voyage_to': '',
        'distance': 0.0,
        'voyage_days': 0.0,
        'initial_cargo': 0.0,
        'bog_rate': 0.0,
        'power_reqs': None,
        'daily_profile': None,
        'economics': None,
        'heel_requirements': None
    }

    st.subheader(f"{leg_type} Leg Details")
    
    tabs = st.tabs([
        "Route & Cargo",
        "Environmental",
        "Technical",
        "Economics",
        "Analysis"
    ])

    # Route & Cargo Tab
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        with col1:
            # Calculate heel requirements
            if is_ballast:
                heel_reqs = calculate_heel_requirements(
                    tank_capacity=vessel_config['tank_capacity'],
                    voyage_days=15.0,  # Default estimate
                    daily_consumption=vessel_config['daily_consumption']
                )
                st.write("#### Recommended Heel Ranges")
                st.write(f"Minimum: {heel_reqs['min_heel']:,.0f} m³")
                st.write(f"Maximum: {heel_reqs['max_heel']:,.0f} m³")
                
                initial_cargo = st.number_input(
                    "Heel Quantity (m³)",
                    min_value=float(heel_reqs['min_heel']),
                    max_value=float(heel_reqs['max_heel']),
                    value=float(heel_reqs['recommended_heel']),
                    help="Recommended heel based on voyage duration and consumption"
                )
            else:
                initial_cargo = st.number_input(
                    "Initial Cargo Volume (m³)",
                    min_value=0.0,
                    max_value=float(vessel_config['tank_capacity']),
                    value=float(vessel_config['tank_capacity'] * 0.98),
                    help="Maximum cargo capacity adjusted for tank limits"
                )
        
        with col2:
            voyage_from = st.text_input("From Port", key=f"{leg_type}_from")
        with col3:
            voyage_to = st.text_input("To Port", key=f"{leg_type}_to")
        
        # Calculate distance and voyage details
        if voyage_from and voyage_to:
            distance = route_distance(voyage_from, voyage_to, world_ports_data)
            
            col1, col2 = st.columns(2)
            with col1:
                speed = st.number_input(
                    "Speed (knots)",
                    min_value=10.0,
                    max_value=21.0,
                    value=19.0,
                    step=0.1,
                    help="Optimal speed range for vessel type"
                )
            
            voyage_days = float(distance) / (float(speed) * 24.0) if speed > 0 else 0.0
            
            with col2:
                st.metric(
                    "Estimated Voyage Days",
                    f"{voyage_days:.1f}",
                    help="Based on distance and speed"
                )

            return_data.update({
                'voyage_from': voyage_from,
                'voyage_to': voyage_to,
                'distance': distance,
                'speed': speed,
                'voyage_days': voyage_days
            })

    # Environmental Tab
    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            ambient_temp = st.number_input(
                "Average Ambient Temperature (°C)",
                min_value=-20.0,
                max_value=45.0,
                value=19.5,
                help="Affects BOG generation and system efficiency"
            )
            
            temp_variation = st.number_input(
                "Temperature Variation (±°C)",
                min_value=0.0,
                max_value=10.0,
                value=2.0,
                help="Daily temperature fluctuation range"
            )
        
        with col2:
            wave_height = st.number_input(
                "Significant Wave Height (m)",
                min_value=0.0,
                max_value=10.0,
                value=1.0,
                help="Affects sloshing and power requirements"
            )
            
            wind_speed = st.number_input(
                "Average Wind Speed (knots)",
                min_value=0.0,
                max_value=50.0,
                value=15.0,
                help="Affects power requirements"
            )

        tank_pressure = st.number_input(
            "Tank Pressure (mbar)",
            min_value=1000.0,
            max_value=1300.0,
            value=1013.0,
            help="Operating pressure affects BOG rate"
        )
        
        solar_radiation = st.selectbox(
            "Solar Radiation Level",
            options=['Low', 'Medium', 'High'],
            help="Affects heat ingress and BOG generation"
        )

        return_data.update({
            'environmental': {
                'ambient_temp': ambient_temp,
                'temp_variation': temp_variation,
                'wave_height': wave_height,
                'wind_speed': wind_speed,
                'tank_pressure': tank_pressure,
                'solar_radiation': solar_radiation
            }
        })

    # Continue with Technical tab
    with tabs[2]:
        st.write("#### Engine & Power Systems")
        
        col1, col2 = st.columns(2)
        with col1:
            engine_load = st.slider(
                "Engine Load Factor",
                min_value=0.5,
                max_value=1.0,
                value=0.8,
                help="Affects engine efficiency"
            )
            
            if 'MEGI' in vessel_config:
                reliq_capacity = st.number_input(
                    "Reliquefaction Capacity (tons/hour)",
                    min_value=0.0,
                    max_value=float(vessel_config['reliq_capacity']),
                    value=float(vessel_config['reliq_capacity']),
                    help="Maximum reliquefaction capacity"
                )
        
        with col2:
            tank_age = st.number_input(
                "Tank Age (years)",
                min_value=0.0,
                max_value=20.0,
                value=5.0,
                help="Affects insulation efficiency"
            )

        return_data.update({
            'technical': {
                'engine_load': engine_load,
                'tank_age': tank_age,
                'reliq_capacity': reliq_capacity if 'MEGI' in vessel_config else 0.0
            }
        })


    # Economics Tab
    with tabs[3]:
        if voyage_days > 0:
            col1, col2 = st.columns(2)
            with col1:
                st.write("#### Fuel & Energy Prices")
                lng_price = st.number_input(
                    "LNG Price ($/mmBTU)",
                    min_value=0.0,
                    max_value=50.0,
                    value=15.0,
                    help="Current LNG market price"
                )
                
                bunker_price = st.number_input(
                    "Bunker Price ($/mt)",
                    min_value=0.0,
                    max_value=2000.0,
                    value=800.0,
                    help="Alternative fuel price"
                )
            
            with col2:
                st.write("#### Operating Costs")
                electricity_cost = st.number_input(
                    "Electricity Cost ($/kWh)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.15,
                    help="Cost of power generation"
                )
                
                carbon_price = st.number_input(
                    "Carbon Price ($/ton CO2)",
                    min_value=0.0,
                    max_value=200.0,
                    value=30.0,
                    help="Carbon credit market price"
                )

            return_data.update({
                'economics_input': {
                    'lng_price': lng_price,
                    'bunker_price': bunker_price,
                    'electricity_cost': electricity_cost,
                    'carbon_price': carbon_price
                }
            })

    # Analysis Tab
    with tabs[4]:
        if voyage_days > 0:
            # Generate temperature and wave profiles
            temps = np.random.normal(
                return_data['environmental']['ambient_temp'],
                return_data['environmental']['temp_variation'],
                int(voyage_days)
            )
            waves = np.random.normal(
                return_data['environmental']['wave_height'],
                0.5,
                int(voyage_days)
            )
            
            # Calculate daily BOG profile
            daily_profile = calculate_daily_bog_profile(
                initial_volume=initial_cargo,
                voyage_days=voyage_days,
                vessel_type="MEGI" if 'MEGI' in vessel_config else "DFDE",
                ambient_temps=temps,
                wave_heights=waves,
                solar_radiation=return_data['environmental']['solar_radiation'],
                tank_pressure=return_data['environmental']['tank_pressure'],
                tank_age=return_data['technical']['tank_age']
            )
            
            # Calculate power requirements
            power_reqs = calculate_power_requirements(
                vessel_type="MEGI" if 'MEGI' in vessel_config else "DFDE",
                bog_generated=daily_profile['bog_volume'].mean(),
                reliq_capacity=return_data['technical'].get('reliq_capacity', 0.0),
                ambient_temp=return_data['environmental']['ambient_temp'],
                wave_height=return_data['environmental']['wave_height'],
                speed=return_data['speed'],
                wind_speed=return_data['environmental']['wind_speed']
            )
            
            # Calculate economics
            economics = calculate_economic_metrics(
                vessel_type="MEGI" if 'MEGI' in vessel_config else "DFDE",
                power_requirements=power_reqs,
                bog_generated=daily_profile['bog_volume'].sum(),
                bog_reliquefied=daily_profile['bog_volume'].sum() * 
                               vessel_config.get('reliq_efficiency', 0.0),
                lng_price=return_data['economics_input']['lng_price'],
                bunker_price=return_data['economics_input']['bunker_price'],
                electricity_cost=return_data['economics_input']['electricity_cost'],
                voyage_days=voyage_days,
                carbon_price=return_data['economics_input']['carbon_price']
            )
            
            # Store calculated results
            return_data.update({
                'daily_profile': daily_profile,
                'power_reqs': power_reqs,
                'economics': economics
            })
            
            # Display Results
            st.write("### Performance Analysis")
            
            # Key Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Average BOG Rate",
                    f"{daily_profile['bog_rate'].mean():.3f}%/day",
                    help="Average daily boil-off rate"
                )
                st.metric(
                    "Total BOG Generated",
                    f"{daily_profile['bog_volume'].sum():.1f} m³",
                    help="Total boil-off gas volume"
                )
            
            with col2:
                st.metric(
                    "Power Consumption",
                    f"{power_reqs['total_power']:.1f} MW",
                    help="Total power requirement"
                )
                if 'MEGI' in vessel_config:
                    st.metric(
                        "Reliquefaction Power",
                        f"{power_reqs['reliq_power']:.1f} MW",
                        help="Power used for reliquefaction"
                    )
            
            with col3:
                st.metric(
                    "Net Economic Benefit",
                    f"${economics['net_benefit']:,.2f}",
                    help="Total value generated"
                )
                st.metric(
                    "Environmental Value",
                    f"${economics['emissions_value']:,.2f}",
                    help="Value of emissions reduction"
                )
            
            # Visualizations
            st.write("### Detailed Analysis")
            
            # Daily Profile Chart
            st.plotly_chart(
                create_daily_profile_chart(daily_profile),
                use_container_width=True
            )
            
            # BOG Flow and Power Distribution
            st.plotly_chart(
                create_sankey_diagram(
                    bog_data={
                        'bog_reliquefied': daily_profile['bog_volume'].sum() * 
                                         vessel_config.get('reliq_efficiency', 0.0),
                        'bog_consumed': power_reqs['engine_power'] * voyage_days,
                        'bog_to_gcu': max(0, daily_profile['bog_volume'].sum() - 
                                        (power_reqs['engine_power'] * voyage_days))
                    },
                    power_data=power_reqs
                ),
                use_container_width=True
            )
            
            # Economic Analysis
            st.plotly_chart(
                create_economic_summary_chart(economics),
                use_container_width=True
            )
            
            # Efficiency Analysis
            st.plotly_chart(
                plot_vessel_efficiency_chart(
                    vessel_type="MEGI" if 'MEGI' in vessel_config else "DFDE",
                    power_data=power_reqs,
                    daily_data=daily_profile
                ),
                use_container_width=True
            )

    return return_data

def show_bog_calculator():
    """Main function for the LNG Vessel BOG Calculator"""
    st.title("LNG Vessel Optimization Suite")
    
    # Add descriptive information
    with st.expander("About This Calculator", expanded=False):
        st.markdown("""
        ### Advanced BOG and Vessel Performance Calculator
        
        This calculator provides comprehensive analysis of:
        - BOG generation and management strategies
        - Power consumption optimization
        - Economic impact assessment
        - Environmental considerations
        
        #### Key Features
        - Dynamic heel calculation based on vessel specifications
        - Real-time BOG rate adjustments for environmental conditions
        - Comprehensive economic analysis
        - Detailed visualization of all key metrics
        
        #### Supported Vessel Types
        - MEGI vessels with reliquefaction
        - DFDE vessels with different operating profiles
        """)
    
    try:
        # Load data and configurations
        world_ports_data = load_world_ports()
        vessel_configs = get_vessel_configs()
        
        # Vessel Selection and Configuration
        st.sidebar.title("Vessel Configuration")
        
        vessel_type = st.sidebar.selectbox(
            "Select Vessel Type",
            options=list(vessel_configs.keys()),
            help="Choose vessel propulsion type"
        )
        vessel_config = vessel_configs[vessel_type]
        
        # Display vessel specifications
        with st.expander("Vessel Technical Specifications", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("#### Capacity Specifications")
                st.write(f"Tank Capacity: {vessel_config['tank_capacity']:,} m³")
                st.write(f"Base BOG Rate: {vessel_config['base_bog_rate']}%/day")
                st.write(f"Engine Efficiency: {vessel_config['engine_efficiency']*100}%")
            
            with col2:
                st.write("#### Operating Parameters")
                st.write(f"Daily Consumption: {vessel_config['daily_consumption']:,} tons")
                st.write(f"Reliq Capacity: {vessel_config.get('reliq_capacity', 'N/A')} tons/hour")
                if 'emissions_reduction' in vessel_config:
                    st.write(f"Emissions Reduction: {vessel_config['emissions_reduction']*100}%")
            
            with col3:
                st.write("#### Power Specifications")
                if vessel_type == "MEGI":
                    st.write(f"Base Power: {vessel_config['power_output']['calm']} MW")
                    st.write(f"Adverse Power: {vessel_config['power_output']['adverse']} MW")
                else:
                    st.write(f"Max Power: {vessel_config['power_output'].get('max', 40)} MW")
                    st.write(f"NBOG Power: {vessel_config['power_output'].get('nbog_laden', 20)} MW")
        
        st.markdown("---")
        
        # Create voyage sections with progress indicator
        progress_bar = st.progress(0)
        st.info("Calculating laden voyage details...")
        
        laden_data = create_voyage_section_enhanced(
            "Laden",
            world_ports_data,
            vessel_config
        )
        progress_bar.progress(50)
        
        st.markdown("---")
        st.info("Calculating ballast voyage details...")
        
        ballast_data = create_voyage_section_enhanced(
            "Ballast",
            world_ports_data,
            vessel_config,
            True
        )
        progress_bar.progress(100)
        
        # Route Visualization and Summary
        if (laden_data['voyage_from'] and laden_data['voyage_to'] and 
            ballast_data['voyage_from'] and ballast_data['voyage_to']):
            
            st.markdown("---")
            st.subheader("Complete Voyage Analysis")
            
            # Route visualization
            st.write("### Route Visualization")
            laden_ports = [laden_data['voyage_from'], laden_data['voyage_to']]
            ballast_ports = [ballast_data['voyage_from'], ballast_data['voyage_to']]
            
            route_map = plot_combined_route(laden_ports, ballast_ports, world_ports_data)
            st_folium(route_map, width=800, height=500)
            
            # Voyage Summary
            if laden_data.get('economics') and ballast_data.get('economics'):
                st.write("### Voyage Summary")
                
                col1, col2, col3, col4 = st.columns(4)
                
                # Distance and Duration
                total_distance = laden_data['distance'] + ballast_data['distance']
                total_days = laden_data['voyage_days'] + ballast_data['voyage_days']
                
                with col1:
                    st.metric(
                        "Total Distance",
                        f"{total_distance:,.0f} NM",
                        help="Round trip distance"
                    )
                    st.metric(
                        "Total Duration",
                        f"{total_days:.1f} days",
                        help="Round trip duration"
                    )
                
                # BOG Metrics
                total_bog = (laden_data['daily_profile']['bog_volume'].sum() + 
                           ballast_data['daily_profile']['bog_volume'].sum())
                
                with col2:
                    st.metric(
                        "Total BOG Generated",
                        f"{total_bog:,.1f} m³",
                        help="Total boil-off gas volume"
                    )
                    if vessel_type == "MEGI":
                        total_reliquefied = (
                            total_bog * vessel_config['reliq_efficiency']
                        )
                        st.metric(
                            "Total BOG Reliquefied",
                            f"{total_reliquefied:,.1f} m³",
                            help="Volume of BOG recovered"
                        )
                
                # Economic Metrics
                total_benefit = (laden_data['economics']['net_benefit'] + 
                               ballast_data['economics']['net_benefit'])
                total_emissions = (laden_data['economics']['emissions_value'] + 
                                 ballast_data['economics']['emissions_value'])
                
                with col3:
                    st.metric(
                        "Net Economic Benefit",
                        f"${total_benefit:,.2f}",
                        help="Total economic value generated"
                    )
                    st.metric(
                        "Environmental Value",
                        f"${total_emissions:,.2f}",
                        help="Value of emissions reduction"
                    )
                
                # Efficiency Metrics
                avg_power = (laden_data['power_reqs']['total_power'] + 
                           ballast_data['power_reqs']['total_power']) / 2
                
                with col4:
                    st.metric(
                        "Average Power",
                        f"{avg_power:.1f} MW",
                        help="Average power consumption"
                    )
                    st.metric(
                        "Total Value Generated",
                        f"${(total_benefit + total_emissions):,.2f}",
                        help="Combined economic and environmental benefits"
                    )
                
                # Generate Report
                if st.button("Generate Detailed Report"):
                    report = create_comprehensive_report(
                        laden_data, ballast_data,
                        vessel_type, vessel_config,
                        total_distance, total_days,
                        total_bog, total_benefit,
                        total_emissions
                    )
                    
                    st.download_button(
                        label="Download Report",
                        data=report.to_csv().encode('utf-8'),
                        file_name='voyage_optimization_report.csv',
                        mime='text/csv'
                    )
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.info("Please check your inputs and try again.")
        st.exception(e)

if __name__ == "__main__":
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

def create_comprehensive_report(
    laden_data: dict,
    ballast_data: dict,
    vessel_type: str,
    vessel_config: dict,
    total_distance: float,
    total_days: float,
    total_bog: float,
    total_benefit: float,
    total_emissions: float
) -> pd.DataFrame:
    """
    Create a comprehensive voyage report including all key metrics
    """
    report_data = {
        'Voyage Summary': {
            'Vessel Type': vessel_type,
            'Total Distance (NM)': f"{total_distance:,.0f}",
            'Total Duration (days)': f"{total_days:.1f}",
            'Total BOG Generated (m³)': f"{total_bog:,.1f}",
            'Total Economic Benefit ($)': f"{total_benefit:,.2f}",
            'Environmental Value ($)': f"{total_emissions:,.2f}",
            'Total Value Generated ($)': f"{(total_benefit + total_emissions):,.2f}"
        },
        'Laden Voyage': {
            'From Port': laden_data['voyage_from'],
            'To Port': laden_data['voyage_to'],
            'Distance (NM)': f"{laden_data['distance']:,.0f}",
            'Duration (days)': f"{laden_data['voyage_days']:.1f}",
            'Initial Cargo (m³)': f"{laden_data['initial_cargo']:,.0f}",
            'Average BOG Rate (%/day)': f"{laden_data['daily_profile']['bog_rate'].mean():.3f}",
            'Total BOG (m³)': f"{laden_data['daily_profile']['bog_volume'].sum():,.1f}",
            'Average Power (MW)': f"{laden_data['power_reqs']['total_power']:.1f}",
            'Economic Benefit ($)': f"{laden_data['economics']['net_benefit']:,.2f}"
        },
        'Ballast Voyage': {
            'From Port': ballast_data['voyage_from'],
            'To Port': ballast_data['voyage_to'],
            'Distance (NM)': f"{ballast_data['distance']:,.0f}",
            'Duration (days)': f"{ballast_data['voyage_days']:.1f}",
            'Heel Quantity (m³)': f"{ballast_data['initial_cargo']:,.0f}",
            'Average BOG Rate (%/day)': f"{ballast_data['daily_profile']['bog_rate'].mean():.3f}",
            'Total BOG (m³)': f"{ballast_data['daily_profile']['bog_volume'].sum():,.1f}",
            'Average Power (MW)': f"{ballast_data['power_reqs']['total_power']:.1f}",
            'Economic Benefit ($)': f"{ballast_data['economics']['net_benefit']:,.2f}"
        },
        'Technical Analysis': {
            'Engine Efficiency (%)': f"{vessel_config['engine_efficiency']*100:.1f}",
            'Reliquefaction Efficiency (%)': f"{vessel_config.get('reliq_efficiency', 0)*100:.1f}",
            'Daily Consumption (tons)': f"{vessel_config['daily_consumption']:,.1f}",
            'Emissions Reduction (%)': f"{vessel_config.get('emissions_reduction', 0)*100:.1f}"
        }
    }
    
    return pd.DataFrame.from_dict(report_data, orient='index')

def calculate_optimal_heel(
    vessel_config: dict,
    voyage_days: float,
    ambient_temp: float,
    wave_height: float,
    safety_factor: float = 1.2
) -> dict:
    """
    Calculate optimal heel quantity considering all factors
    """
    # Base heel requirement for tank cooling
    min_cooling_heel = vessel_config['tank_capacity'] * 0.008
    
    # Consumption-based heel
    daily_consumption = vessel_config['daily_consumption']
    consumption_heel = daily_consumption * voyage_days * safety_factor
    
    # Environmental factor adjustments
    temp_factor = 1.0 + (ambient_temp - 19.5) / 100.0
    wave_factor = 1.0 + wave_height * 0.02
    
    # Adjusted heel requirements
    adjusted_min_heel = max(
        min_cooling_heel,
        consumption_heel * temp_factor * wave_factor
    )
    
    max_heel = vessel_config['tank_capacity'] * 0.02
    recommended_heel = min(
        (adjusted_min_heel + max_heel) / 2,
        max_heel
    )
    
    return {
        'min_heel': adjusted_min_heel,
        'max_heel': max_heel,
        'recommended_heel': recommended_heel,
        'factors': {
            'temperature': temp_factor,
            'wave': wave_factor,
            'safety': safety_factor
        }
    }

def validate_input_data(data: dict) -> tuple[bool, str]:
    """
    Validate input data for calculations
    """
    required_fields = [
        'voyage_from',
        'voyage_to',
        'distance',
        'voyage_days',
        'initial_cargo'
    ]
    
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    if data['distance'] <= 0:
        return False, "Invalid distance value"
    
    if data['voyage_days'] <= 0:
        return False, "Invalid voyage duration"
    
    if data['initial_cargo'] <= 0:
        return False, "Invalid cargo/heel quantity"
    
    return True, "Data validation successful"

def export_full_analysis(
    laden_data: dict,
    ballast_data: dict,
    vessel_config: dict,
    file_name: str = "voyage_analysis.xlsx"
) -> bytes:
    """
    Export complete analysis to Excel file
    """
    with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
        # Voyage Summary
        summary_df = create_comprehensive_report(
            laden_data, ballast_data,
            "MEGI" if 'MEGI' in vessel_config else "DFDE",
            vessel_config,
            laden_data['distance'] + ballast_data['distance'],
            laden_data['voyage_days'] + ballast_data['voyage_days'],
            (laden_data['daily_profile']['bog_volume'].sum() + 
             ballast_data['daily_profile']['bog_volume'].sum()),
            (laden_data['economics']['net_benefit'] + 
             ballast_data['economics']['net_benefit']),
            (laden_data['economics']['emissions_value'] + 
             ballast_data['economics']['emissions_value'])
        )
        summary_df.to_excel(writer, sheet_name='Voyage Summary')
        
        # Daily Profiles
        laden_data['daily_profile'].to_excel(writer, sheet_name='Laden Profile')
        ballast_data['daily_profile'].to_excel(writer, sheet_name='Ballast Profile')
        
        # Economic Analysis
        economics_df = pd.DataFrame({
            'Laden': laden_data['economics'],
            'Ballast': ballast_data['economics']
        })
        economics_df.to_excel(writer, sheet_name='Economics')
        
        # Technical Analysis
        tech_data = {
            'Power Requirements': {
                'Laden': laden_data['power_reqs'],
                'Ballast': ballast_data['power_reqs']
            },
            'Vessel Configuration': vessel_config
        }
        pd.DataFrame(tech_data).to_excel(writer, sheet_name='Technical')
    
    return open(file_name, 'rb').read()
