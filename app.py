import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb - Full", layout="wide")

# --- CSS PER TESTI GRANDI ---
st.markdown("""
    <style>
    .stSelectbox label, .stRadio label, .stMultiSelect label { font-size: 20px !important; font-weight: bold !important; color: #1E3A8A; }
    .stTabs [data-baseweb="tab"] { font-size: 22px !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- MAPPATURA SCENARI ---
MAPPING = {
    "Baseline (CT)": "Gestione Tradizionale (Baseline)",
    "CC (CT)": "Cover crop (CT)",
    "Res (CT)": "Residui (CT)",
    "CC + Res (CT)": "Cover + Residui (Tradizionale)",
    "MT": "Minima Lavorazione",
    "MT + Res": "Minima + Residui",
    "MT + CC": "Minima + Cover",
    "MT + CC + Res": "Minima + Cover + Residui"
}

def decode(name):
    return MAPPING.get(name.strip(), name.strip())

@st.cache_data
def load_data(provincia, scelta_amm):
    suffix = {"Cremona": "digestate", "Mantova": "slurry", "Piacenza": "manure"}[provincia]
    file_name = f"{provincia}_{suffix}.xlsx" if scelta_amm == "Sì" else f"{provincia}_NO{suffix}.xlsx"
    try:
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df['Scenario_Esteso'] = df['Scenario'].apply(decode)
        return df
    except: return None

st.title("🌱 Dashboard Decarbonizzazione Casalasco")
tab1, tab2, tab3 = st.tabs(["📊 LIVELLO 1", "🧪 LIVELLO 2", "🌍 LIVELLO 3"])

# --- LIVELLO 1: MULTI-SCENARIO ---
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with c2: a1 = st.radio(f"Uso Ammendante ({p1})?", ["Sì", "No"], horizontal=True, key="a1")
    df1 = load_data(p1, a1)
    if df1 is not None:
        with c3: rot1 = st.selectbox("🚜 Rotazione", df1['Rotazione'].unique(), key="rot1")
        df1_r = df1[df1['Rotazione'] == rot1].copy()
        scen_multi = st.multiselect("✨ Seleziona Scenari (dal 2026)", [s for s in df1_r['Scenario_Esteso'].unique() if s != "Gestione Tradizionale (Baseline)"], key="m1")
        
        if scen_multi:
            animation_list = []
            targets = scen_multi + ["Gestione Tradizionale (Baseline)"]
            for m in range(1, 121, 4):
                for s in targets:
                    base_data = df1_r[(df1_r['Scenario_Esteso'] == "Gestione Tradizionale (Baseline)") & (df1_r['Mese_Progressivo'] <= m)].copy()
                    scen_data = df1_r[(df1_r['Scenario_Esteso'] == s) & (df1_r['Mese_Progressivo'] <= m)].copy()
                    temp = base_data if m <= 60 else scen_data
                    temp['Scenario_Visualizzato'] = s
                    temp['Frame'] = m
                    animation_list.append(temp)
            
            df_anim = pd.concat(animation_list)
            fig1 = px.line(df_anim, x='Data', y='total_soc', color='Scenario_Visualizzato', animation_frame='Frame',
                           color_discrete_map={"Gestione Tradizionale (Baseline)": "#0000FF"}, template="plotly_white")
            fig1.layout.updatemenus = [dict(type="buttons", showactive=False, x=0, y=-0.15, buttons=[dict(label="▶ AVVIA SIMULAZIONE", method="animate", args=[None, {"frame": {"duration": 40}}])])]
            fig1.update_traces(line=dict(width=3), selector=dict(name="Gestione Tradizionale (Baseline)"))
            st.plotly_chart(fig1, use_container_width=True)

# --- LIVELLO 2: AMMENDANTE SI/NO ---
with tab2:
    p2 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p2")
    df_si = load_data(p2, "Sì")
    df_no = load_data(p2, "No")
    if df_si is not None and df_no is not None:
        c1, c2 = st.columns(2)
        with c1: rot2 = st.selectbox("🚜 Rotazione", df_si['Rotazione'].unique(), key="rot2")
        with c2: scen2 = st.selectbox("✨ Scenario Rigenerativo", [s for s in df_si['Scenario_Esteso'].unique() if "Baseline" not in s], key="scen2")
        
        label_amm = {"Cremona": "Digestato", "Mantova": "Slurry", "Piacenza": "Letame"}[p2]
        targets = {f"{scen2} (+ {label_amm})": (df_si, scen2), f"{scen2} (Senza)": (df_no, scen2), "Baseline (Rif. Blu)": (df_si, "Gestione Tradizionale (Baseline)")}
        
        anim2 = []
        for m in range(1, 121, 4):
            for name, (source_df, source_scen) in targets.items():
                d_r = source_df[source_df['Rotazione'] == rot2]
                if m <= 60:
                    temp = d_r[(d_r['Scenario_Esteso'] == "Gestione Tradizionale (Baseline)") & (d_r['Mese_Progressivo'] <= m)].copy()
                else:
                    temp = d_r[(d_r['Scenario_Esteso'] == source_scen) & (d_r['Mese_Progressivo'] <= m)].copy()
                temp['Legenda'] = name
                temp['Frame'] = m
                anim2.append(temp)
        
        df_anim2 = pd.concat(anim2)
        fig2 = px.line(df_anim2, x='Data', y='total_soc', color='Legenda', animation_frame='Frame', 
                       color_discrete_map={"Baseline (Rif. Blu)": "#0000FF"}, template="plotly_white")
        fig2.layout.updatemenus = [dict(type="buttons", showactive=False, x=0, y=-0.15, buttons=[dict(label="▶ AVVIA COMPARAZIONE", method="animate", args=[None, {"frame": {"duration": 40}}])])]
        st.plotly_chart(fig2, use_container_width=True)

# --- LIVELLO 3: DUE COMBINAZIONI ---
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        pa = st.selectbox("📍 Provincia A", ["Cremona", "Mantova", "Piacenza"], key="pa")
        aa = st.radio("Ammendante A", ["Sì", "No"], key="aa")
    with col2:
        pb = st.selectbox("📍 Provincia B", ["Cremona", "Mantova", "Piacenza"], index=1, key="pb")
        ab = st.radio("Ammendante B", ["Sì", "No"], key="ab")
    
    dfa = load_data(pa, aa)
    dfb = load_data(pb, ab)
    if dfa is not None and dfb is not None:
        rot3 = st.selectbox("🚜 Rotazione Comune", list(set(dfa['Rotazione']) & set(dfb['Rotazione'])), key="rot3")
        scen3 = st.selectbox("✨ Scenario da confrontare", [s for s in dfa['Scenario_Esteso'].unique() if "Baseline" not in s], key="scen3")
        
        anim3 = []
        lA, lB = f"{pa} ({aa} Amm.)", f"{pb} ({ab} Amm.)"
        for m in range(1, 121, 4):
            for (curr_df, curr_label) in [(dfa, lA), (dfb, lB)]:
                d_r = curr_df[curr_df['Rotazione'] == rot3]
                temp = d_r[(d_r['Scenario_Esteso'] == ( "Gestione Tradizionale (Baseline)" if m <= 60 else scen3)) & (d_r['Mese_Progressivo'] <= m)].copy()
                temp['Sito'] = curr_label
                temp['Frame'] = m
                anim3.append(temp)
        
        df_anim3 = pd.concat(anim3)
        fig3 = px.line(df_anim3, x='Data', y='total_soc', color='Sito', animation_frame='Frame', template="plotly_white")
        fig3.layout.updatemenus = [dict(type="buttons", showactive=False, x=0, y=-0.15, buttons=[dict(label="▶ AVVIA CONFRONTO", method="animate", args=[None, {"frame": {"duration": 40}}])])]
        st.plotly_chart(fig3, use_container_width=True)
