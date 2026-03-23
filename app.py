import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb", layout="wide")

st.title("🌱 Simulatore Dinamico Decarbonizzazione")
st.markdown("Relatore: **Andrea Ferrari** | Analisi evolutiva SOC Stock")

# --- FUNZIONE CARICAMENTO DATI ---
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

    # --- PREPARAZIONE DATI PER ANIMAZIONE FLUIDA ---
    # Creiamo un dataframe con i frame per Plotly
    animation_list = []
    # Step 3 per bilanciare velocità e fluidità
    for m in range(1, 121, 3):
        # Baseline
        temp_base = df_rot[(df_rot['Scenario'] == baseline_nome) & (df_rot['Mese_Progressivo'] <= m)].copy()
        # Scenari rigenerativi (nascono a mese 60)
        if m >= 60:
            temp_scen = df_rot[(df_rot['Scenario'].isin(scenari_sim)) & 
                               (df_rot['Mese_Progressivo'] <= m) & 
                               (df_rot['Mese_Progressivo'] >= 60)].copy()
            temp_df = pd.concat([temp_base, temp_scen])
        else:
            temp_df = temp_base
        
        temp_df['Frame'] = m
        animation_list.append(temp_df)
    
    df_anim = pd.concat(animation_list)

    # --- CREAZIONE GRAFICO CON SLIDER NASCOSTO ---
    fig = px.line(
        df_anim, 
        x='Data', 
        y='total_soc', 
        color='Scenario',
        animation_frame='Frame',
        range_x=[df_rot['Data'].min(), df_rot['Data'].max()],
        range_y=[df_rot['total_soc'].min()*0.98, df_rot['total_soc'].max()*1.02],
        title=f"Evoluzione SOC Stock: {rot_scelta}",
        labels={'total_soc': 'Stock di C (ton/ha)', 'Data': 'Anno'},
        template="plotly_white"
    )

    # TRUCCO: Nascondiamo lo slider e i bottoni nativi di Plotly
    fig.update_layout(
        sliders=[dict(visible=False)], 
        updatemenus=[dict(visible=False)], # Nasconde il tasto Play di Plotly
        hovermode="x unified"
    )

    # Velocità dell'animazione interna
    fig.layout.updatemenus = [dict(
        type="buttons",
        buttons=[dict(label="Play", method="animate", args=[None, {"frame": {"duration": 50, "redraw": True}, "fromcurrent": True}])],
        visible=False # Nascondiamo anche questo
    )]

    # Linea verticale 2026
    split_date = pd.to_datetime("2026-01-01")
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper",
                  line=dict(color="Red", width=1, dash="dot"))

    # --- TASTO PLAY STREAMLIT ---
    # Quando l'utente preme questo tasto, Streamlit ricarica l'app con l'animazione avviata
    st.sidebar.divider()
    if st.sidebar.button("▶️ PLAY AVVIA SIMULAZIONE"):
        # Se premuto, impostiamo l'autostart dell'animazione Plotly
        fig.layout.updatemenus[0].buttons[0].args[1]['auto_play'] = True
    
    st.plotly_chart(fig, use_container_width=True)

    # --- TABELLA E DELTA ---
    st.divider()
    ultimi_dati = df_rot[df_rot['Mese_Progressivo'] == 120]
    scenari_attivi = [baseline_nome] + scenari_sim
    df_tab = ultimi_dati[ultimi_dati['Scenario'].isin(scenari_attivi)]
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Stock finale al 2031")
        st.dataframe(df_tab[['Scenario', 'total_soc', 'Input_C_Totale']].style.highlight_max(subset=['total_soc']))
    
    with col2:
        if scenari_sim:
            v_base = ultimi_dati[ultimi_dati['Scenario'] == baseline_nome]['total_soc'].values[0]
            for s in scenari_sim:
                v_scen = ultimi_dati[ultimi_dati['Scenario'] == s]['total_soc'].values[0]
                st.metric(f"Guadagno {s}", f"{v_scen - v_base:.2f} ton/ha")
