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

    with col4:
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
        vessel_name = "CITY ISLAND"
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
                    ["ras laffan", "milford haven", 2.0, 20.0, 50.0, "LNG"],
                    ["milford haven", "rotterdam", 3.0, 15.0, 40.0, "LNG"]
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
    #st.markdown("### Voyage Planning")

    # Calculate projected CII button
    # New code with styled button
    col1, col2 = st.columns([7, 1])

    with col1: st.markdown("### Voyage Planning")  
    with col2:
        calculate_projected = st.button(
            'Calculate Projected CII', 
            disabled=not bool(st.session_state.cii_data),
            help="Current CII calculation required before projecting future CII",
            use_container_width=True,
            key="calculate_projected_cii_button"  # Unique key
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
                    "Fuel Used (mT/d)",
                    help="Enter total fuel consumption",
                    min_value=0,
                    step=0.1,
                    required=True
                ),
                "Fuel Type": st.column_config.SelectboxColumn(
                    "Fuel Type",
                    help="Select fuel type",
                    options=list(EMISSION_FACTORS.keys()),
                    required=True
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
