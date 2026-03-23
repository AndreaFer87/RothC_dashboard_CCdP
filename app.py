import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco - Decarb", layout="wide")

st.title("🌱 Agricoltura Rigenerativa: Modelli Decisionali")
st.markdown("Analisi sequestro del carbonio - Modello Roth-C")

@st.cache_data
def load_data():
    try:
        # Caricamento flessibile: sep=None capisce da solo se è , o ;
        df = pd.read_csv("Cremona_digestate.csv", sep=None, engine='python', encoding='latin-1', on_bad_lines='skip')
        
        # PULIZIA FONDAMENTALE: rimuove spazi bianchi dai nomi delle colonne
        # Esempio: trasforma " Rotazione " in "Rotazione"
        df.columns = df.columns.str.strip()
        
        return df
    except Exception as e:
        st.error(f"Errore nel caricamento file: {e}")
        return None

df = load_data()

if df is not None:
    # Debug opzionale: scrivi i nomi delle colonne per essere sicuri
    # st.write("Colonne trovate:", df.columns.tolist()) 

    st.sidebar.header("Parametri")
    
    # Verifichiamo se la colonna esiste davvero dopo la pulizia
    nome_colonna = 'Rotazione'
    if nome_colonna in df.columns:
        rotazioni_disponibili = df[nome_colonna].unique()
        rotazione = st.sidebar.selectbox("Seleziona Rotazione", rotazioni_disponibili)
        
        df_rot = df[df[nome_colonna] == rotazione]

        # Selezione Scenari (usiamo 'Scenario' pulito)
        col_scenario = 'Scenario'
        if col_scenario in df.columns:
            tutti_scenari = df_rot[col_scenario].unique().tolist()
            baseline = st.sidebar.selectbox("Scenario Baseline", tutti_scenari)
            scenari_extra = st.sidebar.multiselect("Confronta con Scenari Rigenerativi", 
                                                  [s for s in tutti_scenari if s != baseline])

            lista_scenari = [baseline] + scenari_extra
            df_plot = df_rot[df_rot[col_scenario].isin(lista_scenari)]

            # Grafico
            if not df_plot.empty and 'total_soc' in df.columns:
                fig = px.line(df_plot, x='Mese_Progressivo', y='total_soc', color=col_scenario,
                             title=f"Evoluzione SOC Stock - {rotazione}",
                             labels={'total_soc': 'Carbonio nel suolo (Mg C/ha)', 'Mese_Progressivo': 'Mesi'},
                             template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"Colonna '{col_scenario}' non trovata. Controlla il CSV.")
    else:
        st.error(f"Colonna '{nome_colonna}' non trovata. Colonne presenti: {df.columns.tolist()}")
