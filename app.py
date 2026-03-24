import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb - Pro", layout="wide")

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

# --- 2. FUNZIONI CORE ---

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
        st.error(f"Errore caricamento file {file_name}: {e}")
        return None

def apply_final_layout(fig, df_visualizzato, title, baseline_name, punti_riferimento):
    y_min = df_visualizzato['total_soc'].min() * 0.99
    y_max = df_visualizzato['total_soc'].max() * 1.01
    split_date = pd.to_datetime("2026-01-01")
    target_date = pd.to_datetime("2030-09-01")
    
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
    for val, label in punti_riferimento:
        fig.add_trace(px.scatter(x=[target_date], y=[val]).data[0])
        fig.data[-1].update(mode='markers', marker=dict(color='black', size=12, symbol='circle'), 
                            name=f"Rif. 2026: {label}", showlegend=True)
    
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper", 
                  line=dict(color="Red", width=2, dash="dot"))
    
    # Baseline Blu e più spessa
    fig.update_traces(line=dict(width=2.5), selector=dict(name=baseline_name))
    return fig

# --- 3. DEFINIZIONE TAB ---
tab1, tab2, tab3 = st.tabs(["📊 LIVELLO 1", "🧪 LIVELLO 2", "🌍 LIVELLO 3"])

# --- LIVELLO 1 ---
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with c2: a1 = st.radio(f"Ammendante ({p1})?", ["Sì", "No"], horizontal=True, key="a1")
    
    df1 = load_data(p1, a1)
    
    if df1 is not None:
        with c3:
            all_rots = df1['Rotazione'].unique()
            rots_standard = sorted([r for r in all_rots if "year" not in str(r).lower()])
            rot1 = st.selectbox("🚜 Rotazione", rots_standard, key="rot1")
        
        df_base_real = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == base_n)].copy()
        
        # LOGICA PIACENZA CC
        is_piacenza_cc = (p1 == "Piacenza" and a1 == "No" and "Pomodoro - Frumento" in rot1)

        if is_piacenza_cc:
            st.markdown("---")
            col_cc1, col_cc2 = st.columns(2)
            
            with col_cc1:
                modalita_cc = st.radio(
                    "🧐 **Analisi Frequenza Cover Crop?**",
                    ["No, simulazione standard", "Sì, confronta frequenze"],
                    horizontal=True, key="radio_freq_cc"
                )

            if modalita_cc == "Sì, confronta frequenze":
                # 1. Scegli le frequenze (le rotazioni yearX)
                mapping_cc = {
                    "CC Anno 1": "Pomodoro - Frumento granella 1cc year1",
                    "CC Anno 3": "Pomodoro - Frumento granella 1cc year3",
                    "CC Anno 5": "Pomodoro - Frumento granella 1cc year5",
                    "CC Anni 1 e 3": "Pomodoro - Frumento granella 1cc year13",
                    "CC Anni 1 e 5": "Pomodoro - Frumento granella 1cc year15"
                }
                
                with col_cc2:
                    # 2. Scegli lo scenario rigenerativo da applicare a quelle frequenze
                    # Prendiamo gli scenari disponibili in una delle rotazioni speciali
                    sample_rot = mapping_cc["CC Anno 1"]
                    scenari_speciali = [s for s in df1[df1['Rotazione'] == sample_rot]['Scenario_Esteso'].unique() if s != base_n]
                    scen_cc_scelto = st.selectbox("✨ Seleziona Pratica da testare", scenari_speciali, key="scen_cc_piac")
                
                scelte_freq = st.multiselect("📅 Seleziona frequenze da confrontare", list(mapping_cc.keys()), key="m_freq_piacenza")
                
                if scelte_freq:
                    final_targets = scelte_freq + [base_n]
                    temp_list = []
                    for s in final_targets:
                        if s == base_n:
                            u = df_base_real.copy()
                        else:
                            rot_spec = mapping_cc[s]
                            # Filtriamo per la rotazione specifica AND lo scenario scelto
                            df_spec = df1[(df1['Rotazione'] == rot_spec) & (df1['Scenario_Esteso'] == scen_cc_scelto)].copy()
                            u = pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], 
                                          df_spec[df_spec['Mese_Progressivo'] > 60]])
                        u['Legenda'] = s
                        temp_list.append(u)
                    df_merged_scenarios = pd.concat(temp_list)
            else:
                # Simulazione Standard
                scen_scelti = st.multiselect("✨ Scenari Standard", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n], key="m1_std")
                final_targets = scen_scelti + [base_n]
                temp_list = []
                for s in final_targets:
                    df_s = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s)].copy()
                    u = pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], df_s[df_s['Mese_Progressivo'] > 60]])
                    u['Legenda'] = s
                    temp_list.append(u)
                df_merged_scenarios = pd.concat(temp_list)
        else:
            # Caso normale (Cremona, Mantova o Piacenza Manure)
            scen_scelti = st.multiselect("✨ Seleziona Scenari", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n], key="m1_gen")
            final_targets = scen_scelti + [base_n]
            temp_list = []
            for s in final_targets:
                df_s = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s)].copy()
                u = pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], df_s[df_s['Mese_Progressivo'] > 60]])
                u['Legenda'] = s
                temp_list.append(u)
            df_merged_scenarios = pd.concat(temp_list)

        # --- DISEGNO GRAFICO (Logica Baseline SOPRA) ---
        if 'final_targets' in locals() and len(final_targets) > 1:
            val_2026 = df_base_real[df_base_real['Mese_Progressivo'] == 61]['total_soc'].values[0]
            anim_frames = []
            for m in range(1, 118, 4):
                for s in final_targets:
                    if m <= 60:
                        temp_f = df_base_real[df_base_real['Mese_Progressivo'] <= m].copy()
                    else:
                        temp_f = df_merged_scenarios[(df_merged_scenarios['Legenda'] == s) & (df_merged_scenarios['Mese_Progressivo'] <= m)].copy()
                    temp_f['Legenda_Anim'], temp_f['Frame'] = s, m
                    anim_frames.append(temp_f)
            
            df_anim = pd.concat(anim_frames).sort_values(['Frame', 'Mese_Progressivo'])
            fig1 = px.line(df_anim, x='Data', y='total_soc', color='Legenda_Anim', 
                           animation_frame='Frame', color_discrete_map={base_n: "#0000FF"},
                           template="plotly_white", category_orders={"Legenda_Anim": final_targets})
            
            fig1 = apply_final_layout(fig1, df_merged_scenarios, f"Proiezione Carbonio - {p1}", base_n, [(val_2026, p1)])
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
# --- LIVELLO 2 E 3 ---
with tab2:
    p2 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p2")
    df_si, df_no = load_data(p2, "Sì"), load_data(p2, "No")
    if df_si is not None and df_no is not None:
        c1, c2, c3 = st.columns(3)
        with c1: rot2 = st.selectbox("🚜 Rotazione", df_si['Rotazione'].unique(), key="rot2")
        with c2: scen2 = st.selectbox("✨ Scenario Rigenerativo", [s for s in df_si['Scenario_Esteso'].unique() if base_n not in s], key="scen2")
        with c3: amm_base = st.radio("Ammendante nella Baseline?", ["Sì", "No"], horizontal=True, key="amm_base")
        
        df_base_ref = df_si if amm_base == "Sì" else df_no
        b_ref_name = "Baseline (Riferimento)"
        targets2_list = [f"{scen2} (+ Amm.)", f"{scen2} (No Amm.)", b_ref_name]
        
        anim2 = []
        for m in range(1, 118, 4):
            for t in targets2_list:
                if t == b_ref_name:
                    src = df_base_ref
                    s_name = base_n
                elif "+ Amm." in t:
                    src = df_si
                    s_name = scen2
                else:
                    src = df_no
                    s_name = scen2
                
                # Staffetta
                if m <= 60:
                    temp = df_base_ref[(df_base_ref['Rotazione'] == rot2) & (df_base_ref['Scenario_Esteso'] == base_n) & (df_base_ref['Mese_Progressivo'] <= m)].copy()
                else:
                    d_r = src[src['Rotazione'] == rot2]
                    temp = d_r[(d_r['Scenario_Esteso'] == s_name) & (d_r['Mese_Progressivo'] <= m)].copy()
                
                temp['Legenda'], temp['Frame'] = t, m
                anim2.append(temp)
        
        df_anim2 = pd.concat(anim2).sort_values(['Frame', 'Mese_Progressivo'])
        val_2026_l2 = df_base_ref[(df_base_ref['Rotazione'] == rot2) & (df_base_ref['Scenario_Esteso'] == base_n) & (df_base_ref['Mese_Progressivo'] == 61)]['total_soc'].values[0]
        
        fig2 = px.line(df_anim2, x='Data', y='total_soc', color='Legenda', animation_frame='Frame',
                       color_discrete_map={b_ref_name: "#0000FF"}, template="plotly_white",
                       category_orders={"Legenda": targets2_list})
        fig2 = apply_final_layout(fig2, df_anim2, f"Impatto Ammendante - {p2}", b_ref_name, [(val_2026_l2, "Base")])
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

with tab3:
    c1, c2 = st.columns(2)
    with c1: pa, aa = st.selectbox("Sito A", ["Cremona", "Mantova", "Piacenza"], key="pa"), st.radio("Amm. A", ["Sì", "No"], key="aa")
    with c2: pb, ab = st.selectbox("Sito B", ["Cremona", "Mantova", "Piacenza"], index=1, key="pb"), st.radio("Amm. B", ["Sì", "No"], key="ab")
    dfa, dfb = load_data(pa, aa), load_data(pb, ab)
    if dfa is not None and dfb is not None:
        rot3 = st.selectbox("🚜 Rotazione Comune", list(set(dfa['Rotazione']) & set(dfb['Rotazione'])), key="rot3")
        scen3 = st.selectbox("✨ Scenario da confrontare", [s for s in dfa['Scenario_Esteso'].unique() if base_n not in s], key="scen3")
        
        lbl_a, lbl_b = f"{pa} ({aa})", f"{pb} ({ab})"
        anim3 = []
        for m in range(1, 118, 4):
            for (df, lbl) in [(dfa, lbl_a), (dfb, lbl_b)]:
                if m <= 60:
                    temp = df[(df['Rotazione'] == rot3) & (df['Scenario_Esteso'] == base_n) & (df['Mese_Progressivo'] <= m)].copy()
                else:
                    temp = df[(df['Rotazione'] == rot3) & (df['Scenario_Esteso'] == scen3) & (df['Mese_Progressivo'] <= m)].copy()
                temp['Sito'], temp['Frame'] = lbl, m
                anim3.append(temp)
        
        df_anim3 = pd.concat(anim3).sort_values(['Frame', 'Mese_Progressivo'])
        val_2026_A = dfa[(dfa['Rotazione'] == rot3) & (dfa['Scenario_Esteso'] == base_n) & (dfa['Mese_Progressivo'] == 61)]['total_soc'].values[0]
        val_2026_B = dfb[(dfb['Rotazione'] == rot3) & (dfb['Scenario_Esteso'] == base_n) & (dfb['Mese_Progressivo'] == 61)]['total_soc'].values[0]
        
        fig3 = px.line(df_anim3, x='Data', y='total_soc', color='Sito', animation_frame='Frame', template="plotly_white")
        fig3 = apply_final_layout(fig3, df_anim3, "Confronto Territoriale", "NESSUNA", [(val_2026_A, pa), (val_2026_B, pb)])
        st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
