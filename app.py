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

# Funzione per pulire il layout Plotly (rimuove slider, fissa assi e aggiunge linea 2026)
def apply_clean_layout(fig, title, baseline_name):
    split_date = pd.to_datetime("2026-01-01")
    fig.update_layout(
        title=title,
        xaxis=dict(range=[pd.to_datetime("2021-01-01"), pd.to_datetime("2031-01-01")]),
        sliders=[], # Rimuove esplicitamente lo slider
        updatemenus=[dict(
            type="buttons", showactive=False, x=0, y=-0.15,
            buttons=[dict(label="▶ AVVIA SIMULAZIONE", method="animate", args=[None, {"frame": {"duration": 40, "redraw": False}, "fromcurrent": True}])]
        )]
    )
    # Linea di demarcazione 2026
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper", line=dict(color="Black", width=2, dash="dash"))
    fig.add_annotation(x=split_date, y=1.05, yref="paper", text="Proiezione Futura (2026)", showarrow=False, font=dict(color="Black"))
    # Spessore Baseline
    fig.update_traces(line=dict(width=3), selector=dict(name=baseline_name))
    return fig

st.title("🌱 Dashboard Decarbonizzazione Casalasco")
tab1, tab2, tab3 = st.tabs(["📊 LIVELLO 1", "🧪 LIVELLO 2", "🌍 LIVELLO 3"])

# --- LIVELLO 1 ---
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with c2: a1 = st.radio(f"Ammendante ({p1})?", ["Sì", "No"], horizontal=True, key="a1")
    df1 = load_data(p1, a1)
    if df1 is not None:
        with c3: rot1 = st.selectbox("🚜 Rotazione", df1['Rotazione'].unique(), key="rot1")
        df1_r = df1[df1['Rotazione'] == rot1].copy()
        scen_multi = st.multiselect("✨ Seleziona Scenari", [s for s in df1_r['Scenario_Esteso'].unique() if s != "Gestione Tradizionale (Baseline)"], key="m1")
        
        if scen_multi:
            animation_list = []
            targets = scen_multi + ["Gestione Tradizionale (Baseline)"]
            for m in range(1, 121, 4):
                for s in targets:
                    temp = df1_r[(df1_r['Scenario_Esteso'] == ("Gestione Tradizionale (Baseline)" if m <= 60 else s)) & (df1_r['Mese_Progressivo'] <= m)].copy()
                    temp['Scenario_Visualizzato'] = s
                    temp['Frame'] = m
                    animation_list.append(temp)
            fig1 = px.line(pd.concat(animation_list), x='Data', y='total_soc', color='Scenario_Visualizzato', animation_frame='Frame', 
                           color_discrete_map={"Gestione Tradizionale (Baseline)": "#0000FF"}, template="plotly_white")
            fig1 = apply_clean_layout(fig1, f"Analisi Multi-Scenario - {p1}", "Gestione Tradizionale (Baseline)")
            st.plotly_chart(fig1, use_container_width=True)

# --- LIVELLO 2 ---
with tab2:
    p2 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p2")
    df_si = load_data(p2, "Sì")
    df_no = load_data(p2, "No")
    if df_si is not None and df_no is not None:
        c1, c2 = st.columns(2)
        with c1: rot2 = st.selectbox("🚜 Rotazione", df_si['Rotazione'].unique(), key="rot2")
        with c2: scen2 = st.selectbox("✨ Scenario da testare", [s for s in df_si['Scenario_Esteso'].unique() if "Baseline" not in s], key="scen2")
        
        label_amm = {"Cremona": "Digestato", "Mantova": "Slurry", "Piacenza": "Letame"}[p2]
        targets = {f"{scen2} (+ {label_amm})": (df_si, scen2), f"{scen2} (No Amm.)": (df_no, scen2), "Baseline (Rif. Blu)": (df_si, "Gestione Tradizionale (Baseline)")}
        
        anim2 = []
        for m in range(1, 121, 4):
            for name, (source_df, source_scen) in targets.items():
                d_r = source_df[source_df['Rotazione'] == rot2]
                temp = d_r[(d_r['Scenario_Esteso'] == ("Gestione Tradizionale (Baseline)" if m <= 60 else source_scen)) & (d_r['Mese_Progressivo'] <= m)].copy()
                temp['Legenda'] = name
                temp['Frame'] = m
                anim2.append(temp)
        
        fig2 = px.line(pd.concat(anim2), x='Data', y='total_soc', color='Legenda', animation_frame='Frame',
                       color_discrete_map={"Baseline (Rif. Blu)": "#0000FF"}, template="plotly_white")
        fig2 = apply_clean_layout(fig2, f"Impatto {label_amm} su {scen2}", "Baseline (Rif. Blu)")
        st.plotly_chart(fig2, use_container_width=True)

# --- LIVELLO 3 ---
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        pa, aa = st.selectbox("Provincia A", ["Cremona", "Mantova", "Piacenza"], key="pa"), st.radio("Ammendante A", ["Sì", "No"], key="aa")
    with c2:
        pb, ab = st.selectbox("Provincia B", ["Cremona", "Mantova", "Piacenza"], index=1, key="pb"), st.radio("Ammendante B", ["Sì", "No"], key="ab")
    
    dfa, dfb = load_data(pa, aa), load_data(pb, ab)
    if dfa is not None and dfb is not None:
        rot3 = st.selectbox("🚜 Rotazione Comune", list(set(dfa['Rotazione']) & set(dfb['Rotazione'])), key="rot3")
        scen3 = st.selectbox("✨ Scenario Confronto", [s for s in dfa['Scenario_Esteso'].unique() if "Baseline" not in s], key="scen3")
        
        anim3 = []
        for m in range(1, 121, 4):
            for (df, lbl) in [(dfa, f"{pa} ({aa})"), (dfb, f"{pb} ({ab})")]:
                d_r = df[df['Rotazione'] == rot3]
                temp = d_r[(d_r['Scenario_Esteso'] == ("Gestione Tradizionale (Baseline)" if m <= 60 else scen3)) & (d_r['Mese_Progressivo'] <= m)].copy()
                temp['Sito'] = lbl
                temp['Frame'] = m
                anim3.append(temp)
        
        fig3 = px.line(pd.concat(anim3), x='Data', y='total_soc', color='Sito', animation_frame='Frame', template="plotly_white")
        fig3 = apply_clean_layout(fig3, "Confronto Territoriale", "NESSUNA")
        st.plotly_chart(fig3, use_container_width=True)
