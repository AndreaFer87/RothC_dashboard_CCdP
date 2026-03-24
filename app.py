import streamlit as st
import pd as pd
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
    try:
        suffix = {"Cremona": "digestate", "Mantova": "slurry", "Piacenza": "manure"}[provincia]
        file_name = f"{provincia}_{suffix}.xlsx" if scelta_amm == "Sì" else f"{provincia}_NO{suffix}.xlsx"
        df = pd.read_excel(file_name)
        df.columns = df.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df['Data'] = df['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df['Scenario_Esteso'] = df['Scenario'].apply(decode)
        return df
    except:
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

tab1, tab2, tab3 = st.tabs(["📊 LIVELLO 1", "🧪 LIVELLO 2", "🌍 LIVELLO 3"])

# --- LIVELLO 1 ---
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with c2: a1 = st.radio(f"Ammendante ({p1})?", ["Sì", "No"], horizontal=True, key="a1")
    df1 = load_data(p1, a1)
    
    if df1 is not None:
        rots_std = sorted([r for r in df1['Rotazione'].unique() if "year" not in str(r).lower()])
        with c3: rot1 = st.selectbox("🚜 Rotazione", rots_std, key="rot1")
        
        base_df1 = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == base_n)].copy()
        
        # --- SICUREZZA 1 ---
        if base_df1.empty:
            st.warning("Caricamento dati in corso o rotazione non trovata...")
            st.stop()

        scen_list = []
        targets1 = []
        
        if p1 == "Piacenza" and a1 == "No" and "Pomodoro" in rot1:
            st.markdown("---")
            cc_c1, cc_c2 = st.columns(2)
            with cc_c1: mod_cc = st.radio("🧐 **Analisi Frequenza Cover Crop?**", ["No", "Sì"], horizontal=True, key="mcc_piac")
            
            if mod_cc == "Sì":
                m_cc = {
                    "CC Anno 1": "year1",
                    "CC Anno 3": "year3",
                    "CC Anno 5": "year5",
                    "CC Anni 1 e 3": "year13",
                    "CC Anni 1 e 5": "year15"
                }
                with cc_c2: s_cc = st.selectbox("✨ Pratica", [s for s in df1['Scenario_Esteso'].unique() if s != base_n], key="scc_p_val")
                f_sel = st.multiselect("📅 Seleziona Frequenze", list(m_cc.keys()))
                
                if f_sel:
                    targets1 = f_sel + [base_n]
                    for s in targets1:
                        if s == base_n: u = base_df1.copy()
                        else:
                            df_spec = df1[(df1['Rotazione'].astype(str).str.contains(m_cc[s])) & (df1['Scenario_Esteso'] == s_cc)].copy()
                            if not df_spec.empty:
                                u = pd.concat([base_df1[base_df1['Mese_Progressivo'] <= 60], df_spec[df_spec['Mese_Progressivo'] > 60]])
                            else: u = base_df1.copy()
                        u['Legenda_Anim'] = s
                        scen_list.append(u)
            else:
                s_std = st.multiselect("✨ Scenari", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n], key="sstd_piac")
                targets1 = s_std + [base_n]
                for s in targets1:
                    df_s = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s)].copy()
                    u = pd.concat([base_df1[base_df1['Mese_Progressivo'] <= 60], df_s[df_s['Mese_Progressivo'] > 60]])
                    u['Legenda_Anim'] = s
                    scen_list.append(u)
        else:
            s_std = st.multiselect("✨ Scenari", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n], key="sstd_other")
            targets1 = s_std + [base_n]
            for s in targets1:
                df_s = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s)].copy()
                u = pd.concat([base_df1[base_df1['Mese_Progressivo'] <= 60], df_s[df_s['Mese_Progressivo'] > 60]])
                u['Legenda_Anim'] = s
                scen_list.append(u)

        if scen_list and targets1:
            df_m1 = pd.concat(scen_list)
            
            # --- SICUREZZA 2: CALCOLO V26 ---
            t26 = base_df1[base_df1['Mese_Progressivo'] >= 60]
            v26_1 = t26['total_soc'].iloc[0] if not t26.empty else base_df1['total_soc'].iloc[-1]
            
            anim1 = []
            for m in range(1, 121, 4):
                for s in targets1:
                    t_f = df_m1[(df_m1['Legenda_Anim'] == s) & (df_m1['Mese_Progressivo'] <= m)].copy()
                    if not t_f.empty:
                        t_f['Frame'] = m
                        anim1.append(t_f)
            
            if anim1:
                fig1 = px.line(pd.concat(anim1).sort_values(['Frame', 'Mese_Progressivo']), x='Data', y='total_soc', color='Legenda_Anim', animation_frame='Frame', color_discrete_map={base_n: "#0000FF"}, template="plotly_white")
                st.plotly_chart(apply_final_layout(fig1, df_m1, f"Proiezione - {p1}", base_n, [(v26_1, p1)]), use_container_width=True)

# --- LIVELLO 2 ---
with tab2:
    p2 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p2")
    dsi, dno = load_data(p2, "Sì"), load_data(p2, "No")
    if dsi is not None and dno is not None:
        c2a, c2b, c2c = st.columns(3)
        with c2a: r2 = st.selectbox("🚜 Rotazione", sorted([r for r in dsi['Rotazione'].unique() if "year" not in str(r).lower()]), key="r2")
        with c2b: s2 = st.selectbox("✨ Scenario", [s for s in dsi['Scenario_Esteso'].unique() if base_n not in s], key="s2")
        with c2c: ab2 = st.radio("Ammendante in Baseline?", ["Sì", "No"], horizontal=True, key="ab2")
        
        dref2 = dsi if ab2 == "Sì" else dno
        b_lbl = "Baseline (Riferimento)"
        t2_list = [f"{s2} (+ Amm.)", f"{s2} (No Amm.)", b_lbl]
        
        scen_list2 = []
        for t in t2_list:
            src = dsi if "+ Amm." in t else (dno if "No Amm." in t else dref2)
            sn = s2 if t != b_lbl else base_n
            u_base = dref2[(dref2['Rotazione'] == r2) & (dref2['Scenario_Esteso'] == base_n) & (dref2['Mese_Progressivo'] <= 60)]
            u_scen = src[(src['Rotazione'] == r2) & (src['Scenario_Esteso'] == sn) & (src['Mese_Progressivo'] > 60)]
            if not u_base.empty or not u_scen.empty:
                u = pd.concat([u_base, u_scen])
                u['Legenda_Anim'] = t
                scen_list2.append(u)
        
        if scen_list2:
            df_m2 = pd.concat(scen_list2)
            t26_2 = dref2[(dref2['Rotazione'] == r2) & (dref2['Scenario_Esteso'] == base_n) & (dref2['Mese_Progressivo'] >= 60)]
            v26_2 = t26_2['total_soc'].iloc[0] if not t26_2.empty else 0
            
            anim2 = []
            for m in range(1, 121, 4):
                for t in t2_list:
                    t_f = df_m2[(df_m2['Legenda_Anim'] == t) & (df_m2['Mese_Progressivo'] <= m)].copy()
                    if not t_f.empty:
                        t_f['Frame'] = m
                        anim2.append(t_f)
            
            if anim2:
                fig2 = px.line(pd.concat(anim2).sort_values(['Frame', 'Mese_Progressivo']), x='Data', y='total_soc', color='Legenda_Anim', animation_frame='Frame', color_discrete_map={b_lbl: "#0000FF"}, template="plotly_white")
                st.plotly_chart(apply_final_layout(fig2, df_m2, f"Impatto Ammendante - {p2}", b_lbl, [(v26_2, "Base")]), use_container_width=True)

# --- LIVELLO 3 ---
with tab3:
    c3a, c3b = st.columns(2)
    with c3a: pa, aa = st.selectbox("Sito A", ["Cremona", "Mantova", "Piacenza"], key="pa"), st.radio("Amm. A", ["Sì", "No"], key="aa")
    with c3b: pb, ab = st.selectbox("Sito B", ["Cremona", "Mantova", "Piacenza"], index=1, key="pb"), st.radio("Amm. B", ["Sì", "No"], key="ab")
    dfa, dfb = load_data(pa, aa), load_data(pb, ab)
    if dfa is not None and dfb is not None:
        common_rots = sorted([r for r in list(set(dfa['Rotazione']) & set(dfb['Rotazione'])) if "year" not in str(r).lower()])
        if common_rots:
            r3 = st.selectbox("🚜 Rotazione Comune", common_rots, key="r3")
            s3 = st.selectbox("✨ Scenario", [s for s in dfa['Scenario_Esteso'].unique() if base_n not in s], key="s3")
            la, lb = f"{pa} ({aa})", f"{pb} ({ab})"
            
            scen_list3 = []
            for df, lbl in [(dfa, la), (dfb, lb)]:
                u_b = df[(df['Rotazione'] == r3) & (df['Scenario_Esteso'] == base_n) & (df['Mese_Progressivo'] <= 60)]
                u_s = df[(df['Rotazione'] == r3) & (df['Scenario_Esteso'] == s3) & (df['Mese_Progressivo'] > 60)]
                u = pd.concat([u_b, u_s])
                u['Legenda_Anim'] = lbl
                scen_list3.append(u)
                
            df_m3 = pd.concat(scen_list3)
            t26a = dfa[(dfa['Rotazione'] == r3) & (dfa['Scenario_Esteso'] == base_n) & (dfa['Mese_Progressivo'] >= 60)]
            v26a = t26a['total_soc'].iloc[0] if not t26a.empty else 0
            t26b = dfb[(dfb['Rotazione'] == r3) & (dfb['Scenario_Esteso'] == base_n) & (dfb['Mese_Progressivo'] >= 60)]
            v26b = t26b['total_soc'].iloc[0] if not t26b.empty else 0
            
            anim3 = []
            for m in range(1, 121, 4):
                for lbl in [la, lb]:
                    t_f = df_m3[(df_m3['Legenda_Anim'] == lbl) & (df_m3['Mese_Progressivo'] <= m)].copy()
                    if not t_f.empty:
                        t_f['Frame'] = m
                        anim3.append(t_f)
            
            if anim3:
                fig3 = px.line(pd.concat(anim3).sort_values(['Frame', 'Mese_Progressivo']), x='Data', y='total_soc', color='Legenda_Anim', animation_frame='Frame', template="plotly_white")
                st.plotly_chart(apply_final_layout(fig3, df_m3, "Confronto Territoriale", "NONE", [(v26a, pa), (v26b, pb)]), use_container_width=True)
