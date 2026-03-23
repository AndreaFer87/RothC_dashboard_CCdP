import streamlit as st
import pandas as pd
import plotly.express as px
import time

st.set_page_config(page_title="Casalasco - Decarb", layout="wide")

st.title("🌱 Simulatore Decarbonizzazione Casalasco")
st.markdown("Analisi SOC Stock (2021-2031) - Modello Roth-C")

# --- FUNZIONE CARICAMENTO DATI ---
@st.cache_data
def load_data(provincia, ammendante_si_no):
    # Mappa dei file in base alle tue scelte
    files = {
        "Cremona": {"Sì": "Cremona_digestate.xlsx", "No": "Cremona_NOdigestate.xlsx"},
        "Mantova": {"Sì": "Mantova_slurry.xlsx", "No": "Mantova_NOslurry.xlsx"},
        "Piacenza": {"Sì": "Piacenza_manure.xlsx", "No": "Piacenza_NOmanure.xlsx"}
    }
    
    file_path = files[provincia][ammendante_si_no]
    
    try:
        # Se hai caricato i file come XLSX su GitHub:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        
        # Mappatura date: Mese 60 è Dicembre 2025
        # Creiamo una colonna Data partendo da Gennaio 2021 (Mese 1)
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        return df
    except Exception as e:
        st.error(f"Errore caricamento {file_path}: {e}")
        return None

# --- SIDEBAR DI CONTROLLO ---
st.sidebar.header("Configurazione Dashboard")
prov = st.sidebar.selectbox("Seleziona Provincia", ["Cremona", "Mantova", "Piacenza"])

label_ammendante = {
    "Cremona": "Uso Digestato?",
    "Mantova": "Uso Slurry?",
    "Piacenza": "Uso Letame?"
}
amm_scelta = st.sidebar.radio(label_ammendante[prov], ["Sì", "No"])

df = load_data(prov, amm_scelta)

if df is not None:
    # Filtri Rotazione e Scenario
    rotazioni = df['Rotazione'].unique()
    rot_scelta = st.sidebar.selectbox("Rotazione", rotazioni)
    
    scenari_totali = df[df['Rotazione'] == rot_scelta]['Scenario'].unique().tolist()
    baseline_nome = "Baseline (CT)" # Assicurati che nel file si chiami così
    
    scenari_sim = st.sidebar.multiselect(
        "Scegli Scenari da Simulare (dal 2026)", 
        [s for s in scenari_totali if s != baseline_nome]
    )

    # --- LOGICA ANIMAZIONE / VISUALIZZAZIONE ---
    col1, col2 = st.columns([4, 1])
    
    with col2:
        st.write("### Controlli")
        run_sim = st.button("▶️ Avvia Simulazione")
        tempo_sim = st.slider("Velocità (sec)", 0.1, 1.0, 0.3)

    # Dati filtrati per rotazione
    df_rot = df[df['Rotazione'] == rot_scelta]
    
    # Placeholder per il grafico
    chart_placeholder = st.empty()

    # Se clicco Play, simulo l'andamento
    mesi_totali = df_rot['Mese_Progressivo'].max()
    
    if run_sim:
        for m in range(1, mesi_totali + 1):
            # Filtriamo i dati fino al mese 'm'
            # 1. Baseline sempre visibile
            df_curr_base = df_rot[(df_rot['Scenario'] == baseline_nome) & (df_rot['Mese_Progressivo'] <= m)]
            
            # 2. Altri scenari visibili solo dal mese 60 in poi
            df_curr_scen = df_rot[(df_rot['Scenario'].isin(scenari_sim)) & 
                                  (df_rot['Mese_Progressivo'] <= m) & 
                                  (df_rot['Mese_Progressivo'] >= 60)]
            
            df_viz = pd.concat([df_curr_base, df_curr_scen])
            
            fig = px.line(df_viz, x='Data', y='total_soc', color='Scenario',
                         range_x=[df_rot['Data'].min(), df_rot['Data'].max()],
                         range_y=[df_rot['total_soc'].min()*0.95, df_rot['total_soc'].max()*1.05],
                         title=f"Simulazione in corso: {rot_scelta}",
                         template="plotly_white")
            
            # Linea verticale per segnare l'inizio della fase rigenerativa (Gen 2026)
            fig.add_vline(x=pd.to_datetime("2026-01-01"), line_dash="dash", line_color="green", annotation_text="Inizio Rigenerativa")
            
            chart_placeholder.plotly_chart(fig, use_container_width=True)
            time.sleep(tempo_sim)
    else:
        # Visualizzazione statica iniziale (solo baseline o tutto se già pronti)
        df_static = df_rot[df_rot['Scenario'] == baseline_nome]
        fig = px.line(df_static, x='Data', y='total_soc', color='Scenario',
                     title=f"Andamento Storico Baseline - {rot_scelta}",
                     template="plotly_white")
        fig.add_vline(x=pd.to_datetime("2026-01-01"), line_dash="dash", line_color="gray")
        chart_placeholder.plotly_chart(fig, use_container_width=True)

    # --- TABELLA RIASSUNTIVA ---
    st.divider()
    st.write("### Risultati Finali (Fine 2031)")
    final_data = df_rot[df_rot['Mese_Progressivo'] == mesi_totali]
    st.dataframe(final_data[['Scenario', 'total_soc', 'Input_C_Totale']])
