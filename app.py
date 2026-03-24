import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb", layout="wide")

# --- STILE CSS PER TESTI GRANDI ---
st.markdown("""
    <style>
    .stSelectbox label, .stRadio label, .stMultiSelect label { font-size: 22px !important; font-weight: bold !important; color: #1E3A8A; }
    .stSelectbox div div, .stMultiSelect div div { font-size: 18px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🌱 Simulatore Dinamico Decarbonizzazione")

# --- MAPPATURA SCENARI ---
def decode_scenario_exact(name):
    mapping = {
        "Baseline (CT)": "Gestione Tradizionale (Baseline)",
        "CC (CT)": "Cover crop (CT)",
        "Res (CT)": "Residui (CT)",
        "CC + Res (CT)": "Cover + Residui (Tradizionale)",
        "MT": "Minima Lavorazione",
        "MT + Res": "Minima + Residui",
        "MT + CC": "Minima + Cover",
        "MT + CC + Res": "Minima + Cover + Residui"
    }
    return mapping.get(name.strip(), name.strip())

@st.cache_data
def load_data(provincia, scelta_amm):
    files = {
        "Cremona": {"Sì": "Cremona_digestate.xlsx", "No": "Cremona_NOdigestate.xlsx"},
        "Mantova": {"Sì": "Mantova_slurry.xlsx", "No": "Mantova_NOslurry.xlsx"},
        "Piacenza": {"Sì": "Piacenza_manure.xlsx", "No": "Piacenza_NOmanure.xlsx"}
    }
    file_name = files[provincia][scelta_amm]
    try:
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df['Scenario_Esteso'] = df['Scenario'].apply(decode_scenario_exact)
        return df
    except Exception as e:
        st.error(f"Errore: {e}")
        return None

# --- FILTRI ORIZZONTALI ---
col1, col2, col3 = st.columns(3)
with col1: prov = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"])
with col2:
    amm_label = {"Cremona": "Digestato", "Mantova": "Slurry", "Piacenza": "Letame"}
    amm_scelta = st.radio(f"Uso di {amm_label[prov]}?", ["Sì", "No"], horizontal=True)
with col3:
    df = load_data(prov, amm_scelta)
    if df is not None: rot_scelta = st.selectbox("🚜 Rotazione", df['Rotazione'].unique())

if df is not None:
    df_rot = df[df['Rotazione'] == rot_scelta].copy()
    baseline_nome = "Gestione Tradizionale (Baseline)"
    
    # Lista dinamica degli scenari presenti nel file
    opzioni = [s for s in df_rot['Scenario_Esteso'].unique() if s != baseline_nome]
    scenari_sim = st.multiselect("✨ Seleziona Pratiche Rigenerative (dal 2026)", opzioni)

    # --- LOGICA FRAME (TRUCCO PER FAR VEDERE TUTTI GLI SCENARI) ---
    scenari_da_disegnare = [baseline_nome] + scenari_sim
    animation_list = []
    
    for m in range(1, 121, 3):
        for s in scenari_da_disegnare:
            if m <= 60:
                # PRIMA DEL 2026: Tutti gli scenari usano i dati della Baseline
                # Questo crea linee sovrapposte (sembra una sola) ma "registra" lo scenario nel grafico
                temp = df_rot[(df_rot['Scenario_Esteso'] == baseline_nome) & (df_rot['Mese_Progressivo'] <= m)].copy()
                temp['Scenario_Esteso'] = s 
            else:
                # DOPO IL 2026: Ognuno prende i suoi dati reali
                temp = df_rot[(df_rot['Scenario_Esteso'] == s) & (df_rot['Mese_Progressivo'] <= m)].copy()
            
            temp['Frame'] = m
            animation_list.append(temp)

    df_anim = pd.concat(animation_list)

    # --- GRAFICO ---
    color_map = {baseline_nome: "#0000FF"} # Baseline Blu

    fig = px.line(
        df_anim, x='Data', y='total_soc', color='Scenario_Esteso',
        animation_frame='Frame',
        range_x=[df_rot['Data'].min(), df_rot['Data'].max()],
        range_y=[df_rot['total_soc'].min()*0.98, df_rot['total_soc'].max()*1.05],
        title=f"Evoluzione Stock Carbonio (SOC) - {rot_scelta}",
        labels={'total_soc': 'Stock di C (ton/ha)', 'Scenario_Esteso': 'Pratica Agricola'},
        color_discrete_map=color_map,
        template="plotly_white"
    )

    # UI: Tasto Play sotto, slider rimosso
    fig.layout.updatemenus = [dict(
        type="buttons", showactive=False, x=0, y=-0.2,
        buttons=[dict(label="▶ AVVIA SIMULAZIONE 2021-2031", method="animate", 
                 args=[None, {"frame": {"duration": 40, "redraw": False}, "fromcurrent": True}])]
    )]
    fig.layout.sliders = [dict(visible=False)]
    
    # Linea rossa 2026
    split_date = pd.to_datetime("2026-01-01")
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper", line=dict(color="Red", width=2, dash="dot"))
    fig.add_annotation(x=split_date, y=df_rot['total_soc'].max(), text="Inizio Rigenerazione", showarrow=False, yshift=15)

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- TABELLA RIASSUNTIVA ---
    st.divider()
    st.subheader("📊 Confronto Risultati al 2031")
    ultimi = df_rot[(df_rot['Mese_Progressivo'] == 120) & (df_rot['Scenario_Esteso'].isin(scenari_da_disegnare))]
    st.dataframe(ultimi[['Scenario_Esteso', 'total_soc', 'Input_C_Totale']].rename(columns={'total_soc': 'SOC Finale', 'Input_C_Totale': 'Input C/anno'}))
