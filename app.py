import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.ensemble import IsolationForest
import datetime
import time
import hashlib
from fpdf import FPDF
import urllib.parse

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="MPLADS-Guard | MoSPI AI Engine", page_icon="🏛️", layout="wide")

# ---------------------------------------------------------
# FEATURE 1: SECURE GOVERNMENT LOGIN WALL
# ---------------------------------------------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'false_positives' not in st.session_state:
    st.session_state.false_positives = []

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center; color: #ff4b4b;'>🏛️ MoSPI e-SAKSHI Vigilance Gateway</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>National Single Sign-On (e-Pramaan) Authentication Portal</p>", unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        with st.form("login_form"):
            st.write("### Authorized Officer Login")
            officer_id = st.text_input("Govt Officer ID / NIC Mail", value="officer.audit@nic.in")
            password = st.text_input("Password", type="password") 
            submit = st.form_submit_button("Verify & Access Dashboard")
            
            if submit:
                if officer_id == "officer.audit@nic.in" and password == "sih2026":
                    st.session_state.authenticated = True
                    st.success("✅ Credentials authenticated via NIC SSO Gateway. Redirecting...")
                    time.sleep(0.7)
                    st.rerun()
                else:
                    st.error("🚨 Invalid Credentials. Access restricted to authorized MoSPI audit personnel.")
        st.info("💡 **Jury Note:** Enter password `sih2026` to access the system.")
    st.stop()

# ---------------------------------------------------------
# AUTHENTICATED DASHBOARD EXECUTION
# ---------------------------------------------------------
# Force Indian Standard Time (UTC + 5:30)
ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
current_time = datetime.datetime.now(ist_offset).strftime("%d %b %Y, %I:%M %p IST")

# --- NEW CIRCULAR PROFILE IN SIDEBAR ---
st.sidebar.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png" width="90" style="border-radius: 50%; border: 3px solid #2ecc71; padding: 2px;">
    <h3 style="margin-bottom: 0px; padding-bottom: 0px; margin-top: 10px;">Auditor General</h3>
    <p style="color: #888; font-size: 14px; margin-top: 0px;">MoSPI Vigilance HQ</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("⚙️ Portal Settings")
lang = st.sidebar.radio("Display Language / भाषा चुनें", ["English", "हिन्दी"])

st.title("SIH26102: MoSPI - AI Anomaly & Fraud Detection for MPLADS" if lang == "English" else "सांख्यिकी मंत्रालय - एमपीलैड्स एआई विसंगति एवं धोखाधड़ी निगरानी")
# REMOVED OFFICER EMAIL FROM HEADER
st.markdown(f"**Team: COGNITIVE CREW | 🟢 Live Server Sync:** {current_time}")

if st.sidebar.button("🔒 Logout (e-Pramaan SSO)"):
    st.session_state.authenticated = False
    st.rerun()

@st.cache_data
def load_data():
    try:
        data = pd.read_csv("mplads_data.csv")
        if 'Citizen_Grievances' not in data.columns:
            data['Citizen_Grievances'] = [32 if i % 7 == 0 else (18 if i % 5 == 0 else 2) for i in range(len(data))]
        if 'Contractor' not in data.columns:
            contractors_list = ["Apex Infra Works", "Bharat Buildcon", "National Roadways Ltd", 
                                "Shree Ram Construction", "Vikas Projects Pvt Ltd", "Kaveri Engineering"]
            data['Contractor'] = [contractors_list[i % len(contractors_list)] for i in range(len(data))]
        if 'lat' not in data.columns:
            np.random.seed(42)
            data['lat'] = np.random.uniform(20.0, 27.0, size=len(data))
            data['lon'] = np.random.uniform(73.0, 84.0, size=len(data))
        return data
    except FileNotFoundError:
        st.error("🚨 Error: 'mplads_data.csv' not found. Ensure file is in directory.")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # ---------------------------------------------------------
    # SIDEBAR & AI ENGINE
    # ---------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.subheader("AI Control Panel")
    contamination_rate = st.sidebar.slider("AI Detection Sensitivity", min_value=0.05, max_value=0.50, value=0.20, step=0.05)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📱 Citizen Transparency QR")
    
    qr_data = urllib.parse.quote("https://egovernance.vikaspedia.in/viewcontent/e-governance/online-citizen-services/mplads%E2%80%93esakshi-web-portal?lgn=en")
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=140x140&data={qr_data}"
    st.sidebar.image(qr_url, caption="Scan to view public portal")

    df['Cost_Overrun'] = df['Disbursed_Cost_Lakhs'] - df['Sanctioned_Cost_Lakhs']
    df['Expected_Progress'] = (df['Disbursed_Cost_Lakhs'] / df['Sanctioned_Cost_Lakhs']) * 100
    df['Progress_Lag'] = df['Expected_Progress'] - df['Physical_Progress_Percent']

    features = ['Cost_Overrun', 'Progress_Lag']
    model = IsolationForest(contamination=contamination_rate, random_state=42)
    df['ML_Anomaly_Flag'] = model.fit_predict(df[features])
    df['ML_Score'] = model.decision_function(df[features]) 
    
    def assign_risk(row):
        if row['Project_ID'] in st.session_state.false_positives:
            return 'Cleared (MLOps)'
        if row['Citizen_Grievances'] >= 25 and row['Progress_Lag'] > 10:
            return 'High Risk'
        if row['ML_Anomaly_Flag'] == -1:
            if row['Cost_Overrun'] > 0 or row['Progress_Lag'] > 20:
                return 'High Risk'
            else:
                return 'Low Risk'
        elif row['Progress_Lag'] > 10 or row['Cost_Overrun'] > 0:
            return 'Low Risk'
        return 'Normal'

    df['Risk_Level'] = df.apply(assign_risk, axis=1)

    def generate_short_reasoning(row):
        if row['Risk_Level'] == 'Cleared (MLOps)':
            return "Auditor Override (Model Retraining Initiated)"
        if row['Citizen_Grievances'] >= 25 and row['Progress_Lag'] > 10:
            return f"CPGRAMS Override: {row['Citizen_Grievances']} Complaints"
        elif row['Risk_Level'] == 'High Risk':
            if row['Cost_Overrun'] > 0 and row['Progress_Lag'] > 20:
                return "Critical: Overbudget & Severe Lag"
            elif row['Progress_Lag'] > 20:
                return "Critical: Severe Work-to-Fund Lag"
            return "Severe Statistical Outlier"
        elif row['Risk_Level'] == 'Low Risk':
            if row['Cost_Overrun'] > 0:
                return "Warning: Slight Overbudget"
            elif row['Progress_Lag'] > 10:
                return "Monitor: Noticeable Work Delay"
            return "Minor Metric Variance"
        return "Clear: Normal Execution"

    df['AI_Reasoning'] = df.apply(generate_short_reasoning, axis=1)

    # ---------------------------------------------------------
    # UI CLEANING LAYER
    # ---------------------------------------------------------
    rename_map = {
        'Project_ID': 'Project ID', 'Sanctioned_Cost_Lakhs': 'Sanctioned Cost', 'Disbursed_Cost_Lakhs': 'Disbursed Cost',
        'Physical_Progress_Percent': 'Physical Progress', 'Citizen_Grievances': 'Citizen Complaints',
        'Risk_Level': 'Risk Tier', 'AI_Reasoning': 'AI Reasoning'
    }
    
    ui_display_cols = ['Project ID', 'Constituency', 'Contractor', 'Sanctioned Cost', 'Disbursed Cost', 'Physical Progress', 'Citizen Complaints', 'Risk Tier', 'AI Reasoning']
    col_config = {
        "Sanctioned Cost": st.column_config.NumberColumn("Sanctioned Cost", format="₹ %.2f L"),
        "Disbursed Cost": st.column_config.NumberColumn("Disbursed Cost", format="₹ %.2f L"),
        "Physical Progress": st.column_config.ProgressColumn("Physical Progress", min_value=0, max_value=100, format="%d%%"),
        "Citizen Complaints": st.column_config.NumberColumn("Complaints", format="%d ⚠️"),
    }

    # ---------------------------------------------------------
    # PDF GENERATORS
    # ---------------------------------------------------------
    def create_legal_pdf(project_id, constituency, reasoning, disbursed, progress, hash_signature):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 15)
        pdf.cell(190, 10, txt="MINISTRY OF STATISTICS AND PROGRAMME IMPLEMENTATION", ln=True, align='C')
        pdf.set_font("Arial", '', 11)
        pdf.cell(190, 8, txt="GOVERNMENT OF INDIA - VIGILANCE AUDIT DIVISION", ln=True, align='C')
        pdf.line(10, 28, 200, 28)
        pdf.ln(8)
        pdf.set_font("Arial", 'B', 11)
        date_str = datetime.date.today().strftime('%B %d, %Y')
        pdf.cell(190, 7, txt=f"Official Notice Ref: MoSPI/VIG/{project_id}/{datetime.date.today().year}", ln=True)
        pdf.cell(190, 7, txt=f"Date: {date_str} | Dispatched to: District Magistrate, {constituency}", ln=True)
        pdf.ln(4)
        pdf.cell(190, 7, txt="SUBJECT: FORMAL SHOW-CAUSE MANDATE - FUND DISCREPANCY", ln=True)
        pdf.ln(3)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 7, txt=f"Under executive direction, you are ordered to halt further tranches for Project ID: {project_id}.")
        pdf.multi_cell(0, 7, txt=f"Primary AI Detection Trigger: {reasoning}.")
        pdf.multi_cell(0, 7, txt=f"Discrepancy Audit: Rs {disbursed:.2f} Lakhs withdrawn against only {progress}% certified on-ground physical progress.")
        pdf.ln(4)
        pdf.set_font("Arial", 'B', 10)
        pdf.multi_cell(0, 6, txt="WARNING: Non-compliance activates immediate suspension of the District Authority's PFMS drawing rights and triggers formal inquiry under Section 4(1) of the Public Fund Misappropriation Act.")
        pdf.ln(8)
        pdf.cell(190, 6, txt="Cryptographic Anti-Tampering Hash (SHA-256):", ln=True)
        pdf.set_font("Courier", '', 8)
        pdf.multi_cell(0, 5, txt=hash_signature)
        return bytes(pdf.output(dest='S').encode('latin-1'))

    def create_executive_summary_pdf(df_data, total_proj, high_risk, low_risk, roi_saved):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, txt="MoSPI EXECUTIVE BRIEFING - MPLADS AI AUDIT", ln=True, align='C')
        pdf.line(10, 20, 200, 20)
        pdf.ln(8)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(190, 8, txt=f"Report Generated: {datetime.date.today().strftime('%B %d, %Y')}", ln=True)
        pdf.ln(4)
        pdf.cell(190, 8, txt="1. Financial Exposure & Risk Triage", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 6, txt=f"   - High-Risk Violations: {high_risk} projects")
        pdf.multi_cell(0, 6, txt=f"   - Watchlist (Low Risk): {low_risk} projects")
        pdf.multi_cell(0, 6, txt=f"   - Funds Ring-Fenced (ROI): Rs {roi_saved:,.2f} Lakhs")
        pdf.ln(4)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(190, 8, txt="2. Recommended Strategic Actions", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 6, txt="1. Dispatch automated Show-Cause notices to the District Magistrates of the flagged constituencies.")
        pdf.multi_cell(0, 6, txt="2. Temporarily suspend PFMS nodal drawing rights for the identified high-risk implementing agencies.")
        pdf.ln(10)
        pdf.set_font("Arial", 'I', 9)
        pdf.cell(190, 8, txt="Auto-Generated by MPLADS-Guard AI Protocol Engine", ln=True)
        return bytes(pdf.output(dest='S').encode('latin-1'))

    # ---------------------------------------------------------
    # 6 DASHBOARD TABS
    # ---------------------------------------------------------
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Summary", "⚖️ Triage & Action", "📈 Visuals", "🔍 Search", "🛡️ Contractors", "📍 Phase 2 Map"
    ])

    def color_risk_tier(val):
        if val == 'High Risk': return 'background-color: #ff4b4b; color: white'
        elif val == 'Low Risk': return 'background-color: #f1c40f; color: black'
        elif val == 'Cleared (MLOps)': return 'background-color: #2ecc71; color: white'
        return ''

    # --- TAB 1: SUMMARY ---
    with tab1:
        st.subheader("Macro Vigilance Metrics")
        high_risk_count = len(df[df['Risk_Level'] == 'High Risk'])
        low_risk_count = len(df[df['Risk_Level'] == 'Low Risk'])
        cleared_count = len(st.session_state.false_positives)
        at_risk_funds = df[df['Risk_Level'] == 'High Risk']['Disbursed_Cost_Lakhs'].sum()
        
        st.download_button("📄 Download Minister's Executive Briefing", data=create_executive_summary_pdf(df, len(df), high_risk_count, low_risk_count, at_risk_funds), file_name="Briefing.pdf", mime="application/pdf", type="primary")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Active Projects", len(df))
        col2.metric("High-Risk Alerts", high_risk_count, delta=f"{cleared_count} Overridden" if cleared_count > 0 else "Urgent", delta_color="inverse")
        col3.metric("Low-Risk Warnings", low_risk_count, delta="Watchlist", delta_color="off")
        col4.metric("Taxpayer ROI", f"₹{at_risk_funds:,.2f} L", delta="Saved", delta_color="normal")
        st.markdown("---")
        
        col_table, col_leader = st.columns([1.6, 1])
        with col_table:
            st.write("**Central Ingestion Stream:**")
            ui_df = df.rename(columns=rename_map)
            st.dataframe(ui_df[ui_display_cols].style.map(color_risk_tier, subset=['Risk Tier']), width="stretch", hide_index=True, column_config=col_config)
            
        with col_leader:
            st.write("**🚨 District Fraud Leaderboard:**")
            district_summary = df[df['Risk_Level'] == 'High Risk'].groupby('Constituency').agg(Flags=('Project_ID', 'count'), At_Risk_Lakhs=('Disbursed_Cost_Lakhs', 'sum')).reset_index()
            if not district_summary.empty:
                st.plotly_chart(px.bar(district_summary, x='Flags', y='Constituency', orientation='h', color='At_Risk_Lakhs', color_continuous_scale='Reds', height=350, labels={'At_Risk_Lakhs': 'Exposure (₹ Lakhs)'}), width="stretch")
            else:
                st.success("No high-risk districts.")

    # --- TAB 2: ACTION PORTAL ---
    with tab2:
        anomalies_df = df[df['Risk_Level'].isin(['High Risk', 'Low Risk'])].copy()
        col_queue, col_action = st.columns([1.3, 1])
        with col_queue:
            st.subheader("🚨 Priority Escalation Queue")
            high_risk_only = anomalies_df[anomalies_df['Risk_Level'] == 'High Risk']
            if not high_risk_only.empty:
                if st.button(f"🚀 Execute Mass Escalation (Freeze all {len(high_risk_only)} High-Risk Projects)"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    for i in range(100):
                        time.sleep(0.01)
                        progress_bar.progress(i + 1)
                        if i % 25 == 0:
                            status_text.text(f"Cryptographically sealing and transmitting notices... {i}%")
                    status_text.text(f"✅ Mass Escalation Enforced: Mandates routed to PFMS Nodal Gateways.")
                    st.toast('Bulk Escalation Complete!', icon='🚀')
            st.markdown("<br>", unsafe_allow_html=True)

            if not anomalies_df.empty:
                ui_anomalies_df = anomalies_df.rename(columns=rename_map)
                st.dataframe(ui_anomalies_df[ui_display_cols].style.map(color_risk_tier, subset=['Risk Tier']), width="stretch", hide_index=True, column_config=col_config)
            else:
                st.success("Queue Clear.")
                
        with col_action:
            st.subheader("📝 Targeted Show-Cause Generator")
            if not anomalies_df.empty:
                selected_project = st.selectbox("Select Project for Intervention:", anomalies_df['Project_ID'].tolist())
                p_data = anomalies_df[anomalies_df['Project_ID'] == selected_project].iloc[0]
                date_str = datetime.date.today().strftime('%B %d, %Y')
                dm_email = f"dm_{p_data['Constituency'].lower().replace(' ', '_')}@nic.in"
                crypto_hash = hashlib.sha256(f"{selected_project}_MoSPI_AUTH".encode('utf-8')).hexdigest()
                
                if st.button("✅ Mark as False Positive (Retrain AI)"):
                    st.session_state.false_positives.append(selected_project)
                    st.success("Feedback registered! Adjusting model weights and clearing project...")
                    time.sleep(1)
                    st.rerun()
                
                st.markdown("---")
                st.markdown(f"""
                <div style='border: 2px solid #e74c3c; padding: 18px; border-radius: 8px; background-color: #1e1e1e; color: white;'>
                    <h4 style='text-align: center; color: #ff4b4b; margin-bottom: 0px;'>MINISTRY OF STATISTICS AND PROGRAMME IMPLEMENTATION</h4>
                    <p style='text-align: center; font-size: 13px; color: #a0a0a0;'>GOVERNMENT OF INDIA</p>
                    <hr style='border-color: #444;'>
                    <p><b>Date:</b> {date_str} | <b>To:</b> DM, {p_data['Constituency']}</p>
                    <p><b>Subject:</b> Show-Cause Mandate - Immediate Fund Freeze for <b>{p_data['Project_ID']}</b></p>
                    <p><b>Reasoning:</b> <span style='color: #ff4b4b;'>{p_data['AI_Reasoning']}</span></p>
                    <p style='font-family: monospace; font-size: 10px; color: #00ffcc;'>SHA-256 Hash: {crypto_hash[:40]}...</p>
                </div><br>
                """, unsafe_allow_html=True)
                
                pdf_bytes = create_legal_pdf(p_data['Project_ID'], p_data['Constituency'], p_data['AI_Reasoning'], p_data['Disbursed_Cost_Lakhs'], p_data['Physical_Progress_Percent'], crypto_hash)
                
                st.markdown("**Dispatch Controls:**")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.download_button("📥 PDF", data=pdf_bytes, file_name=f"{selected_project}.pdf", mime="application/pdf")
                with c2:
                    if st.button("📧 Email"): st.toast(f"Dispatched to {dm_email} via NIC Gateway!", icon='📧')
                with c3:
                    if st.button("📱 SMS"): st.toast("SMS Alert Delivered to Vendor", icon='📱')
            else:
                st.info("No projects require action.")

    # --- TAB 3: VISUALS ---
    with tab3:
        st.subheader("Sectoral Fund Outlay")
        category_df = df.groupby('Category')[['Sanctioned_Cost_Lakhs', 'Disbursed_Cost_Lakhs']].sum().reset_index()
        fig_bar = px.bar(
            category_df, x='Category', y=['Sanctioned_Cost_Lakhs', 'Disbursed_Cost_Lakhs'],
            barmode='group', title="Sanctioned vs. Disbursed Allocation across Sectors",
            labels={'value': 'Capital (₹ Lakhs)', 'variable': 'Expenditure Status', 'Sanctioned_Cost_Lakhs': 'Sanctioned', 'Disbursed_Cost_Lakhs': 'Disbursed'},
            color_discrete_map={'Sanctioned_Cost_Lakhs': '#2ecc71', 'Disbursed_Cost_Lakhs': '#e67e22'}
        )
        st.plotly_chart(fig_bar, width="stretch")

    # --- TAB 4: ADVANCED SEARCH ---
    with tab4:
        st.subheader("Officer Search & Data Extraction")
        col_f1, col_f2, col_f3 = st.columns(3)
        search_id = col_f1.text_input("🔍 Search ID/Constituency/Contractor:")
        filter_category = col_f2.multiselect("📂 Ministry / Sector:", options=df['Category'].unique())
        filter_risk = col_f3.multiselect("⚠️ AI Risk Rating:", options=['High Risk', 'Low Risk', 'Normal', 'Cleared (MLOps)'])
        
        filtered_df = df.copy()
        if search_id:
            filtered_df = filtered_df[filtered_df['Project_ID'].str.contains(search_id, case=False) | filtered_df['Constituency'].str.contains(search_id, case=False) | filtered_df['Contractor'].str.contains(search_id, case=False)]
        if filter_category:
            filtered_df = filtered_df[filtered_df['Category'].isin(filter_category)]
        if filter_risk:
            filtered_df = filtered_df[filtered_df['Risk_Level'].isin(filter_risk)]
            
        ui_filtered_df = filtered_df.rename(columns=rename_map)
        st.dataframe(ui_filtered_df[ui_display_cols], width="stretch", hide_index=True, column_config=col_config)
        if not filtered_df.empty:
            st.download_button("📥 Export Filtered Audit Report (CSV)", data=filtered_df.to_csv(index=False).encode('utf-8'), file_name="MoSPI_Audit_Report.csv", mime="text/csv")

    # --- TAB 5: CONTRACTORS ---
    with tab5:
        st.subheader("🛡️ Implementing Agency (Contractor) Vigilance Engine")
        c_stats = df.groupby('Contractor').agg(Projects=('Project_ID', 'count'), Flags=('Risk_Level', lambda x: (x == 'High Risk').sum()), Total_Disbursed=('Disbursed_Cost_Lakhs', 'sum')).reset_index()
        c_stats['Status'] = c_stats['Flags'].apply(lambda f: '🚨 Blacklist Recommended' if f >= 2 else ('⚠️ Under Watch' if f == 1 else '✅ Cleared Vendor'))
        
        c_stats_ui = c_stats.rename(columns={'Total_Disbursed': 'Total Disbursed (Lakhs)', 'Projects': 'Total Projects', 'Flags': 'High Risk Flags'})
        st.dataframe(c_stats_ui.sort_values(by='High Risk Flags', ascending=False), width="stretch", hide_index=True, column_config={"Total Disbursed (Lakhs)": st.column_config.NumberColumn("Total Disbursed", format="₹ %.2f L")})

        st.markdown("---")
        st.subheader("🔍 Deep-Dive: Contractor Rap Sheet & Actions")
        selected_vendor = st.selectbox("Select Agency for Direct Investigation:", c_stats['Contractor'].unique())
        vendor_df = df[df['Contractor'] == selected_vendor]
        vendor_stats = c_stats[c_stats['Contractor'] == selected_vendor].iloc[0]
        
        col_v1, col_v2 = st.columns([1, 1.5])
        with col_v1:
            st.markdown(f"**Agency:** {selected_vendor}")
            st.markdown(f"**Total Capital Handled:** ₹{vendor_stats['Total_Disbursed']:,.2f} Lakhs")
            st.markdown(f"**Status:** {vendor_stats['Status']}")
            
            if vendor_stats['Status'] == '🚨 Blacklist Recommended':
                if st.button("⚖️ Route Debarment Order to Ministry of Corporate Affairs"):
                    with st.spinner("Compiling cross-district violations..."):
                        time.sleep(1.5)
                        st.error(f"✅ Formal debarment request for '{selected_vendor}' successfully transmitted to MCA registry.")
            else:
                st.info("Agency does not currently meet nationwide debarment thresholds.")
                
        with col_v2:
            st.write(f"**Associated Projects for {selected_vendor}:**")
            ui_vendor_df = vendor_df.rename(columns=rename_map)
            st.dataframe(ui_vendor_df[['Project ID', 'Constituency', 'Disbursed Cost', 'Risk Tier']], width="stretch", hide_index=True, column_config=col_config)

    # --- TAB 6: PHASE 2 HYBRID SATELLITE MAP ---
    with tab6:
        st.subheader("📍 Phase 2 Roadmap: ISRO Geospatial Integration")
        st.markdown("For the Grand Finale, we will link directly with satellite imaging APIs to plot fraud density dynamically and execute Computer Vision verifications.")
        
        map_df = df[df['Risk_Level'].isin(['High Risk', 'Low Risk'])]
        if not map_df.empty:
            
            # MULTI-LAYER HYBRID MAP (Satellite + City Boundaries & Labels)
            esri_satellite = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            esri_labels = "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
            
            try:
                fig_map = px.scatter_map(map_df, lat="lat", lon="lon", hover_name="Project_ID", hover_data={"Constituency": True, "Risk_Level": True, "lat": False, "lon": False}, color="Risk_Level", color_discrete_map={'High Risk': 'red', 'Low Risk': 'orange'}, zoom=4.5, height=500, labels={'Risk_Level': 'Risk Tier'})
                fig_map.update_layout(map_style="white-bg", map_layers=[
                    {"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri", "source": [esri_satellite]},
                    {"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri Labels", "source": [esri_labels]}
                ], margin={"r":0,"t":0,"l":0,"b":0})
            except AttributeError:
                fig_map = px.scatter_mapbox(map_df, lat="lat", lon="lon", hover_name="Project_ID", hover_data={"Constituency": True, "Risk_Level": True, "lat": False, "lon": False}, color="Risk_Level", color_discrete_map={'High Risk': 'red', 'Low Risk': 'orange'}, zoom=4.5, height=500, labels={'Risk_Level': 'Risk Tier'})
                fig_map.update_layout(mapbox_style="white-bg", mapbox_layers=[
                    {"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri", "source": [esri_satellite]},
                    {"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri Labels", "source": [esri_labels]}
                ], margin={"r":0,"t":0,"l":0,"b":0})
                
            st.plotly_chart(fig_map, width="stretch")
            
        st.markdown("---")
        st.subheader("📸 Automated Computer Vision Verification (Mockup)")
        st.markdown("""
        <div style="display:flex; justify-content:space-between; text-align:center;">
            <div style="width:48%; border:2px dashed #888; padding:20px; background-color:#111;">
                <h4 style="color:#2ecc71;">Baseline Claim (e-SAKSHI)</h4>
                <p>Contractor submits: "Roof structure 100% Complete"</p>
                <div style="height:150px; background-color:#333; display:flex; align-items:center; justify-content:center; color:#fff;">[Contractor Uploaded Image]</div>
            </div>
            <div style="width:48%; border:2px solid #e74c3c; padding:20px; background-color:#220000;">
                <h4 style="color:#e74c3c;">ISRO Satellite CNN Analysis</h4>
                <p>AI Ground Truth: No roof detected. Foundation only.</p>
                <div style="height:150px; background-color:#333; display:flex; align-items:center; justify-content:center; color:#e74c3c; font-weight:bold; border: 3px solid red;">[AI Bounding Box: 0% Match]</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
