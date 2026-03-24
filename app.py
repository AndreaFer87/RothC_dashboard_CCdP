import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb", layout="wide")

# --- STILE CSS PER FONT GRANDI ---
st.markdown("""
    <style>
    .stSelectbox label, .stRadio label, .stMultiSelect label {
        font-size: 20px !important;
        font-weight: bold !important;
    }
    .stSelectbox div div, .stMultiSelect div div {
        font-size: 18px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🌱 Simulatore Dinamico Decarbonizzazione")
st.markdown("Relatore: **Andrea Ferrari**")

# --- FUNZIONE DECODIFICA SCENARI ---
def decode_scenario(name):
    if "Baseline" in name or "CT" in name:
        return "Gestione Tradizionale (Baseline)"
    # Sostituzioni per nomi estesi
    decoded = name.replace("CC", "Cover Crop")
    decoded = decoded.replace("MT", "Minima Lavorazione")
    decoded = decoded.replace("Res", "Residui Interrati")
    decoded = decoded.replace("+", " + ")
    return decoded

# --- CARICAMENTO DATI EXCEL ---
@st.cache_data
def load_data(provincia, scelta_amm):
    files = {
        "Cremona": {"Sì": "Cremona_digestate.xlsx", "No": "Cremona_NOdigestate.xlsx"},
        "Mantova": {"Sì": "Mantova_slurry.xlsx", "No": "Mantova_NOslurry.xlsx"},
        "Piacenza": {"Sì": "Piacenza_manure.xlsx", "No": "Piacenza_NOmanure.xlsx"}
    }
    file_name = files[provincia][scelta_amm]
    try:
        # Nota: Assicurati che i file siano .xlsx e non .csv su GitHub
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df['Scenario_Esteso'] = df['Scenario'].apply(decode_scenario)
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
    scenari_estesi = df_rot['Scenario_Esteso'].unique().tolist()
    baseline_estesa = [s for s in scenari_estesi if "Baseline" in s][0]
    
    scenari_sim_estesi = st.multiselect(
        "✨ Scegli le Pratiche Rigenerative da confrontare", 
        [s for s in scenari_estesi if s != baseline_estesa]
    )

    # --- LOGICA DEI FRAME ---
    scenari_attivi = [baseline_estesa] + scenari_sim_estesi
    animation_list = []
    
    for m in range(1, 121, 3):
        for scen in scenari_attivi:
            if scen == baseline_estesa:
                temp = df_rot[(df_rot['Scenario_Esteso'] == scen) & (df_rot['Mese_Progressivo'] <= m)].copy()
            else:
                if m < 60:
                    # Copia la baseline fino al 2026 per evitare che la linea parta da zero
                    temp = df_rot[(df_rot['Scenario_Esteso'] == baseline_estesa) & (df_rot['Mese_Progressivo'] <= m)].copy()
                    temp['Scenario_Esteso'] = scen 
                else:
                    # Dati reali dello scenario
                    temp = df_rot[(df_rot['Scenario_Esteso'] == scen) & (df_rot['Mese_Progressivo'] <= m)].copy()
            
            temp['Frame'] = m
            animation_list.append(temp)
    
    df_anim = pd.concat(animation_list)

    # --- GRAFICO ---
    # Mappa colori: Baseline BLU, gli altri colori automatici di Plotly
    color_map = {baseline_estesa: "#0000FF"}
    
    fig = px.line(
        df_anim, 
        x='Data', 
        y='total_soc', 
        color='Scenario_Esteso',
        animation_frame='Frame',
        range_x=[df_rot['Data'].min(), df_rot['Data'].max()],
        range_y=[df_rot['total_soc'].min()*0.95, df_rot['total_soc'].max()*1.05],
        title=f"Proiezione Stock Carbonio - {rot_scelta}",
        labels={'total_soc': 'Stock di C (ton/ha)', 'Data': 'Anno', 'Scenario_Esteso': 'Pratica'},
        color_discrete_map=color_map,
        template="plotly_white"
    )

    # Configurazione PLAY sotto il grafico
    fig.layout.updatemenus = [dict(
        type="buttons", showactive=False, x=0, y=-0.25,
        buttons=[dict(label="▶ AVVIA SIMULAZIONE 2021-2031", method="animate", 
                 args=[None, {"frame": {"duration": 40, "redraw": False}, "fromcurrent": True}])]
    )]
    fig.layout.sliders = [dict(visible=False)]
    
    # Linea verticale 2026
    split_date = pd.to_datetime("2026-01-01")
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper", 
                  line=dict(color="Red", width=2, dash="dot"))
    
    # CORREZIONE ERRORE: yshift invece di ysift
    fig.add_annotation(x=split_date, y=df_rot['total_soc'].max(), 
                       text="Inizio Pratiche Rigenerative", 
                       showarrow=False, yshift=15)

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- TABELLA RIASSUNTIVA ---
    st.divider()
    st.subheader("📊 Risultati attesi al 2031")
    ultimi_dati = df_rot[(df_rot['Mese_Progressivo'] == 120) & (df_rot['Scenario_Esteso'].isin(scenari_attivi))]
    
    st.dataframe(
        ultimi_dati[['Scenario_Esteso', 'total_soc', 'Input_C_Totale']]
        .rename(columns={'total_soc': 'Stock C finale (ton/ha)', 'Input_C_Totale': 'Input C (ton/ha/anno)'})
        .style.highlight_max(subset=['Stock C finale (ton/ha)'], color='#d4edda'),
        use_container_width=True
    )
