import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb", layout="wide")

st.title("🌱 Simulatore Dinamico Decarbonizzazione")
st.markdown("Relatore: **Andrea Ferrari** | Analisi evolutiva SOC Stock")

# --- CARICAMENTO DATI ---
@st.cache_data
def load_data(provincia, scelta_amm):
    # Assicurati che i file su GitHub siano .xlsx
    files = {
        "Cremona": {"Sì": "Cremona_digestate.xlsx", "No": "Cremona_NOdigestate.xlsx"},
        "Mantova": {"Sì": "Mantova_slurry.xlsx", "No": "Mantova_NOslurry.xlsx"},
        "Piacenza": {"Sì": "Piacenza_manure.xlsx", "No": "Piacenza_NOmanure.xlsx"}
    }
    file_name = files[provincia][scelta_amm]
    try:
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        # Creazione asse temporale
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
    scenari_sim = st.sidebar.multiselect("Scegli scenari", [s for s in scenari_totali if s != baseline_nome])

    # --- PREPARAZIONE DATI PER ANIMAZIONE FLUIDA ---
    scenari_finali = [baseline_nome] + scenari_sim
    
    # Creiamo un dataframe "cumulativo" per l'animazione
    # Ogni frame 'f' contiene tutti i dati dal mese 0 al mese 'f'
    animation_frames = []
    
    # Per non appesantire troppo, animiamo ogni 3 mesi (step=3)
    step = 3
    for m in range(1, 121, step):
        # Filtro baseline (sempre presente da 0 a m)
        temp_df = df_rot[(df_rot['Scenario'] == baseline_nome) & (df_rot['Mese_Progressivo'] <= m)].copy()
        
        # Filtro scenari scelti (presenti solo se m > 60 e solo per la loro porzione)
        if m > 60:
            df_scen = df_rot[(df_rot['Scenario'].isin(scenari_sim)) & 
                            (df_rot['Mese_Progressivo'] <= m) & 
                            (df_rot['Mese_Progressivo'] >= 60)].copy()
            temp_df = pd.concat([temp_df, df_scen])
        
        temp_df['Frame'] = m  # Identificativo del frame temporale
        animation_frames.append(temp_df)
    
    df_anim = pd.concat(animation_frames)

    # --- CREAZIONE GRAFICO ANIMATO (NATIVO PLOTLY) ---
    fig = px.line(
        df_anim, 
        x='Data', 
        y='total_soc', 
        color='Scenario',
        animation_frame='Frame', # Questa è la chiave per eliminare il flash
        range_x=[df_rot['Data'].min(), df_rot['Data'].max()],
        range_y=[df_rot['total_soc'].min()*0.98, df_rot['total_soc'].max()*1.02],
        title=f"Evoluzione SOC Stock: {rot_scelta}",
        template="plotly_white"
    )

    # Miglioriamo la velocità dell'animazione
    fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 50 # millisecondi
    fig.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 20

    # Linea verticale fissa al 2026
    split_date = pd.to_datetime("2026-01-01")
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper",
                  line=dict(color="Red", width=1, dash="dot"))

    st.plotly_chart(fig, use_container_width=True)

    st.info("💡 Clicca sul tasto 'Play' in basso a sinistra nel grafico per avviare la simulazione temporale.")

    # --- TABELLA RIASSUNTIVA ---
    st.divider()
    st.subheader("Confronto Stock Finale (2031)")
    ultimi_dati = df_rot[(df_rot['Mese_Progressivo'] == 120) & (df_rot['Scenario'].isin(scenari_finali))]
    
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(ultimi_dati[['Scenario', 'total_soc', 'Input_C_Totale']])
    with col2:
        val_base = ultimi_dati[ultimi_dati['Scenario'] == baseline_nome]['total_soc'].values[0]
        for s in scenari_sim:
            val_scen = ultimi_dati[ultimi_dati['Scenario'] == s]['total_soc'].values[0]
            st.metric(f"Incremento con {s}", f"{val_scen - val_base:.2f} Mg/ha")
