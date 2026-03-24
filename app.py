import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb - Pro", layout="wide")

# --- CSS PER TESTI GRANDI ---
st.markdown("""
    <style>
    .stSelectbox label, .stRadio label, .stMultiSelect label { font-size: 20px !important; font-weight: bold !important; color: #1E3A8A; }
    .stTabs [data-baseweb="tab"] { font-size: 22px !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- MAPPATURA SCENARI ---
MAPPING = {
    "Baseline (CT)": "Gestione Tradizionale (Baseline)",
    "CC (CT)": "Cover crop (CT)",
    "Res (CT)": "Residui (CT)",
    "CC + Res (CT)": "Cover + Residui (Tradizionale)",
    "MT": "Minima Lavorazione",
    "MT + Res": "Minima + Residui",
    "MT + CC": "Minima + Cover",
    "MT + CC + Res": "Minima + Cover + Residui"
}

def decode(name):
    return MAPPING.get(name.strip(), name.strip())

@st.cache_data
def load_data(provincia, scelta_amm):
    suffix = {"Cremona": "digestate", "Mantova": "slurry", "Piacenza": "manure"}[provincia]
    file_name = f"{provincia}_{suffix}.xlsx" if scelta_amm == "Sì" else f"{provincia}_NO{suffix}.xlsx"
    try:
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df['Scenario_Esteso'] = df['Scenario'].apply(decode)
        return df
    except: return None

# --- FUNZIONE LAYOUT PULITO ---
def apply_final_layout(fig, df_visualizzato, title, baseline_name, df_orig):
    # Calcolo dinamico asse Y
    y_min = df_visualizzato['total_soc'].min() * 0.99
    y_max = df_visualizzato['total_soc'].max() * 1.01
    split_date = pd.to_datetime("2026-01-01")
    
    # Valore SOC a Gennaio 2026 (Mese 61) per la linea di riferimento
    try:
        val_2026 = df_orig[(df_orig['Scenario_Esteso'] == "Gestione Tradizionale (Baseline)") & 
                           (df_orig['Mese_Progressivo'] == 61)]['total_soc'].values[0]
    except:
        val_2026 = df_visualizzato['total_soc'].iloc[0]

    fig.update_layout(
        title=title,
        xaxis=dict(range=[pd.to_datetime("2021-01-01"), pd.to_datetime("2031-01-01")], 
                   fixedrange=True, showgrid=False), # Tolte linee grigie
        yaxis=dict(range=[y_min, y_max], title="Stock di C (ton/ha)", showgrid=False), # Tolte linee grigie
        sliders=[],
        updatemenus=[dict(
            type="buttons", showactive=False, x=0, y=-0.12,
            buttons=[dict(label="▶ AVVIA SIMULAZIONE", method="animate", 
                          args=[None, {"frame": {"duration": 40, "redraw": False}, "fromcurrent": True}])]
        )]
    )
    
    # 1. Linea NERA CONTINUA di riferimento (Target dal 2026)
    fig.add_shape(type="line", x0=split_date, x1=pd.to_datetime("2031-01-01"), 
                  y0=val_2026, y1=val_2026,
                  line=dict(color="Black", width=1.5, dash="solid"))
    
    # 2. Linea di demarcazione verticale 2026
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper", 
                  line=dict(color="Gray", width=1, dash="dot"))
    
    fig.update_traces(line=dict(width=2.5), selector=
