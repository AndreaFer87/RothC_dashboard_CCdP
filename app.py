import streamlit as st
import pandas as pd
import plotly.express as px

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
    scenari_sim = st.sidebar.multiselect("Scegli scenari", [s for s in scenari_totali if s != baseline_nome])

    # --- PREPARAZIONE DATI PER ANIMAZIONE NATIVA ---
    # Creiamo i frame per Plotly: dal mese 1 al 120
    animation_list = []
    step = 3 # Step per fluidità senza appesantire il browser
    for m in range(1, 121, step):
        # Baseline (0-m)
        temp_base = df_rot[(df_rot['Scenario'] == baseline_nome) & (df_rot['Mese_Progressivo'] <= m)].copy()
        # Scenari Rigenerativi (60-m)
        if m >= 60:
            temp_scen = df_rot[(df_rot['Scenario'].isin(scenari_sim)) & 
                               (df_rot['Mese_Progressivo'] <= m) & 
                               (df_rot['Mese_Progressivo'] >= 60)].copy()
            temp_df = pd.concat([temp_base, temp_scen])
        else:
            temp_df = temp_base
        
        temp_df['Mese_Frame'] = m
        animation_list.append(temp_df)
    
    df_anim = pd.concat(animation_list)

    # --- CREAZIONE GRAFICO CON LOGICA SLIDER NATIVO ---
    fig = px.line(
        df_anim, 
        x='Data', 
        y='total_soc', 
        color='Scenario',
        animation_frame='Mese_Frame',
        range_x=[df_rot['Data'].min(), df_rot['Data'].max()],
        range_y=[df_rot['total_soc'].min()*0.98, df_rot['total_soc'].max()*1.02],
        title=f"Evoluzione SOC Stock: {rot_scelta}",
        labels={'total_soc': 'Stock di C (ton/ha)', 'Data': 'Anno'},
        template="plotly_white"
    )

    # TRUCCO: Configuriamo l'animazione ma NASCONDIAMO i controlli grafici
    fig.layout.updatemenus = [dict(
        type="buttons",
        showactive=False,
        x=0.05, y=-0.15, # Spostati fuori dal grafico
        buttons=[dict(label="Play", method="animate", args=[None, {"frame": {"duration": 40, "redraw": False}, "fromcurrent": True, "transition": {"duration": 0}}])]
    )]

    # Nascondiamo lo slider nativo (quello grigio brutto)
    fig.layout.sliders = [dict(visible=False)]
    
    # Linea 2026
    split_date = pd.to_datetime("2026-01-01")
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper", line=dict(color="Red", width=1, dash="dot"))

    # --- TASTO PLAY STREAMLIT ---
    # Per far partire l'animazione nativa al click del tasto Streamlit,
    # usiamo il parametro 'auto_play' nel momento in cui viene renderizzato.
    st.sidebar.divider()
    autostart = st.sidebar.button("▶️ PLAY AVVIA SIMULAZIONE")

    # Visualizzazione
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    if autostart:
        st.info("Simulazione avviata. Nota: Per motivi tecnici di Streamlit, l'animazione nativa si attiva interagendo con il tasto interno di Plotly se presente, oppure ricaricando i frame.")
        # Poiché Streamlit non può "cliccare" un tasto JS in Plotly, il modo migliore 
        # per restare fluidi senza slider è mostrare il tasto Play di Plotly piccolo e pulito.
        # Ho riabilitato il tasto Play di Plotly ma rimpicciolito sotto.
        fig.update_layout(updatemenus=[dict(visible=True, type="buttons", buttons=[dict(label="▶ AVVIA", method="animate", args=[None, {"frame": {"duration": 30, "redraw": False}, "fromcurrent": True}])])])
        st.rerun()

    # --- TABELLA FINALE ---
    st.divider()
    ultimi_dati = df_rot[df_rot['Mese_Progressivo'] == 120]
    scenari_scelti = [baseline_nome] + scenari_sim
    st.dataframe(ultimi_dati[ultimi_dati['Scenario'].isin(scenari_scelti)][['Scenario', 'total_soc', 'Input_C_Totale']])
