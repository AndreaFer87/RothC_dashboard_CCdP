import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAZIONE E CSS ---
st.set_page_config(page_title="Casalasco Decarb - Pro", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 3.5rem !important; }
    .main-title { font-size: 28px !important; font-weight: bold !important; color: #1E3A8A; margin-bottom: 20px !important; }
    .stTabs { margin-top: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🌱 Simulazione Sequestro C - Modello RothC</h1>', unsafe_allow_html=True)

# --- 1. MAPPATURA E COSTANTI ---
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
base_n = "Gestione Tradizionale (Baseline)"

def decode(name):
    return MAPPING.get(name.strip(), name.strip())

@st.cache_data
def load_data(provincia, scelta_amm):
    try:
        suffix = {"Cremona": "digestate", "Mantova": "slurry", "Piacenza": "manure"}[provincia]
        file_name = f"{provincia}_{suffix}.xlsx" if scelta_amm == "Sì" else f"{provincia}_NO{suffix}.xlsx"
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df['Scenario_Esteso'] = df['Scenario'].apply(decode)
        return df
    except: return None

def apply_final_layout(fig, df_visualizzato, title, baseline_name, punti_riferimento):
    y_min = df_visualizzato['total_soc'].min() * 0.99
    y_max = df_visualizzato['total_soc'].max() * 1.01
    fig.update_layout(
        height=600, margin=dict(t=80),
        title=dict(text=title, font=dict(size=20), y=0.95),
        xaxis=dict(range=[pd.to_datetime("2021-01-01"), pd.to_datetime("2031-01-01")], showgrid=False), 
        yaxis=dict(range=[y_min, y_max], title="Stock di C (ton/ha)", showgrid=False),
        sliders=[], 
        updatemenus=[dict(type="buttons", showactive=False, x=0, y=-0.15,
            buttons=[dict(label="▶ AVVIA SIMULAZIONE", method="animate", 
            args=[None, {"frame": {"duration": 40, "redraw": False}, "fromcurrent": True}])]
        )]
    )
    for val, label in punti_riferimento:
        fig.add_trace(px.scatter(x=[pd.to_datetime("2030-09-01")], y=[val]).data[0])
        fig.data[-1].update(mode='markers', marker=dict(color='black', size=12), name=f"Rif. 2026: {label}")
    fig.add_shape(type="line", x0=pd.to_datetime("2026-01-01"), x1=pd.to_datetime("2026-01-01"), y0=0, y1=1, yref="paper", line=dict(color="Red", width=2, dash="dot"))
    fig.update_traces(line=dict(width=2.5), selector=dict(name=baseline_name))
    return fig

tab1, tab2, tab3 = st.tabs(["📊 LIVELLO 1", "🧪 LIVELLO 2", "🌍 LIVELLO 3"])

# --- LIVELLO 1 ---
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with c2: a1 = st.radio(f"Ammendante ({p1})?", ["Sì", "No"], horizontal=True, key="a1")
    df1 = load_data(p1, a1)
    if df1 is not None:
        with c3:
            rots1 = sorted([r for r in df1['Rotazione'].unique() if "year" not in str(r).lower()])
            rot1 = st.selectbox("🚜 Rotazione", rots1, key="rot1")
        
        base_df1 = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == base_n)].copy()
        is_piacenza_cc = (p1 == "Piacenza" and a1 == "No" and "Pomodoro" in rot1)

        if is_piacenza_cc:
            st.markdown("---")
            cc_c1, cc_c2 = st.columns(2)
            with cc_c1: mod_cc = st.radio("🧐 **Analisi Frequenza Cover Crop?**", ["No", "Sì"], horizontal=True, key="mcc")
            if mod_cc == "Sì":
                map_cc = {"CC Anno 1": "year1", "CC Anno 3": "year3", "CC Anno 5": "year5", "CC Anni 1 e 3": "year13", "CC Anni 1 e 5": "year15"}
                with cc_c2: 
                    scen_spec = st.selectbox("✨ Pratica", [s for s in df1['Scenario_Esteso'].unique() if s != base_n], key="ss")
                sel_f = st.multiselect("📅 Frequenze", list(map_cc.keys()), key="sf")
                if sel_f:
                    targets1 = sel_f + [base_n]
                    df_m1 = pd.concat([ (base_df1.assign(Legenda=s) if s == base_n else pd.concat([base_df1[base_df1['Mese_Progressivo'] <= 60], df1[(df1['Rotazione'].str.contains(map_cc[s])) & (df1['Scenario_Esteso'] == scen_spec) & (df1['Mese_Progressivo'] > 60)]]).assign(Legenda=s)) for s in targets1 ])
            else:
                scen_s1 = st.multiselect("✨ Scenari", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n], key="ss1")
                targets1 = scen_s1 + [base_n]
                df_m1 = pd.concat([ (pd.concat([base_df1[base_df1['Mese_Progressivo'] <= 60], df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s) & (df1['Mese_Progressivo'] > 60)]]).assign(Legenda=s)) for s in targets1 ])
        else:
            scen_s1 = st.multiselect("✨ Scenari", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n], key="ss2")
            targets1 = scen_s1 + [base_n]
            df_m1 = pd.concat([ (pd.concat([base_df1[base_df1['Mese_Progressivo'] <= 60], df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s) & (df1['Mese_Progressivo'] > 60)]]).assign(Legenda=s)) for s in targets1 ])

        if 'targets1' in locals() and len(targets1) > 1:
            val26_1 = base_df1[base_df1['Mese_Progressivo'] == 61]['total_soc'].values[0]
            anim1 = []
            for m in range(1, 121, 4):
                for s in targets1:
                    t_f = base_df1[base_df1['Mese_Progressivo'] <= m].copy() if m <= 60 else df_m1[(df_m1['Legenda'] == s) & (df_m1['Mese_Progressivo'] <= m)].copy()
                    t_f['L'], t_f['Frame'] = s, m
                    anim1.append(t_f)
            fig1 = px.line(pd.concat(anim1).sort_values(['Frame', 'Mese_Progressivo']), x='Data', y='total_soc', color='L', animation_frame='Frame', color_discrete_map={base_n: "#0000FF"}, template="plotly_white")
            st.plotly_chart(apply_final_layout(fig1, df_m1, f"Proiezione Carbonio - {p1}", base_n, [(val26_1, p1)]), use_container_width=True)

# --- LIVELLO 2 ---
with tab2:
    p2 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p2")
    df_si, df_no = load_data(p2, "Sì"), load_data(p2, "No")
    if df_si is not None and df_no is not None:
        c2a, c2b, c2c = st.columns(3)
        with c2a: rot2 = st.selectbox("🚜 Rotazione", df_si['Rotazione'].unique(), key="rot2")
        with c2b: scen2 = st.selectbox("✨ Scenario Rigenerativo", [s for s in df_si['Scenario_Esteso'].unique() if base_n not in s], key="scen2")
        with c2c: amm_b2 = st.radio("Ammendante in Baseline?", ["Sì", "No"], horizontal=True, key="ab2")
        
        df_ref2 = df_si if amm_b2 == "Sì" else df_no
        b_ref_name = "Baseline (Riferimento)"
        targets2 = [f"{scen2} (+ Amm.)", f"{scen2} (No Amm.)", b_ref_name]
        
        # Unione dati per limiti assi
        df_m2 = pd.concat([df_si[(df_si['Rotazione'] == rot2) & (df_si['Scenario_Esteso'] == scen2)], df_no[(df_no['Rotazione'] == rot2) & (df_no['Scenario_Esteso'] == scen2)], df_ref2[(df_ref2['Rotazione'] == rot2) & (df_ref2['Scenario_Esteso'] == base_n)]])

        anim2 = []
        for m in range(1, 121, 4):
            for t in targets2:
                src = df_si if "+ Amm." in t else (df_no if "No Amm." in t else df_ref2)
                sn = scen2 if t != b_ref_name else base_n
                if m <= 60:
                    t_f = df_ref2[(df_ref2['Rotazione'] == rot2) & (df_ref2['Scenario_Esteso'] == base_n) & (df_ref2['Mese_Progressivo'] <= m)].copy()
                else:
                    pre = df_ref2[(df_ref2['Rotazione'] == rot2) & (df_ref2['Scenario_Esteso'] == base_n) & (df_ref2['Mese_Progressivo'] <= 60)]
                    post = src[(src['Rotazione'] == rot2) & (src['Scenario_Esteso'] == sn) & (src['Mese_Progressivo'] > 60) & (src['Mese_Progressivo'] <= m)]
                    t_f = pd.concat([pre, post])
                t_f['L'], t_f['Frame'] = t, m
                anim2.append(t_f)
        
        val26_2 = df_ref2[(df_ref2['Rotazione'] == rot2) & (df_ref2['Scenario_Esteso'] == base_n) & (df_ref2['Mese_Progressivo'] == 61)]['total_soc'].values[0]
        fig2 = px.line(pd.concat(anim2).sort_values(['Frame', 'Mese_Progressivo']), x='Data', y='total_soc', color='L', animation_frame='Frame', color_discrete_map={b_ref_name: "#0000FF"}, template="plotly_white")
        st.plotly_chart(apply_final_layout(fig2, df_m2, f"Impatto Ammendante - {p2}", b_ref_name, [(val26_2, "Base")]), use_container_width=True)

# --- LIVELLO 3 ---
with tab3:
    c3a, c3b = st.columns(2)
    with c3a: pa, aa = st.selectbox("Sito A", ["Cremona", "Mantova", "Piacenza"], key="pa"), st.radio("Amm. A", ["Sì", "No"], key="aa")
    with c3b: pb, ab = st.selectbox("Sito B", ["Cremona", "Mantova", "Piacenza"], index=1, key="pb"), st.radio("Amm. B", ["Sì", "No"], key="ab")
    dfa, dfb = load_data(pa, aa), load_data(pb, ab)
    if dfa is not None and dfb is not None:
        rot3 = st.selectbox("🚜 Rotazione Comune", sorted(list(set(dfa['Rotazione']) & set(dfb['Rotazione']))), key="rot3")
        scen3 = st.selectbox("✨ Scenario da confrontare", [s for s in dfa['Scenario_Esteso'].unique() if base_n not in s], key="scen3")
        la, lb = f"{pa} ({aa})", f"{pb} ({ab})"
        
        anim3 = []
        for m in range(1, 121, 4):
            for (df, lbl) in [(dfa, la), (dfb, lb)]:
                if m <= 60:
                    t_f = df[(df['Rotazione'] == rot3) & (df['Scenario_Esteso'] == base_n) & (df['Mese_Progressivo'] <= m)].copy()
                else:
                    pre = df[(df['Rotazione'] == rot3) & (df['Scenario_Esteso'] == base_n) & (df['Mese_Progressivo'] <= 60)]
                    post = df[(df['Rotazione'] == rot3) & (df['Scenario_Esteso'] == scen3) & (df['Mese_Progressivo'] > 60) & (df['Mese_Progressivo'] <= m)]
                    t_f = pd.concat([pre, post])
                t_f['L'], t_f['Frame'] = lbl, m
                anim3.append(t_f)
        
        v26a = dfa[(dfa['Rotazione'] == rot3) & (dfa['Scenario_Esteso'] == base_n) & (dfa['Mese_Progressivo'] == 61)]['total_soc'].values[0]
        v26b = dfb[(dfb['Rotazione'] == rot3) & (dfb['Scenario_Esteso'] == base_n) & (dfb['Mese_Progressivo'] == 61)]['total_soc'].values[0]
        fig3 = px.line(pd.concat(anim3).sort_values(['Frame', 'Mese_Progressivo']), x='Data', y='total_soc', color='L', animation_frame='Frame', template="plotly_white")
        st.plotly_chart(apply_final_layout(fig3, pd.concat([dfa, dfb]), "Confronto Territoriale", "NONE", [(v26a, pa), (v26b, pb)]), use_container_width=True)
