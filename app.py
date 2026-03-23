import streamlit as st
import pandas as pd
import plotly.express as px

# Configurazione pagina
st.set_page_config(page_title="Casalasco Decarb", layout="wide")

st.title("🌱 Decarbonizzazione Filiera Casalasco")
st.markdown("Analisi SOC Stock basata su modello **Roth-C**")

# Funzione caricamento dati
@st.cache_data
def load_data():
    # Proviamo a leggere il file gestendo separatore, codifica e potenziali errori di riga
    try:
        # Usiamo 'sep=None' e 'engine=python' per far capire a pandas da solo se è virgola o punto e virgola
        df = pd.read_csv("Cremona_digestate.csv", sep=None, engine='python', encoding='latin-1', on_bad_lines='skip')
        return df
    except Exception as e:
        st.error(f"Errore critico: {e}")
        return None

df = load_data()

    # Sidebar
    st.sidebar.header("Parametri")
    
    # 1. Scelta Rotazione
    rotazione = st.sidebar.selectbox("Seleziona Rotazione", df['Rotazione'].unique())
    df_rot = df[df['Rotazione'] == rotazione]

    # 2. Scelta Baseline e Scenari
    tutti_scenari = df_rot['Scenario'].unique().tolist()
    baseline = st.sidebar.selectbox("Baseline (Riferimento)", tutti_scenari)
    
    scenari_confronto = st.sidebar.multiselect(
        "Seleziona Scenari Rigenerativi da confrontare",
        [s for s in tutti_scenari if s != baseline],
        default=[tutti_scenari[1]] if len(tutti_scenari) > 1 else None
    )

    # Filtro dati
    scenari_finali = [baseline] + scenari_confronto
    df_plot = df_rot[df_rot['Scenario'].isin(scenari_finali)]

    # Layout a Colonne per i Grafici
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Andamento SOC Stock: {rotazione}")
        fig = px.line(df_plot, 
                     x='Mese_Progressivo', 
                     y='total_soc', 
                     color='Scenario',
                     labels={'total_soc': 'SOC (Mg C/ha)', 'Mese_Progressivo': 'Mesi'},
                     template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Confronto Input C Totale")
        # Media annua degli input di carbonio per scenario
        df_input = df_plot.groupby('Scenario')['Input_C_Totale'].mean().reset_index()
        fig_bar = px.bar(df_input, x='Scenario', y='Input_C_Totale', color='Scenario')
        st.plotly_chart(fig_bar, use_container_width=True)

    # Tabella riassuntiva finale
    st.divider()
    st.subheader("Risultati al termine della simulazione")
    ultimi_dati = df_plot[df_plot['Mese_Progressivo'] == df_plot['Mese_Progressivo'].max()]
    st.dataframe(ultimi_dati[['Scenario', 'total_soc', 'Input_C_Totale']].style.highlight_max(axis=0))

except Exception as e:
    st.error(f"Errore nel caricamento file: {e}")
    st.info("Verifica che il nome del file CSV nella cartella sia esattamente quello indicato nel codice.")
