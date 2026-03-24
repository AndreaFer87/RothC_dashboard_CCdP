import streamlit as st
import pandas as pd
import plotly.express as px

# Configurazione Pagina
st.set_page_config(page_title="Casalasco Decarb - Pro", layout="wide")

# --- CSS OTTIMIZZATO PER RECUPERARE SPAZIO ---
st.markdown("""
    <style>
    /* Riduce lo spazio superiore della pagina */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }
    /* Riduce lo spazio tra i widget e il grafico */
    .stSelectbox, .stRadio, .stMultiSelect {
        margin-bottom: -10px !important;
    }
    /* Aumenta font etichette */
    .stSelectbox label, .stRadio label, .stMultiSelect label {
        font-size: 20px !important;
        font-weight: bold !important;
    }
    /* Font dei Tab */
    .stTabs [data-baseweb="tab"] {
        font-size: 22px !important;
        height: 50px !important;
    }
    /* Titolo compatto */
    h1 {
        margin-top: -30px !important;
        padding-bottom: 10px !important;
        font-size: 38px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Simulazione scenari sequestro C nel suolo")

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
        height=650, # Forza l'altezza del grafico per ingrandirlo
        margin=dict(l=20, r=20, t=50, b=20), # Riduce i margini bianchi attorno al grafico
        title=dict(text=title, font=dict(size=24), y=0.98), # Alza il titolo del grafico
        xaxis=dict(range=[pd.to_datetime("2021-01-01"), pd.to_datetime("2031-01-01")], 
                   tickfont=dict(size=14), showgrid=False), 
        yaxis=dict(range=[y_min, y_max], title=dict(text="Stock di C (ton/ha)", font=dict(size=18)), 
                   tickfont=dict(size=14), showgrid=False),
        sliders=[], 
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.05, y=-0.08, # Sposta il bottone più vicino all'asse
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
    
    fig.update_traces(line=dict(width=2.5), selector=dict(name=baseline_name))
    return fig

# --- 3. DEFINIZIONE TAB ---
tab1, tab2, tab3 = st.tabs(["📊 LIVELLO 1", "🧪 LIVELLO 2", "🌍 LIVELLO 3"])

# --- LIVELLO 1 ---
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with c2: a1 = st.radio(f"Ammendante?", ["Sì", "No"], horizontal=True, key="a1")
    
    df1 = load_data(p1, a1)
    
    if df1 is not None:
        with c3:
            all_rots = df1['Rotazione'].unique()
            rots_standard = sorted([r for r in all_rots if "year" not in str(r).lower()])
            rot1 = st.selectbox("🚜 Rotazione", rots_standard, key="rot1")
        
        df_base_real = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == base_n)].copy()
        is_piacenza_cc = (p1 == "Piacenza" and a1 == "No" and "Pomodoro - Frumento" in rot1)

        if is_piacenza_cc:
            col_cc1, col_cc2 = st.columns(2)
            with col_cc1:
                modalita_cc = st.radio("🧐 **Analisi Frequenza CC?**",
                                      ["No", "Sì"], horizontal=True)

            if modalita_cc == "Sì":
                mapping_cc = {
                    "CC Anno 1": "Pomodoro - Frumento granella 1cc year1",
                    "CC Anno 3": "Pomodoro - Frumento granella 1cc year3",
                    "CC Anno 5": "Pomodoro - Frumento granella 1cc year5",
                    "CC Anni 1 e 3": "Pomodoro - Frumento granella 1cc year13",
                    "CC Anni 1 e 5": "Pomodoro - Frumento granella 1cc year15"
                }
                with col_cc2:
                    scenari_spec = [s for s in df1[df1['Rotazione'] == mapping_cc["CC Anno 1"]]['Scenario_Esteso'].unique() if s != base_n]
                    scen_cc_scelto = st.selectbox("✨ Pratica", scenari_spec)
                
                scelte_freq = st.multiselect("📅 Frequenze", list(mapping_cc.keys()))
                if scelte_freq:
                    final_targets = scelte_freq + [base_n]
                    temp_list = [ (df_base_real.assign(Legenda=base_n) if s == base_n else 
                                  pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], 
                                            df1[(df1['Rotazione'] == mapping_cc[s]) & (df1['Scenario_Esteso'] == scen_cc_scelto)][df1['Mese_Progressivo'] > 60]]).assign(Legenda=s))
                                  for s in final_targets ]
                    df_merged_scenarios = pd.concat(temp_list)
            else:
                scen_scelti = st.multiselect("✨ Scenari", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n])
                final_targets = scen_scelti + [base_n]
                df_merged_scenarios = pd.concat([pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], 
                                                          df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s)][df1['Mese_Progressivo'] > 60]]).assign(Legenda=s) 
                                                for s in final_targets])
        else:
            scen_scelti = st.multiselect("✨ Scenari", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n])
            final_targets = scen_scelti + [base_n]
            df_merged_scenarios = pd.concat([pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], 
                                                      df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s)][df1['Mese_Progressivo'] > 60]]).assign(Legenda=s) 
                                            for s in final_targets])

        if 'final_targets' in locals() and len(final_targets) > 1:
            val_2026 = df_base_real[df_base_real['Mese_Progressivo'] == 61]['total_soc'].values[0]
            anim_frames = []
            for m in range(1, 118, 4):
                for s in final_targets:
                    temp_f = (df_base_real[df_base_real['Mese_Progressivo'] <= m].copy() if m <= 60 else 
                              df_merged_scenarios[(df_merged_scenarios['Legenda'] == s) & (df_merged_scenarios['Mese_Progressivo'] <= m)].copy())
                    temp_f['Legenda_Anim'], temp_f['Frame'] = s, m
                    anim_frames.append(temp_f)
            
            df_anim = pd.concat(anim_frames)
            fig1 = px.line(df_anim, x='Data', y='total_soc', color='Legenda_Anim', animation_frame='Frame', 
                           color_discrete_map={base_n: "#0000FF"}, template="plotly_white")
            
            fig1 = apply_final_layout(fig1, df_merged_scenarios, f"Proiezione Carbonio - {p1}", base_n, [(val_2026, p1)])
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

# Nota: Tab 2 e 3 seguono la stessa logica di apply_final_layout migliorata.
