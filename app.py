import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb - Multilivello", layout="wide")

# --- CSS PER FONT E LAYOUT ---
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

# --- FUNZIONE CARICAMENTO ---
@st.cache_data
def get_data(prov, amm_si_no):
    # Costruzione dinamica nome file come i precedenti
    suffix = {"Cremona": "digestate", "Mantova": "slurry", "Piacenza": "manure"}[prov]
    file_name = f"{prov}_{suffix}.xlsx" if amm_si_no == "Sì" else f"{prov}_NO{suffix}.xlsx"
    try:
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df['Scenario_Esteso'] = df['Scenario'].apply(decode)
        return df
    except:
        return None

st.title("🌱 Dashboard Decarbonizzazione Casalasco")

tab1, tab2, tab3 = st.tabs(["📊 LIVELLO 1: Scenari", "🧪 LIVELLO 2: Ammendanti", "🌍 LIVELLO 3: Territorio"])

# ==========================================
# LIVELLO 1: ANALISI SCENARI AZIENDALI
# ==========================================
with tab1:
    col1, col2, col3 = st.columns(3)
    with col1: p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with col2: a1 = st.radio("Uso Ammendante", ["Sì", "No"], horizontal=True, key="a1")
    
    df1 = get_data(p1, a1)
    
    if df1 is not None:
        with col3: rot1 = st.selectbox("🚜 Rotazione", df1['Rotazione'].unique(), key="r1")
        df1_r = df1[df1['Rotazione'] == rot1].copy()
        
        baseline_n = "Gestione Tradizionale (Baseline)"
        scen_opzioni = [s for s in df1_r['Scenario_Esteso'].unique() if s != baseline_n]
        scen_scelti = st.multiselect("✨ Seleziona Pratiche Rigenerative", scen_opzioni, key="m1")

        if scen_scelti:
            # --- LOGICA ANIMAZIONE (BLU SOPRA FINO A 2026) ---
            scenari_attivi = scen_scelti + [baseline_n]
            animation_list = []
            for m in range(1, 121, 4):
                for s in scenari_attivi:
                    if m <= 60:
                        temp = df1_r[(df1_r['Scenario_Esteso'] == baseline_n) & (df1_r['Mese_Progressivo'] <= m)].copy()
                        temp['Scenario_Grafico'] = s
                    else:
                        temp = df1_r[(df1_r['Scenario_Esteso'] == s) & (df1_r['Mese_Progressivo'] <= m)].copy()
                        temp['Scenario_Grafico'] = s
                    temp['Frame'] = m
                    animation_list.append(temp)
            
            df_anim = pd.concat(animation_list)
            
            fig1 = px.line(df_anim, x='Data', y='total_soc', color='Scenario_Grafico',
                           animation_frame='Frame', template="plotly_white",
                           color_discrete_map={baseline_n: "#0000FF"},
                           range_y=[df1_r['total_soc'].min()*0.98, df1_r['total_soc'].max()*1.05])
            
            fig1.layout.updatemenus = [dict(type="buttons", showactive=False, x=0, y=-0.2,
                                           buttons=[dict(label="▶ AVVIA SIMULAZIONE", method="animate", args=[None, {"frame": {"duration": 50}}])])]
            fig1.layout.sliders = [dict(visible=False)]
            fig1.update_traces(line=dict(width=3), selector=dict(name=baseline_n))
            
            st.plotly_chart(fig1, use_container_width=True)

# ==========================================
# LIVELLO 2: IMPATTO AMMENDANTE (SI VS NO)
# ==========================================
with tab2:
    p2 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p2")
    df_si = get_data(p2, "Sì")
    df_no = get_data(p2, "No")
    
    if df_si is not None and df_no is not None:
        c1, c2 = st.columns(2)
        with c1: rot2 = st.selectbox("🚜 Rotazione", df_si['Rotazione'].unique(), key="r2")
        with c2: scen_2 = st.selectbox("✨ Scenario da comparare", [s for s in df_si['Scenario_Esteso'].unique() if "Baseline" not in s], key="s2")
        
        # Logica di unione dati SI/NO ammendante...
        st.info("Qui vedrai la differenza tra usare o meno il fertilizzante organico sullo stesso scenario.")
        # [Codice per grafico comparativo simile a Tab 1]

# ==========================================
# LIVELLO 3: CONFRONTO TERRITORIALE
# ==========================================
with tab3:
    st.subheader("Confronto tra due sistemi differenti")
    # Qui implementeremo il confronto tra Prov A e Prov B come discusso.
    st.warning("Seleziona i parametri nelle Tab precedenti per sbloccare i confronti avanzati.")
