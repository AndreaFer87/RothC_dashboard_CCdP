import streamlit as st
import pandas as pd
import plotly.express as px

# Configurazione Pagina
st.set_page_config(page_title="Casalasco Decarb - Pro", layout="wide")

# --- CSS DEFINITIVO ---
st.markdown("""
    <style>
    .block-container { padding-top: 3.5rem !important; }
    .main-title { font-size: 30px !important; font-weight: bold !important; color: #1E3A8A; margin-bottom: 20px !important; }
    .stTabs { margin-top: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🌱 Simulazione Modello RothC - Agricoltura Rigenerativa</h1>', unsafe_allow_html=True)

# --- COSTANTI ---
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
        df['Scenario_Esteso'] = df['Scenario'].apply(decode := lambda x: MAPPING.get(x.strip(), x.strip()))
        return df
    except: return None

def apply_final_layout(fig, df_visualizzato, title, points):
    y_min, y_max = df_visualizzato['total_soc'].min() * 0.98, df_visualizzato['total_soc'].max() * 1.02
    fig.update_layout(
        height=620, margin=dict(l=25, r=25, t=70, b=30),
        title=dict(text=title, font=dict(size=22), y=0.96),
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
        
        df_base = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == base_n)].copy()
        is_p_cc = (p1 == "Piacenza" and a1 == "No" and "Pomodoro - Frumento" in rot1)

        if is_p_cc:
            cc_c1, cc_c2 = st.columns(2)
            with cc_c1: m_cc = st.radio("Analisi effetto frequenza Cover crop ?", ["No", "Sì"], horizontal=True)
            if m_cc == "Sì":
                # Mappatura precisa basata sui nomi reali delle rotazioni nel tuo Excel
                maps = {
                    "CC Anno 1": "Pomodoro - Frumento granella 1cc year1",
                    "CC Anno 3": "Pomodoro - Frumento granella 1cc year3",
                    "CC Anno 5": "Pomodoro - Frumento granella 1cc year5",
                    "CC Anni 1-3": "Pomodoro - Frumento granella 1cc year13",
                    "CC Anni 1-5": "Pomodoro - Frumento granella 1cc year15"
                }
                with cc_c2: 
                    scen_cc = st.selectbox("Pratica", [s for s in df1['Scenario_Esteso'].unique() if s != base_n])
                sel = st.multiselect("Seleziona Frequenze", list(maps.keys()))
                if sel:
                    targets = sel + [base_n]
                    # Costruzione DF con STAFFETTA precisa al mese 60
                    df_m = pd.DataFrame()
                    for s in targets:
                        if s == base_n:
                            df_temp = df_base.copy()
                        else:
                            # Prende 2021-2025 da Baseline, poi 2026-2030 dalla rotazione specifica
                            p_pre = df_base[df_base['Mese_Progressivo'] <= 60]
                            p_post = df1[(df1['Rotazione'] == maps[s]) & (df1['Scenario_Esteso'] == scen_cc) & (df1['Mese_Progressivo'] > 60)]
                            df_temp = pd.concat([p_pre, p_post])
                        df_temp['Legenda'] = s
                        df_m = pd.concat([df_m, df_temp])
            else:
                scens = st.multiselect("Scenari", [s for s in df1['Scenario_Esteso'].unique() if s != base_n])
                targets = scens + [base_n]
                df_m = pd.concat([pd.concat([df_base[df_base['Mese_Progressivo'] <= 60], df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s) & (df1['Mese_Progressivo'] > 60)]]).assign(Legenda=s) for s in targets])
        else:
            scens = st.multiselect("Scenari", [s for s in df1['Scenario_Esteso'].unique() if s != base_n], key="scens1")
            targets = scens + [base_n]
            df_m = pd.concat([pd.concat([df_base[df_base['Mese_Progressivo'] <= 60], df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s) & (df1['Mese_Progressivo'] > 60)]]).assign(Legenda=s) for s in targets])

        if 'targets' in locals() and len(targets) > 1:
            val26 = df_base[df_base['Mese_Progressivo'] == 61]['total_soc'].iloc[0]
            frames = []
            for m in range(1, 121, 4): # Esteso a 120 mesi (10 anni)
                for s in targets:
                    f = df_m[(df_m['Legenda'] == s) & (df_m['Mese_Progressivo'] <= m)].copy()
                    f['L'], f['Frame'] = s, m
                    frames.append(f)
            
            fig1 = px.line(pd.concat(frames), x='Data', y='total_soc', color='L', animation_frame='Frame', 
                           color_discrete_map={base_n: "#0000FF"}, template="plotly_white")
            st.plotly_chart(apply_final_layout(fig1, df_m, f"Proiezione - {p1}", [(val26, p1)]), use_container_width=True)

with tab2:
    p2 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p2")
    df_si, df_no = load_data(p2, "Sì"), load_data(p2, "No")
    if df_si is not None and df_no is not None:
        c2a, c2b = st.columns(2)
        with c2a: rot2 = st.selectbox("🚜 Rotazione", df_si['Rotazione'].unique(), key="rot2")
        with c2b: scen2 = st.selectbox("✨ Scenario", [s for s in df_si['Scenario_Esteso'].unique() if base_n not in s], key="scen2")
        amm_b = st.radio("Ammendante Organico in Baseline?", ["Sì", "No"], horizontal=True, key="amm_b2")
        df_br = df_si if amm_b == "Sì" else df_no
        check_base = df_br[(df_br['Rotazione'] == rot2) & (df_br['Scenario_Esteso'] == base_n)]
        
        if not check_base.empty:
            l_ref = "Baseline (Riferimento)"
            t2 = [f"{scen2} (+ Amm.)", f"{scen2} (No Amm.)", l_ref]
            frames2 = []
            for m in range(1, 118, 4):
                for t in t2:
                    src = df_si if "+ Amm." in t else (df_no if "No Amm." in t else df_br)
                    sn = scen2 if t != l_ref else base_n
                    f = df_br[(df_br['Rotazione'] == rot2) & (df_br['Scenario_Esteso'] == base_n) & (df_br['Mese_Progressivo'] <= m)].copy() if m <= 60 else src[(src['Rotazione'] == rot2) & (src['Scenario_Esteso'] == sn) & (src['Mese_Progressivo'] <= m)].copy()
                    f['L'], f['Frame'] = t, m
                    frames2.append(f)
            df_a2 = pd.concat(frames2)
            v26_2 = check_base[check_base['Mese_Progressivo'] == 61]['total_soc'].iloc[0]
            fig2 = px.line(df_a2, x='Data', y='total_soc', color='L', animation_frame='Frame', color_discrete_map={l_ref: "#0000FF"}, template="plotly_white")
            st.plotly_chart(apply_final_layout(fig2, df_a2, "Impatto Ammendante", l_ref, [(v26_2, "Base")]), use_container_width=True)

with tab3:
    c3a, c3b = st.columns(2)
    with c3a: pa = st.selectbox("Sito A", ["Cremona", "Mantova", "Piacenza"], key="pa"); aa = st.radio("Amm. A", ["Sì", "No"], key="aa")
    with c3b: pb = st.selectbox("Sito B", ["Cremona", "Mantova", "Piacenza"], index=1, key="pb"); ab = st.radio("Amm. B", ["Sì", "No"], key="ab")
    dfa, dfb = load_data(pa, aa), load_data(pb, ab)
    if dfa is not None and dfb is not None:
        rot3 = st.selectbox("🚜 Rotazione Comune", sorted(list(set(dfa['Rotazione']) & set(dfb['Rotazione']))), key="rot3")
        scen3 = st.selectbox("✨ Scenario", [s for s in dfa['Scenario_Esteso'].unique() if base_n not in s], key="scen3")
        lbl_a, lbl_b = f"Sito A: {pa} ({aa})", f"Sito B: {pb} ({ab})"
        base_a = dfa[(dfa['Rotazione'] == rot3) & (dfa['Scenario_Esteso'] == base_n)]
        base_b = dfb[(dfb['Rotazione'] == rot3) & (dfb['Scenario_Esteso'] == base_n)]
        
        if not base_a.empty and not base_b.empty:
            frames3 = []
            for m in range(1, 118, 4):
                for (df, lbl, base_df) in [(dfa, lbl_a, base_a), (dfb, lbl_b, base_b)]:
                    f = base_df[base_df['Mese_Progressivo'] <= m].copy() if m <= 60 else df[(df['Rotazione'] == rot3) & (df['Scenario_Esteso'] == scen3) & (df['Mese_Progressivo'] <= m)].copy()
                    f['Sito'], f['Frame'] = lbl, m
                    frames3.append(f)
            df_all3 = pd.concat(frames3)
            v26a = base_a[base_a['Mese_Progressivo'] == 61]['total_soc'].iloc[0]
            v26b = base_b[base_b['Mese_Progressivo'] == 61]['total_soc'].iloc[0]
            fig3 = px.line(df_all3, x='Data', y='total_soc', color='Sito', animation_frame='Frame', template="plotly_white")
            st.plotly_chart(apply_final_layout(fig3, df_all3, "Confronto Territoriale", "NA", [(v26a, pa), (v26b, pb)]), use_container_width=True)
