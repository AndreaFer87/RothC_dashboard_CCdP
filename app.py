import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Casalasco Decarb - Pro", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 3.5rem !important; }
    .main-title { font-size: 28px !important; font-weight: bold !important; color: #1E3A8A; margin-bottom: 20px !important; }
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
    suffix = {"Cremona": "digestate", "Mantova": "slurry", "Piacenza": "manure"}[provincia]
    file_name = f"{provincia}_{suffix}.xlsx" if scelta_amm == "Sì" else f"{provincia}_NO{suffix}.xlsx"
    try:
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df['Scenario_Esteso'] = df['Scenario'].apply(decode)
        return df
    except Exception as e:
        return None

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
    fig.add_shape(type="line", x0=pd.to_datetime("2026-01-01"), x1=pd.to_datetime("2026-01-01"), line=dict(color="Red", width=2, dash="dot"))
    fig.update_traces(line=dict(width=2.5), selector=dict(name=baseline_name))
    return fig

# --- DEFINIZIONE TAB ---
tab1, tab2, tab3 = st.tabs(["📊 LIVELLO 1", "🧪 LIVELLO 2", "🌍 LIVELLO 3"])

# --- LIVELLO 1 ---
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with c2: a1 = st.radio(f"Ammendante ({p1})?", ["Sì", "No"], horizontal=True, key="a1")
    df1 = load_data(p1, a1)
    if df1 is not None:
        with c3:
            rot1 = st.selectbox("🚜 Rotazione", sorted([r for r in df1['Rotazione'].unique() if "year" not in str(r).lower()]), key="rot1")
        
        df_base_real = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == base_n)].copy()
        is_piacenza_cc = (p1 == "Piacenza" and a1 == "No" and "Pomodoro" in rot1)

        temp_list = []
        if is_piacenza_cc:
            st.markdown("---")
            col_cc1, col_cc2 = st.columns(2)
            with col_cc1: mod_cc = st.radio("🧐 **Analisi Frequenza Cover Crop?**", ["No", "Sì"], horizontal=True, key="mcc")
            if mod_cc == "Sì":
                mapping_cc = {"CC Anno 1": "year1", "CC Anno 3": "year3", "CC Anno 5": "year5", "CC Anni 1 e 3": "year13", "CC Anni 1 e 5": "year15"}
                with col_cc2: scen_cc_scelto = st.selectbox("✨ Pratica", [s for s in df1['Scenario_Esteso'].unique() if s != base_n], key="ss_cc")
                scelte_freq = st.multiselect("📅 Frequenze", list(mapping_cc.keys()), key="sf")
                if scelte_freq:
                    final_targets = scelte_freq + [base_n]
                    for s in final_targets:
                        if s == base_n: u = df_base_real.copy()
                        else:
                            df_spec = df1[(df1['Rotazione'].str.contains(mapping_cc[s])) & (df1['Scenario_Esteso'] == scen_cc_scelto)].copy()
                            u = pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], df_spec[df_spec['Mese_Progressivo'] > 60]])
                        u['Legenda'] = s
                        temp_list.append(u)
            else:
                scen_scelti = st.multiselect("✨ Scenari", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n], key="ss1")
                final_targets = scen_scelti + [base_n]
                for s in final_targets:
                    df_s = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s)].copy()
                    u = pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], df_s[df_s['Mese_Progressivo'] > 60]])
                    u['Legenda'] = s
                    temp_list.append(u)
        else:
            scen_scelti = st.multiselect("✨ Scenari", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n], key="ss2")
            final_targets = scen_scelti + [base_n]
            for s in final_targets:
                df_s = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s)].copy()
                u = pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], df_s[df_s['Mese_Progressivo'] > 60]])
                u['Legenda'] = s
                temp_list.append(u)

        if temp_list:
            df_merged = pd.concat(temp_list)
            val_2026 = df_base_real[df_base_real['Mese_Progressivo'] == 61]['total_soc'].values[0]
            anim_frames = []
            for m in range(1, 121, 4):
                for s in final_targets:
                    # Logica Staffetta: baseline per tutti fino al 60, poi scenario specifico
                    if m <= 60: t_f = df_base_real[df_base_real['Mese_Progressivo'] <= m].copy()
                    else: t_f = df_merged[(df_merged['Legenda'] == s) & (df_merged['Mese_Progressivo'] <= m)].copy()
                    t_f['L'], t_f['Frame'] = s, m
                    anim_frames.append(t_f)
            
            fig1 = px.line(pd.concat(anim_frames).sort_values(['Frame', 'Mese_Progressivo']), x='Data', y='total_soc', color='L', animation_frame='Frame', color_discrete_map={base_n: "#0000FF"}, template="plotly_white")
            st.plotly_chart(apply_final_layout(fig1, df_merged, f"Proiezione Carbonio - {p1}", base_n, [(val_2026, p1)]), use_container_width=True)

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
        
        temp_list2 = []
        for t in targets2:
            src = df_si if "+ Amm." in t else (df_no if "No Amm." in t else df_ref2)
            sn = scen2 if t != b_ref_name else base_n
            u = pd.concat([df_ref2[(df_ref2['Rotazione'] == rot2) & (df_ref2['Scenario_Esteso'] == base_n) & (df_ref2['Mese_Progressivo'] <= 60)],
                           src[(src['Rotazione'] == rot2) & (src['Scenario_Esteso'] == sn) & (src['Mese_Progressivo'] > 60)]])
            u['Legenda'] = t
            temp_list2.append(u)
        
        df_merged2 = pd.concat(temp_list2)
        anim2 = []
        for m in range(1, 121, 4):
            for t in targets2:
                if m <= 60: t_f = df_ref2[(df_ref2['Rotazione'] == rot2) & (df_ref2['Scenario_Esteso'] == base_n) & (df_ref2['Mese_Progressivo'] <= m)].copy()
                else: t_f = df_merged2[(df_merged2['Legenda'] == t) & (df_merged2['Mese_Progressivo'] <= m)].copy()
                t_f['L'], t_f['Frame'] = t, m
                anim2.append(t_f)
        
        val26_2 = df_ref2[(df_ref2['Rotazione'] == rot2) & (df_ref2['Scenario_Esteso'] == base_n) & (df_ref2['Mese_Progressivo'] == 61)]['total_soc'].values[0]
        fig2 = px.line(pd.concat(anim2).sort_values(['Frame', 'Mese_Progressivo']), x='Data', y='total_soc', color='L', animation_frame='Frame', color_discrete_map={b_ref_name: "#0000FF"}, template="plotly_white")
        st.plotly_chart(apply_final_layout(fig2, df_merged2, f"Impatto Ammendante - {p2}", b_ref_name, [(val26_2, "Base")]), use_container_width=True)

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
        
        temp_list3 = []
        for df, lbl in [(dfa, la), (dfb, lb)]:
            u = pd.concat([df[(df['Rotazione'] == rot3) & (df['Scenario_Esteso'] == base_n) & (df['Mese_Progressivo'] <= 60)],
                           df[(df['Rotazione'] == rot3) & (df['Scenario_Esteso'] == scen3) & (df['Mese_Progressivo'] > 60)]])
            u['Legenda'] = lbl
            temp_list3.append(u)
            
        df_merged3 = pd.concat(temp_list3)
        anim3 = []
        for m in range(1, 121, 4):
            for lbl in [la, lb]:
                src_df = dfa if lbl == la else dfb
                if m <= 60: t_f = src_df[(src_df['Rotazione'] == rot3) & (src_df['Scenario_Esteso'] == base_n) & (src_df['Mese_Progressivo'] <= m)].copy()
                else: t_f = df_merged3[(df_merged3['Legenda'] == lbl) & (df_merged3['Mese_Progressivo'] <= m)].copy()
                t_f['L'], t_f['Frame'] = lbl, m
                anim3.append(t_f)
        
        v26a = dfa[(dfa['Rotazione'] == rot3) & (dfa['Scenario_Esteso'] == base_n) & (dfa['Mese_Progressivo'] == 61)]['total_soc'].values[0]
        v26b = dfb[(dfb['Rotazione'] == rot3) & (dfb['Scenario_Esteso'] == base_n) & (dfb['Mese_Progressivo'] == 61)]['total_soc'].values[0]
        fig3 = px.line(pd.concat(anim3).sort_values(['Frame', 'Mese_Progressivo']), x='Data', y='total_soc', color='L', animation_frame='Frame', template="plotly_white")
        st.plotly_chart(apply_final_layout(fig3, df_merged3, "Confronto Territoriale", "NONE", [(v26a, pa), (v26b, pb)]), use_container_width=True)
