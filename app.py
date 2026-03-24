import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb - Multilivello", layout="wide")

# --- CSS PER FONT GRANDI ---
st.markdown("""
    <style>
    .stSelectbox label, .stRadio label, .stMultiSelect label { font-size: 18px !important; font-weight: bold !important; color: #1E3A8A; }
    .stTabs [data-baseweb="tab"] { font-size: 20px; font-weight: bold; }
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

# --- CARICAMENTO DATI ---
@st.cache_data
def get_df(prov, amm_si_no):
    label = {"Cremona": "Digestato", "Mantova": "Slurry", "Piacenza": "Letame"}[prov]
    f_suffix = "digestate" if prov == "Cremona" else ("slurry" if prov == "Mantova" else "manure")
    file_name = f"{prov}_{f_suffix}.xlsx" if amm_si_no == "Sì" else f"{prov}_NO{f_suffix}.xlsx"
    
    try:
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df['Scenario_Esteso'] = df['Scenario'].apply(decode)
        df['Prov_Amm'] = f"{prov} ({'Sì' if amm_si_no == 'Sì' else 'No'} {label})"
        return df
    except:
        return None

# --- STRUTTURA A TAB ---
tab1, tab2, tab3 = st.tabs(["📊 Livello 1: Scenari Multipli", "🧪 Livello 2: Impatto Ammendante", "🌍 Livello 3: Confronto Territoriale"])

# ---------------------------------------------------------
# LIVELLO 1: UNA PROVINCIA - UNO AMMENDANTE - SCENARI MULTIPLI
# ---------------------------------------------------------
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: p1 = st.selectbox("Provincia", ["Cremona", "Mantova", "Piacenza"], key="l1_p")
    with c2: a1 = st.radio("Uso Ammendante", ["Sì", "No"], horizontal=True, key="l1_a")
    df1 = get_df(p1, a1)
    
    if df1 is not None:
        with c3: rot1 = st.selectbox("Rotazione", df1['Rotazione'].unique(), key="l1_r")
        df1_r = df1[df1['Rotazione'] == rot1]
        scen_multi = st.multiselect("Scegli Scenari Rigenerativi", [s for s in df1_r['Scenario_Esteso'].unique() if "Baseline" not in s])
        
        target = ["Gestione Tradizionale (Baseline)"] + scen_multi
        # ... (Logica animazione Blu fino a 2026 come codice precedente) ...
        # [Per brevità qui inseriamo solo il concetto, il codice segue la logica "Blu sopra tutto"]
        st.info("Simulazione dinamica di tutti gli scenari scelti per la singola azienda.")

# ---------------------------------------------------------
# LIVELLO 2: UNA PROVINCIA - UNO SCENARIO - AMMENDANTE SI/NO
# ---------------------------------------------------------
with tab2:
    st.subheader("Confronto: Stessa Pratica con e senza Ammendante")
    p2 = st.selectbox("Provincia", ["Cremona", "Mantova", "Piacenza"], key="l2_p")
    df_si = get_df(p2, "Sì")
    df_no = get_df(p2, "No")
    
    if df_si is not None and df_no is not None:
        rot2 = st.selectbox("Rotazione", df_si['Rotazione'].unique(), key="l2_r")
        scen_unico = st.selectbox("Scenario da testare", [s for s in df_si['Scenario_Esteso'].unique() if "Baseline" not in s], key="l2_s")
        
        # Qui uniamo i dati dei due file per mostrare 4 linee: 
        # Baseline SI/NO e Scenario SI/NO
        st.write(f"Confronto tra l'efficacia di {scen_unico} con e senza apporto organico.")

# ---------------------------------------------------------
# LIVELLO 3: DUE COMBINAZIONI PROVINCIA-AMMENDANTE
# ---------------------------------------------------------
with tab3:
    st.subheader("Confronto Strategico tra due Siti o Gestionali")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Combinazione A**")
        pa = st.selectbox("Provincia A", ["Cremona", "Mantova", "Piacenza"])
        aa = st.radio("Ammendante A", ["Sì", "No"])
    with c2:
        st.markdown("**Combinazione B**")
        pb = st.selectbox("Provincia B", ["Cremona", "Mantova", "Piacenza"], index=1)
        ab = st.radio("Ammendante B", ["Sì", "No"])
    
    dfa = get_df(pa, aa)
    dfb = get_df(pb, ab)
    
    if dfa is not None and dfb is not None:
        scen_l3 = st.selectbox("Scenario Rigenerativo da confrontare", [s for s in dfa['Scenario_Esteso'].unique() if "Baseline" not in s])
        st.warning("Visualizzazione della traiettoria di sequestro in due contesti differenti per lo stesso scenario.")

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/b/b0/Logo_Casalasco.png", width=200) # Se hai un logo
