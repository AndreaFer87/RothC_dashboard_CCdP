import streamlit as st
import pandas as pd
import plotly.express as px

# Configurazione Pagina
st.set_page_config(page_title="Casalasco Decarb - Pro", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .block-container { padding-top: 3.5rem !important; }
    .main-title { font-size: 28px !important; font-weight: bold !important; color: #1E3A8A; margin-bottom: 20px !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🌱 Simulazione Sequestro C - Modello RothC</h1>', unsafe_allow_html=True)

# --- MAPPING ---
MAPPING = {
    "Baseline (CT)": "Baseline (CT)",
    "CC (CT)": "Cover crop (CT)",
    "Res (CT)": "Residui (CT)",
    "CC + Res (CT)": "Cover + Residui (CT)",
    "MT": "Minima Lavorazione",
    "MT + Res": "Minima + Residui",
    "MT + CC": "Minima + Cover",
    "MT + CC + Res": "Minima + Cover + Residui"
}
base_n = "Baseline (CT)"

@st.cache_data
def load_data(provincia, scelta_amm):
    try:
        suffix = {"Cremona": "digestate", "Mantova": "slurry", "Piacenza": "manure"}[provincia]
        file_name = f"{provincia}_{suffix}.xlsx" if scelta_amm == "Sì" else f"{provincia}_NO{suffix}.xlsx"
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df['Scenario_Esteso'] = df['Scenario'].apply(lambda x: MAPPING.get(x.strip(), x.strip()))
        return df
    except: return None

def apply_final_layout(fig, df_visualizzato, title, points):
    y_min, y_max = df_visualizzato['total_soc'].min() * 0.98, df_visualizzato['total_soc'].max() * 1.02
    fig.update_layout(
        height=620, margin=dict(l=25, r=25, t=70, b=30),
        title=dict(text=title, font=dict(size=20), y=0.96),
        xaxis=dict(range=[pd.to_datetime("2021-01-01"), pd.to_datetime("2031-01-01")], showgrid=False),
        yaxis=dict(range=[y_min, y_max], title="Stock di C (ton/ha)", showgrid=False),
        sliders=[],
        updatemenus=[dict(type="buttons", showactive=False, x=0, y=-0.15,
            buttons=[dict(label="▶ AVVIA SIMULAZIONE", method="animate", 
            args=[None, {"frame": {"duration": 40, "redraw": False}, "fromcurrent": True}])])]
    )
    for val, label in points:
        fig.add_trace(px.scatter(x=[pd.to_datetime("2030-09-01")], y=[val]).data[0])
        fig.data[-1].update(mode='markers', marker=dict(color='black', size=12), name=f"Rif. 2026: {label}")
    fig.add_shape(type="line", x0=pd.to_datetime("2026-01-01"), x1=pd.to_datetime("2026-01-01"), y0=0, y1=1, yref="paper", line=dict(color="Red", dash="dot"))
    return fig

# --- LOGICA TAB ---
tab1, tab2, tab3 = st.tabs(["📊 LIVELLO 1", "🧪 LIVELLO 2", "🌍 LIVELLO 3"])

with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with c2: a1 = st.radio("Ammendante?", ["Sì", "No"], horizontal=True, key="a1")
    df1 = load_data(p1, a1)
    
    if df1 is not None:
        with c3:
            rot_list = sorted([r for r in df1['Rotazione'].unique() if "year" not in str(r).lower()])
            rot1 = st.selectbox("🚜 Rotazione", rot_list, key="rot1")
        
        df_base_full = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == base_n)].copy()
        is_p_cc = (p1 == "Piacenza" and a1 == "No" and "Pomodoro - Frumento" in rot1)

        if is_p_cc:
            cc_c1, cc_c2 = st.columns(2)
            with cc_c1: m_cc = st.radio("Analisi effetto frequenza Cover crop ?", ["No", "Sì"], horizontal=True)
            if m_cc == "Sì":
                # MAPPING RIGIDO SUI NOMI DELLE ROTAZIONI NEL FILE
                freq_map = {
                    "CC Anno 1": "year1", "CC Anno 3": "year3", "CC Anno 5": "year5",
                    "CC Anni 1-3": "year13", "CC Anni 1-5": "year15"
                }
                with cc_c2: scen_cc = st.selectbox("Pratica", [s for s in df1['Scenario_Esteso'].unique() if s != base_n])
                sel = st.multiselect("Seleziona Frequenze", list(freq_map.keys()))
                
                if sel:
                    targets = [base_n] + sel
                    df_plot = pd.DataFrame()
                    for s in targets:
                        if s == base_n:
                            df_temp = df_base_full.copy()
                        else:
                            # COSTRUZIONE LINEA CONTINUA (0-60 Baseline, 61-120 Scenario)
                            p_pre = df_base_full[df_base_full['Mese_Progressivo'] <= 60].copy()
                            # Filtro robusto: cerchiamo la rotazione che contiene la sottostringa yearX
                            tag = freq_map[s]
                            p_post = df1[(df1['Rotazione'].str.contains(tag, case=False, na=False)) & 
                                         (df1['Scenario_Esteso'] == scen_cc) & 
                                         (df1['Mese_Progressivo'] > 60)].copy()
                            df_temp = pd.concat([p_pre, p_post]).sort_values('Mese_Progressivo')
                        
                        df_temp['Legenda'] = s
                        df_plot = pd.concat([df_plot, df_temp])
            else:
                scens = st.multiselect("Scenari", [s for s in df1['Scenario_Esteso'].unique() if s != base_n])
                targets = [base_n] + scens
                df_plot = pd.DataFrame()
                for s in targets:
                    if s == base_n: df_temp = df_base_full.copy()
                    else:
                        p_pre = df_base_full[df_base_full['Mese_Progressivo'] <= 60].copy()
                        p_post = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s) & (df1['Mese_Progressivo'] > 60)].copy()
                        df_temp = pd.concat([p_pre, p_post]).sort_values('Mese_Progressivo')
                    df_temp['Legenda'] = s
                    df_plot = pd.concat([df_plot, df_temp])
        else:
            scens = st.multiselect("Scenari", [s for s in df1['Scenario_Esteso'].unique() if s != base_n])
            targets = [base_n] + scens
            df_plot = pd.DataFrame()
            for s in targets:
                if s == base_n: df_temp = df_base_full.copy()
                else:
                    p_pre = df_base_full[df_base_full['Mese_Progressivo'] <= 60].copy()
                    p_post = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s) & (df1['Mese_Progressivo'] > 60)].copy()
                    df_temp = pd.concat([p_pre, p_post]).sort_values('Mese_Progressivo')
                df_temp['Legenda'] = s
                df_plot = pd.concat([df_plot, df_temp])

        if 'targets' in locals() and len(targets) > 1:
            # Calcolo valore 2026 per il puntino nero (rif. Baseline)
            val26 = df_base_full[df_base_full['Mese_Progressivo'] == 61]['total_soc'].iloc[0]
            
            # Creazione Frame per Animazione
            frames = []
            for m in range(1, 121, 4):
                f_subset = df_plot[df_plot['Mese_Progressivo'] <= m].copy()
                f_subset['Frame'] = m
                frames.append(f_subset)
            
            fig1 = px.line(pd.concat(frames), x='Data', y='total_soc', color='Legenda', 
                           animation_frame='Frame', template="plotly_white",
                           color_discrete_map={base_n: "#0000FF"})
            
            st.plotly_chart(apply_final_layout(fig1, df_plot, f"Proiezione Carbonio - {p1}", [(val26, p1)]), use_container_width=True)

# --- LIVELLO 2 E 3 SEGUONO STESSA LOGICA DI CONTINUITÀ ---
# (Rimosso per brevità, ma usa p_pre + p_post come sopra per evitare linee spezzate)
