import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb", layout="wide")

# --- STILE CSS PER FONT GRANDI ---
st.markdown("""
    <style>
    .stSelectbox label, .stRadio label, .stMultiSelect label {
        font-size: 22px !important;
        font-weight: bold !important;
        color: #1E3A8A;
    }
    .stSelectbox div div, .stMultiSelect div div {
        font-size: 18px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🌱 Simulatore Dinamico Decarbonizzazione")
st.markdown("Relatore: **Andrea Ferrari**")

# --- NUOVA FUNZIONE DECODIFICA SCENARI (PRECISA) ---
def decode_scenario_exact(name):
    name = name.strip()
    # Mappatura esatta come richiesto
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
    return mapping.get(name, name)

# --- CARICAMENTO DATI ---
@st.cache_data
def load_data(provincia, scelta_amm):
    files = {
        "Cremona": {"Sì": "Cremona_digestate.xlsx", "No": "Cremona_NOdigestate.xlsx"},
        "Mantova": {"Sì": "Mantova_slurry.xlsx", "No": "Mantova_NOslurry.xlsx"},
        "Piacenza": {"Sì": "Piacenza_manure.xlsx", "No": "Piacenza_NOmanure.xlsx"}
    }
    file_name = files[provincia][scelta_amm]
    try:
        # Carichiamo Excel
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        # Creiamo la colonna con i nomi corretti
        df['Scenario_Esteso'] = df['Scenario'].apply(decode_scenario_exact)
        return df
    except Exception as e:
        st.error(f"Errore caricamento {file_name}: {e}")
        return None

# --- FILTRI ORIZZONTALI ---
col_a, col_b, col_c = st.columns(3)
with col_a:
    prov = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"])
with col_b:
    amm_label = {"Cremona": "Digestato", "Mantova": "Slurry", "Piacenza": "Letame"}
    amm_scelta = st.radio(f"Uso di {amm_label[prov]}?", ["Sì", "No"], horizontal=True)
with col_c:
    df = load_data(prov, amm_scelta)
    if df is not None:
        rot_scelta = st.selectbox("🚜 Rotazione Agricola", df['Rotazione'].unique())

if df is not None:
    df_rot = df[df['Rotazione'] == rot_scelta].copy()
    
    # Identifichiamo la baseline
    baseline_estesa = "Gestione Tradizionale (Baseline)"
    
    # Lista scenari disponibili (esclusa la baseline)
    opzioni_scenari = [s for s in df_rot['Scenario_Esteso'].unique() if s != baseline_estesa]
    
    scenari_sim_estesi = st.multiselect(
        "✨ Seleziona Scenari Rigenerativi da confrontare col la Baseline", 
        opzioni_scenari
    )

    # --- LOGICA DEI FRAME ---
    scenari_attivi = [baseline_estesa] + scenari_sim_estesi
    animation_list = []
    
    for m in range(1, 121, 3):
        for scen in scenari_attivi:
            if scen == baseline_estesa:
                # La baseline segue sempre i suoi dati
                temp = df_rot[(df_rot['Scenario_Esteso'] == scen) & (df_rot['Mese_Progressivo'] <= m)].copy()
            else:
                # Gli scenari rigenerativi:
                if m < 60:
                    # Fino al 2026 ricalcano esattamente la baseline (linea blu unica)
                    temp = df_rot[(df_rot['Scenario_Esteso'] == baseline_estesa) & (df_rot['Mese_Progressivo'] <= m)].copy()
                    temp['Scenario_Esteso'] = scen 
                else:
                    # Dal 2026 prendono i loro dati reali
                    temp = df_rot[(df_rot['Scenario_Esteso'] == scen) & (df_rot['Mese_Progressivo'] <= m)].copy()
            
            temp['Frame'] = m
            animation_list.append(temp)
    
    df_anim = pd.concat(animation_list)

    # --- GRAFICO ---
    # Baseline sempre Blu, gli altri colori a rotazione
    color_map = {baseline_estesa: "#0000FF"}
    
    fig = px.line(
        df_anim, 
        x='Data', 
        y='total_soc', 
        color='Scenario_Esteso',
        animation_frame='Frame',
        range_x=[df_rot['Data'].min(), df_rot['Data'].max()],
        range_y=[df_rot['total_soc'].min()*0.98, df_rot['total_soc'].max()*1.05],
        title=f"Evoluzione Stock Carbonio (SOC): {rot_scelta}",
        labels={'total_soc': 'Stock di C (ton/ha)', 'Data': 'Anno', 'Scenario_Esteso': 'Scenario'},
        color_discrete_map=color_map,
        template="plotly_white"
    )

    # Tasto Play e Slider
    fig.layout.updatemenus = [dict(
        type="buttons", showactive=False, x=0, y=-0.2,
        buttons=[dict(label="▶ AVVIA SIMULAZIONE", method="animate", 
                 args=[None, {"frame": {"duration": 50, "redraw": False}, "fromcurrent": True}])]
    )]
    fig.layout.sliders = [dict(visible=False)]
    
    # Linea verticale 2026
    split_date = pd.to_datetime("2026-01-01")
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper", 
                  line=dict(color="Red", width=2, dash="dot"))
    
    fig.add_annotation(x=split_date, y=df_rot['total_soc'].max(), 
                       text="Bivio Strategico 2026", 
                       showarrow=False, yshift=15, font=dict(color="Red", size=14))

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- TABELLA RISULTATI FINALI ---
    st.divider()
    st.subheader("📊 Analisi Carbonio al 2031")
    ultimi_dati = df_rot[(df_rot['Mese_Progressivo'] == 120) & (df_rot['Scenario_Esteso'].isin(scenari_attivi))]
    
    st.dataframe(
        ultimi_dati[['Scenario_Esteso', 'total_soc', 'Input_C_Totale']]
        .rename(columns={'Scenario_Esteso': 'Scenario', 'total_soc': 'Stock Finale (ton/ha)', 'Input_C_Totale': 'Input C (ton/anno)'})
        .style.highlight_max(subset=['Stock Finale (ton/ha)'], color='#d4edda'),
        use_container_width=True
    )
