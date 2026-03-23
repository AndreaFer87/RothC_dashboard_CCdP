import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configurazione Pagina (Deve essere la prima istruzione Streamlit)
st.set_page_config(page_title="Casalasco - Decarb", layout="wide")

st.title("🌱 Agricoltura Rigenerativa: Modelli Decisionali")
st.markdown("Analisi sequestro del carbonio - Modello Roth-C")

# 2. Funzione Caricamento Dati "Indistruttibile"
@st.cache_data
def load_data():
    try:
        # Carichiamo il file con rilevazione automatica del separatore e codifica corretta
        df = pd.read_csv("Cremona_digestate.csv", sep=None, engine='python', encoding='latin-1', on_bad_lines='skip')
        return df
    except Exception as e:
        st.error(f"Errore nel caricamento file: {e}")
        return None

df = load_data()

# 3. Logica Dashboard (solo se il file è stato caricato correttamente)
if df is not None:
    # Sidebar per filtri
    st.sidebar.header("Parametri")
    
    # Selezione Rotazione
    rotazione = st.sidebar.selectbox("Seleziona Rotazione", df['Rotazione'].unique())
    df_rot = df[df['Rotazione'] == rotazione]

    # Selezione Scenari
    tutti_scenari = df_rot['Scenario'].unique().tolist()
    baseline = st.sidebar.selectbox("Scenario Baseline", tutti_scenari)
    scenari_extra = st.sidebar.multiselect("Confronta con Scenari Rigenerativi", 
                                          [s for s in tutti_scenari if s != baseline])

    # Plotting
    lista_scenari = [baseline] + scenari_extra
    df_plot = df_rot[df_rot['Scenario'].isin(lista_scenari)]

    if not df_plot.empty:
        fig = px.line(df_plot, x='Mese_Progressivo', y='total_soc', color='Scenario',
                     title=f"Evoluzione SOC Stock - {rotazione}",
                     labels={'total_soc': 'Carbonio nel suolo (Mg C/ha)', 'Mese_Progressivo': 'Mesi'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Seleziona almeno uno scenario per visualizzare il grafico.")
