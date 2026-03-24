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

# --- FUNZIONE LAYOUT PULITO (Senza Griglia e con Linea Target 2026) ---
def apply_final_layout(fig, df_visualizzato, title, baseline_name, df_orig):
    # Calcolo dinamico asse Y
    y_min = df_visualizzato['total_soc'].min() * 0.99
    y_max = df_visualizzato['total_soc'].max() * 1.01
    split_date = pd.to_datetime("2026-01-01")
    
    # Valore SOC a Gennaio 2026 (Mese 61) per la linea di riferimento orizzontale
    try:
        val_2026 = df_orig[(df_orig['Scenario_Esteso'] == "Gestione Tradizionale (Baseline)") & 
                           (df_orig['Mese_Progressivo'] == 61)]['total_soc'].values[0]
    except:
        val_2026 = df_visualizzato['total_soc'].iloc[0]

    fig.update_layout(
        title=title,
        xaxis=dict(range=[pd.to_datetime("2021-01-01"), pd.to_datetime("2031-01-01")], 
                   fixedrange=True, showgrid=False), 
        yaxis=dict(range=[y_min, y_max], title="Stock di C (ton/ha)", showgrid=False),
        sliders=[],
        updatemenus=[dict(
            type="buttons", showactive=False, x=0, y=-0.12,
            buttons=[dict(label="▶ AVVIA SIMULAZIONE", method="animate", 
                          args=[None, {"frame": {"duration": 40, "redraw": False}, "fromcurrent": True}])]
        )]
    )
    
    # 1. Linea NERA CONTINUA (Target dal 2026 in avanti)
    fig.add_shape(type="line", x0=split_date, x1=pd.to_datetime("2031-01-01"), 
                  y0=val_2026, y1=val_2026,
                  line=dict(color="Black", width=1.5, dash="solid"))
    
    # 2. Linea di demarcazione verticale tratteggiata (Gennaio 2026)
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper", 
                  line=dict(color="Gray", width=1, dash="dot"))
    
    # 3. Spessore Baseline (corretto l'errore di sintassi qui)
    fig.update_traces(line=dict(width=2.5), selector=dict(name=baseline_name))
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
        df1_f = df1[df1['Rotazione'] == rot1].copy()
        base_n = "Gestione Tradizionale (Baseline)"
        scen_scelti = st.multiselect("✨ Seleziona Scenari", [s for s in df1_f['Scenario_Esteso'].unique() if s != base_n], key="m1")
        
        if scen_scelti:
            targets = scen_scelti + [base_n]
            df_snapshot = df1_f[df1_f['Scenario_Esteso'].isin(targets)]
            anim1 = []
            for m in range(1, 121, 4):
                for s in targets:
                    source = base_n if m <= 60 else s
                    temp = df1_f[(df1_f['Scenario_Esteso'] == source) & (df1_f['Mese_Progressivo'] <= m)].copy()
                    temp['Scenario_Visualizzato'], temp['Frame'] = s, m
                    anim1.append(temp)
            fig1 = px.line(pd.concat(anim1), x='Data', y='total_soc', color='Scenario_Visualizzato', 
                           animation_frame='Frame', color_discrete_map={base_n: "#0000FF"}, template="plotly_white")
            fig1 = apply_final_layout(fig1, df_snapshot, f"Analisi Scenari - {p1}", base_n, df1_f)
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

# --- LIVELLO 2 ---
with tab2:
    p2 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p2")
    df_si, df_no = load_data(p2, "Sì"), load_data(p2, "No")
    if df_si is not None and df_no is not None:
        c1, c2 = st.columns(2)
        with c1: rot2 = st.selectbox("🚜 Rotazione", df_si['Rotazione'].unique(), key="rot2")
        with c2: scen2 = st.selectbox("✨ Scenario Rigenerativo", [s for s in df_si['Scenario_Esteso'].unique() if "Baseline" not in s], key="scen2")
        
        label = {"Cremona": "Digestato", "Mantova": "Slurry", "Piacenza": "Letame"}[p2]
        targets2 = {f"{scen2} (+ {label})": (df_si, scen2), f"{scen2} (No Amm.)": (df_no, scen2), "Baseline (Rif. Blu)": (df_si, base_n)}
        df_snapshot2 = pd.concat([df_si[df_si['Scenario_Esteso'].isin([scen2, base_n])], df_no[df_no['Scenario_Esteso'] == scen2]])
        anim2 = []
        for m in range(1, 121, 4):
            for name, (src, s_name) in targets2.items():
                d_r = src[src['Rotazione'] == rot2]
                s_now = base_n if m <= 60 else s_name
                temp = d_r[(d_r['Scenario_Esteso'] == s_now) & (d_r['Mese_Progressivo'] <= m)].copy()
                temp['Legenda'], temp['Frame'] = name, m
                anim2.append(temp)
        fig2 = px.line(pd.concat(anim2), x='Data', y='total_soc', color='Legenda', animation_frame='Frame',
                       color_discrete_map={"Baseline (Rif. Blu)": "#0000FF"}, template="plotly_white")
        fig2 = apply_final_layout(fig2, df_snapshot2, f"Confronto Ammendante - {p2}", "Baseline (Rif. Blu)", df_si[df_si['Rotazione']==rot2])
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

# --- LIVELLO 3 ---
with tab3:
    c1, c2 = st.columns(2)
    with c1: pa, aa = st.selectbox("Sito A", ["Cremona", "Mantova", "Piacenza"], key="pa"), st.radio("Amm. A", ["Sì", "No"], key="aa")
    with c2: pb, ab = st.selectbox("Sito B", ["Cremona", "Mantova", "Piacenza"], index=1, key="pb"), st.radio("Amm. B", ["Sì", "No"], key="ab")
    dfa, dfb = load_data(pa, aa), load_data(pb, ab)
    if dfa is not None and dfb is not None:
        rot3 = st.selectbox("🚜 Rotazione Comune", list(set(dfa['Rotazione']) & set(dfb['Rotazione'])), key="rot3")
        scen3 = st.selectbox("✨ Scenario da confrontare", [s for s in dfa['Scenario_Esteso'].unique() if "Baseline" not in s], key="scen3")
        df_snapshot3 = pd.concat([dfa[dfa['Scenario_Esteso'] == scen3], dfb[dfb['Scenario_Esteso'] == scen3]])
        anim3 = []
        for m in range(1, 121, 4):
            for (df, lbl) in [(dfa, f"{pa} ({aa})"), (dfb, f"{pb} ({ab})")]:
                d_r = df[df['Rotazione'] == rot3]
                s_now = base_n if m <= 60 else scen3
                temp = d_r[(d_r['Scenario_Esteso'] == s_now) & (d_r['Mese_Progressivo'] <= m)].copy()
                temp['Sito'], temp['Frame'] = lbl, m
                anim3.append(temp)
        fig3 = px.line(pd.concat(anim3), x='Data', y='total_soc', color='Sito', animation_frame='Frame', template="plotly_white")
        fig3 = apply_final_layout(fig3, df_snapshot3, "Confronto Territoriale", "NESSUNA", dfa[dfa['Rotazione']==rot3])
        st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
