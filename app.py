import streamlit as st
import pandas as pd
import plotly.express as px
import time

st.set_page_config(page_title="Casalasco Decarb", layout="wide")

st.title("🌱 Simulatore Dinamico Decarbonizzazione")
st.markdown("Relatore: **Andrea Ferrari** | Analisi evolutiva SOC Stock")

# --- CARICAMENTO DATI EXCEL (.xlsx) ---
@st.cache_data
def load_data(provincia, scelta_amm):
    files = {
        "Cremona": {"Sì": "Cremona_digestate.xlsx", "No": "Cremona_NOdigestate.xlsx"},
        "Mantova": {"Sì": "Mantova_slurry.xlsx", "No": "Mantova_NOslurry.xlsx"},
        "Piacenza": {"Sì": "Piacenza_manure.xlsx", "No": "Piacenza_NOmanure.xlsx"}
    }
    file_name = files[provincia][scelta_amm]
    try:
        # Carichiamo Excel direttamente
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        return df
    except Exception as e:
        st.error(f"Errore caricamento {file_name}: {e}")
        return None

# --- SIDEBAR ---
st.sidebar.header("1. Configurazione")
prov = st.sidebar.selectbox("Provincia", ["Cremona", "Mantova", "Piacenza"])
amm_label = {"Cremona": "Digestato", "Mantova": "Slurry", "Piacenza": "Letame"}
amm_scelta = st.sidebar.radio(f"Uso di {amm_label[prov]}?", ["Sì", "No"])

df = load_data(prov, amm_scelta)

if df is not None:
    rot_scelta = st.sidebar.selectbox("Rotazione", df['Rotazione'].unique())
    df_rot = df[df['Rotazione'] == rot_scelta].copy()
    
    scenari_totali = df_rot['Scenario'].unique().tolist()
    baseline_nome = [s for s in scenari_totali if any(x in s for x in ['Baseline', 'CT'])][0]
    
    st.sidebar.header("2. Scenari Rigenerativi")
    scenari_sim = st.sidebar.multiselect("Scegli scenari da confrontare", [s for s in scenari_totali if s != baseline_nome])

    st.sidebar.divider()
    # Tasto Streamlit per avviare
    run_sim = st.sidebar.button("▶️ PLAY AVVIA SIMULAZIONE")
    velocita = st.sidebar.select_slider("Velocità", options=[0.5, 0.3, 0.1, 0.05, 0.02], value=0.05)

    # Placeholder per il grafico
    chart_placeholder = st.empty()

    # Funzione per generare il grafico a un dato mese
    def get_fig(m):
        df_base = df_rot[(df_rot['Scenario'] == baseline_nome) & (df_rot['Mese_Progressivo'] <= m)]
        df_scen = pd.DataFrame()
        if m >= 60:
            df_scen = df_rot[(df_rot['Scenario'].isin(scenari_sim)) & 
                            (df_rot['Mese_Progressivo'] <= m) & 
                            (df_rot['Mese_Progressivo'] >= 60)]
        
        df_viz = pd.concat([df_base, df_scen])
        
        fig = px.line(
            df_viz, x='Data', y='total_soc', color='Scenario',
            range_x=[df_rot['Data'].min(), df_rot['Data'].max()],
            range_y=[df_rot['total_soc'].min()*0.98, df_rot['total_soc'].max()*1.02],
            labels={'total_soc': 'Stock di C (ton/ha)', 'Data': 'Anno'},
            template="plotly_white"
        )
        # Linea verticale Gennaio 2026
        split_date = pd.to_datetime("2026-01-01")
        fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper",
                      line=dict(color="Red", width=1, dash="dot"))
        
        # Nascondiamo i controlli di Plotly per pulizia
        fig.update_layout(showlegend=True, hovermode="x unified")
        return fig

    # LOGICA DI SIMULAZIONE
    if run_sim:
        # Animazione tramite loop (sovrascrive il placeholder senza flash)
        for m in range(1, 121, 2):
            chart_placeholder.plotly_chart(get_fig(m), use_container_width=True)
            time.sleep(velocita)
        # Assicura frame finale
        chart_placeholder.plotly_chart(get_fig(120), use_container_width=True)
    else:
        # Stato iniziale: fermo al "presente" (mese 60)
        chart_placeholder.plotly_chart(get_fig(60), use_container_width=True)

    # --- TABELLA RISULTATI FINALI ---
    st.divider()
    st.subheader("Analisi Stock Finale (2031)")
    ultimi_dati = df_rot[df_rot['Mese_Progressivo'] == 120]
    scen_scelti = [baseline_nome] + scenari_sim
    df_tab = ultimi_dati[ultimi_dati['Scenario'].isin(scen_scelti)]
    
    st.dataframe(df_tab[['Scenario', 'total_soc', 'Input_C_Totale']].style.highlight_max(subset=['total_soc'], color='#d4edda'))
