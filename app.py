import streamlit as st
import pandas as pd
import plotly.express as px
import time

st.set_page_config(page_title="Casalasco Decarb", layout="wide")

st.title("🌱 Simulatore Decarbonizzazione Casalasco")
st.markdown("Analisi SOC Stock (2021-2031) - Relatore: **Andrea Ferrari**")

# --- FUNZIONE CARICAMENTO DATI ---
@st.cache_data
def load_data(provincia, scelta_amm):
    # Mappatura basata sui tuoi file caricati
    files = {
        "Cremona": {"Sì": "Cremona_digestate.xlsx - Sheet 1.csv", "No": "Cremona_NOdigestate.xlsx - Sheet 1.csv"},
        "Mantova": {"Sì": "Mantova_slurry.xlsx - Sheet 1.csv", "No": "Mantova_NOslurry.xlsx - Sheet 1.csv"},
        "Piacenza": {"Sì": "Piacenza_manure.xlsx - Sheet 1.csv", "No": "Piacenza_NOmanure.xlsx - Sheet 1.csv"}
    }
    
    file_name = files[provincia][scelta_amm]
    
    try:
        # Carichiamo il CSV
        df = pd.read_csv(file_name, sep=None, engine='python', encoding='latin-1')
        df.columns = df.columns.str.strip()
        
        # Creazione asse temporale reale (Mese 1 = Gen 2021)
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        return df
    except Exception as e:
        st.error(f"Errore caricamento {file_name}: {e}")
        return None

# --- SIDEBAR ---
st.sidebar.header("Parametri Iniziali")
prov = st.sidebar.selectbox("Provincia", ["Cremona", "Mantova", "Piacenza"])

amm_label = {"Cremona": "Digestato", "Mantova": "Slurry", "Piacenza": "Letame"}
amm_scelta = st.sidebar.radio(f"Uso di {amm_label[prov]} nella Baseline?", ["Sì", "No"])

df = load_data(prov, amm_scelta)

if df is not None:
    rot_scelta = st.sidebar.selectbox("Rotazione Agricola", df['Rotazione'].unique())
    
    df_rot = df[df['Rotazione'] == rot_scelta]
    scenari_totali = df_rot['Scenario'].unique().tolist()
    
    # Identifichiamo la baseline (solitamente contiene 'Baseline' o 'CT')
    baseline_nome = [s for s in scenari_totali if 'Baseline' in s or 'CT' in s][0]
    
    scenari_sim = st.sidebar.multiselect(
        "Seleziona Scenari Rigenerativi (dal 2026)", 
        [s for s in scenari_totali if s != baseline_nome]
    )

    # --- GRAFICO ANIMATO ---
    chart_placeholder = st.empty()
    
    st.sidebar.divider()
    run_sim = st.sidebar.button("▶️ AVVIA SIMULAZIONE")
    velocita = st.sidebar.select_slider("Velocità animazione", options=[0.5, 0.3, 0.1, 0.05], value=0.1)

    split_date = pd.to_datetime("2026-01-01")

    def plot_graph(current_month):
        # 1. Baseline: sempre visibile
        df_base = df_rot[(df_rot['Scenario'] == baseline_nome) & (df_rot['Mese_Progressivo'] <= current_month)]
        
        # 2. Altri scenari: visibili solo dal mese 60 (fine 2025)
        df_scen = pd.DataFrame()
        if current_month >= 60:
            df_scen = df_rot[(df_rot['Scenario'].isin(scenari_sim)) & 
                            (df_rot['Mese_Progressivo'] <= current_month) & 
                            (df_rot['Mese_Progressivo'] >= 60)]
        
        df_viz = pd.concat([df_base, df_scen])
        
        fig = px.line(df_viz, x='Data', y='total_soc', color='Scenario',
                     range_x=[df_rot['Data'].min(), df_rot['Data'].max()],
                     range_y=[df_rot['total_soc'].min()*0.98, df_rot['total_soc'].max()*1.02],
                     title=f"Evoluzione Carbonio nel Suolo - {rot_scelta}",
                     template="plotly_white")
        
        # Linea verticale Gennaio 2026
        fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper",
                      line=dict(color="Green", width=2, dash="dash"))
        
        chart_placeholder.plotly_chart(fig, use_container_width=True)

    if run_sim:
        for m in range(1, 121, 2):
            plot_graph(m)
            time.sleep(velocita)
        plot_graph(120)
    else:
        plot_graph(60)

    # --- TABELLA RISULTATI (Correzione Errore Linea 116) ---
    st.divider()
    st.subheader("Risultati Finali stimati al 2031")
    ultimi_dati = df_rot[df_rot['Mese_Progressivo'] == 120]
    
    # Filtriamo solo la baseline e gli scenari scelti per la tabella
    scenari_finali = [baseline_nome] + scenari_sim
    tabella_finale = ultimi_dati[ultimi_dati['Scenario'].isin(scenari_finali)]
    
    st.dataframe(
        tabella_finale[['Scenario', 'total_soc', 'Input_C_Totale']]
        .style.highlight_max(subset=['total_soc'], color='#d4edda')
    )
