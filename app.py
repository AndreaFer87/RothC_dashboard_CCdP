import streamlit as st
import pandas as pd
import plotly.express as px

# ... [Configurazione iniziale e Mappatura (immutate)] ...

# --- LOGICA DI FILTRO SCENARI PIACENZA ---
def get_scenarios(df_filtered, rotazione):
    all_scens = [s for s in df_filtered['Scenario_Esteso'].unique() if s != base_n]
    
    # Se è la rotazione speciale di Piacenza, separiamo gli scenari "temporali"
    if rotazione == "Pomodoro-Frumento granella 1cc":
        # Scenari temporali (quelli che contengono indicazioni sull'anno)
        cc_temporal = [s for s in all_scens if any(anno in s for anno in ["anno 1", "anno 3", "anno 5", "anni 1"])]
        # Scenari standard (tutti gli altri)
        standard = [s for s in all_scens if s not in cc_temporal]
        return standard, cc_temporal
    
    return all_scens, []

# ... [Funzione apply_final_layout (immutata)] ...

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
        
        # Separazione Scenari
        scen_standard, scen_cc_temp = get_scenarios(df1_f, rot1)
        
        # Multiselect Standard
        scen_scelti = st.multiselect("✨ Scenari Rigenerativi", scen_standard, key="m1")
        
        # Slider/Multiselect Speciale per CC Temporali (solo se rotazione specifica)
        scen_cc_scelti = []
        if scen_cc_temp:
            st.info("💡 **Focus Cover Crop**: Confronta l'inserimento in anni diversi per questa rotazione")
            scen_cc_scelti = st.multiselect("📅 Opzioni temporali Cover Crop", scen_cc_temp, key="m_cc_temp")
        
        # Unione delle scelte
        final_targets = scen_scelti + scen_cc_scelti + [base_n]
        
        if len(final_targets) > 1:
            df_snapshot = df1_f[df1_f['Scenario_Esteso'].isin(final_targets)]
            val_2026 = df1_f[(df1_f['Scenario_Esteso'] == base_n) & (df1_f['Mese_Progressivo'] == 61)]['total_soc'].values[0]
            
            anim1 = []
            for m in range(1, 118, 4):
                for s in final_targets:
                    source = base_n if m <= 60 else s
                    temp = df1_f[(df1_f['Scenario_Esteso'] == source) & (df1_f['Mese_Progressivo'] <= m)].copy()
                    temp['Scenario_Visualizzato'], temp['Frame'] = s, m
                    anim1.append(temp)
            
            fig1 = px.line(pd.concat(anim1), x='Data', y='total_soc', color='Scenario_Visualizzato', 
                           animation_frame='Frame', color_discrete_map={base_n: "#0000FF"}, template="plotly_white")
            
            fig1 = apply_final_layout(fig1, df_snapshot, f"Analisi Scenari - {p1}", base_n, [(val_2026, p1)])
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

# --- LIVELLO 2 ---
with tab2:
    p2 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p2")
    df_si, df_no = load_data(p2, "Sì"), load_data(p2, "No")
    if df_si is not None and df_no is not None:
        c1, c2, c3 = st.columns(3)
        with c1: rot2 = st.selectbox("🚜 Rotazione", df_si['Rotazione'].unique(), key="rot2")
        with c2: scen2 = st.selectbox("✨ Scenario Rigenerativo", [s for s in df_si['Scenario_Esteso'].unique() if "Baseline" not in s], key="scen2")
        with c3: amm_base = st.radio("Ammendante nella Baseline?", ["Sì", "No"], horizontal=True, key="amm_base")
        
        label_amm = {"Cremona": "Digestato", "Mantova": "Slurry", "Piacenza": "Letame"}[p2]
        df_base_ref = df_si if amm_base == "Sì" else df_no
        
        targets2 = {f"{scen2} (+ {label_amm})": (df_si, scen2), f"{scen2} (No Amm.)": (df_no, scen2), "Baseline (Riferimento)": (df_base_ref, base_n)}
        df_snapshot2 = pd.concat([df_si[df_si['Scenario_Esteso'] == scen2], df_no[df_no['Scenario_Esteso'] == scen2], df_base_ref[df_base_ref['Scenario_Esteso'] == base_n]])
        
        val_2026_l2 = df_base_ref[(df_base_ref['Rotazione'] == rot2) & (df_base_ref['Scenario_Esteso'] == base_n) & (df_base_ref['Mese_Progressivo'] == 61)]['total_soc'].values[0]

        anim2 = []
        for m in range(1, 118, 4):
            for name, (src, s_name) in targets2.items():
                d_r = src[src['Rotazione'] == rot2]
                s_now = base_n if m <= 60 else s_name
                temp = d_r[(d_r['Scenario_Esteso'] == s_now) & (d_r['Mese_Progressivo'] <= m)].copy()
                temp['Legenda'], temp['Frame'] = name, m
                anim2.append(temp)
        
        fig2 = px.line(pd.concat(anim2), x='Data', y='total_soc', color='Legenda', animation_frame='Frame',
                       color_discrete_map={"Baseline (Riferimento)": "#0000FF"}, template="plotly_white")
        fig2 = apply_final_layout(fig2, df_snapshot2, f"Impatto Ammendante - {p2}", "Baseline (Riferimento)", [(val_2026_l2, "Base")])
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
        
        # CALCOLO DUE PUNTI DI RIFERIMENTO (A e B)
        val_2026_A = dfa[(dfa['Rotazione'] == rot3) & (dfa['Scenario_Esteso'] == base_n) & (dfa['Mese_Progressivo'] == 61)]['total_soc'].values[0]
        val_2026_B = dfb[(dfb['Rotazione'] == rot3) & (dfb['Scenario_Esteso'] == base_n) & (dfb['Mese_Progressivo'] == 61)]['total_soc'].values[0]

        anim3 = []
        for m in range(1, 118, 4):
            for (df, lbl) in [(dfa, f"{pa} ({aa})"), (dfb, f"{pb} ({ab})")]:
                d_r = df[df['Rotazione'] == rot3]
                s_now = base_n if m <= 60 else scen3
                temp = d_r[(d_r['Scenario_Esteso'] == s_now) & (d_r['Mese_Progressivo'] <= m)].copy()
                temp['Sito'], temp['Frame'] = lbl, m
                anim3.append(temp)
        
        fig3 = px.line(pd.concat(anim3), x='Data', y='total_soc', color='Sito', animation_frame='Frame', template="plotly_white")
        # Applichiamo i due punti neri
        fig3 = apply_final_layout(fig3, df_snapshot3, "Confronto Territoriale", "NESSUNA", [(val_2026_A, pa), (val_2026_B, pb)])
        st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
