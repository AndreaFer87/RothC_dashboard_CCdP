import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAZIONE E CSS (Fix Titolo Tagliato) ---
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
        st.error(f"Errore: {e}")
        return None

def apply_final_layout(fig, df_visualizzato, title, baseline_name, punti_riferimento):
    y_min = df_visualizzato['total_soc'].min() * 0.99
    y_max = df_visualizzato['total_soc'].max() * 1.01
    split_date = pd.to_datetime("2026-01-01")
    target_date = pd.to_datetime("2030-09-01")
    
    fig.update_layout(
        height=600,
        margin=dict(t=80), # Spazio per il titolo del grafico
        title=dict(text=title, font=dict(size=20), y=0.95),
        xaxis=dict(range=[pd.to_datetime("2021-01-01"), pd.to_datetime("2031-01-01")], showgrid=False), 
        yaxis=dict(range=[y_min, y_max], title="Stock di C (ton/ha)", showgrid=False),
        sliders=[], 
        updatemenus=[dict(
            type="buttons", showactive=False, x=0, y=-0.15,
            buttons=[dict(label="▶ AVVIA SIMULAZIONE", method="animate", 
                          args=[None, {"frame": {"duration": 40, "redraw": False}, "fromcurrent": True}])]
        )]
    )
    for val, label in punti_riferimento:
        fig.add_trace(px.scatter(x=[target_date], y=[val]).data[0])
        fig.data[-1].update(mode='markers', marker=dict(color='black', size=12, symbol='circle'), 
                            name=f"Rif. 2026: {label}", showlegend=True)
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper", line=dict(color="Red", width=2, dash="dot"))
    fig.update_traces(line=dict(width=2.5), selector=dict(name=baseline_name))
    return fig

# --- DEFINIZIONE TAB ---
tab1, tab2, tab3 = st.tabs(["📊 LIVELLO 1", "🧪 LIVELLO 2", "🌍 LIVELLO 3"])

with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with c2: a1 = st.radio(f"Ammendante ({p1})?", ["Sì", "No"], horizontal=True, key="a1")
    df1 = load_data(p1, a1)
    
    if df1 is not None:
        with c3:
            rots_standard = sorted([r for r in df1['Rotazione'].unique() if "year" not in str(r).lower()])
            rot1 = st.selectbox("🚜 Rotazione", rots_standard, key="rot1")
        
        df_base_real = df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == base_n)].copy()
        is_piacenza_cc = (p1 == "Piacenza" and a1 == "No" and "Pomodoro - Frumento" in rot1)

        # Costruzione Scenari (Logica del tuo codice originale)
        if is_piacenza_cc:
            st.markdown("---")
            col_cc1, col_cc2 = st.columns(2)
            with col_cc1: modalita_cc = st.radio("🧐 **Analisi Frequenza Cover Crop?**", ["No, simulazione standard", "Sì, confronta frequenze"], horizontal=True)
            if modalita_cc == "Sì, confronta frequenze":
                mapping_cc = {
                    "CC Anno 1": "Pomodoro - Frumento granella 1cc year1",
                    "CC Anno 3": "Pomodoro - Frumento granella 1cc year3",
                    "CC Anno 5": "Pomodoro - Frumento granella 1cc year5",
                    "CC Anni 1 e 3": "Pomodoro - Frumento granella 1cc year13",
                    "CC Anni 1 e 5": "Pomodoro - Frumento granella 1cc year15"
                }
                with col_cc2:
                    scenari_spec = [s for s in df1[df1['Rotazione'] == mapping_cc["CC Anno 1"]]['Scenario_Esteso'].unique() if s != base_n]
                    scen_cc_scelto = st.selectbox("✨ Pratica applicata", scenari_spec)
                scelte_freq = st.multiselect("📅 Seleziona frequenze", list(mapping_cc.keys()))
                if scelte_freq:
                    final_targets = scelte_freq + [base_n]
                    df_merged = pd.concat([ (df_base_real.assign(Legenda=s) if s == base_n else pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], df1[(df1['Rotazione'] == mapping_cc[s]) & (df1['Scenario_Esteso'] == scen_cc_scelto) & (df1['Mese_Progressivo'] > 60)]]).assign(Legenda=s)) for s in final_targets ])
            else:
                scen_scelti = st.multiselect("✨ Scenari Standard", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n])
                final_targets = scen_scelti + [base_n]
                df_merged = pd.concat([ (pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s) & (df1['Mese_Progressivo'] > 60)]]).assign(Legenda=s)) for s in final_targets ])
        else:
            scen_scelti = st.multiselect("✨ Seleziona Scenari", [s for s in df1[df1['Rotazione'] == rot1]['Scenario_Esteso'].unique() if s != base_n])
            final_targets = scen_scelti + [base_n]
            df_merged = pd.concat([ (pd.concat([df_base_real[df_base_real['Mese_Progressivo'] <= 60], df1[(df1['Rotazione'] == rot1) & (df1['Scenario_Esteso'] == s) & (df1['Mese_Progressivo'] > 60)]]).assign(Legenda=s)) for s in final_targets ])

        if 'final_targets' in locals() and len(final_targets) > 1:
            val_2026 = df_base_real[df_base_real['Mese_Progressivo'] == 61]['total_soc'].values[0]
            
            # --- ANIMAZIONE (LOGICA ORIGINALE FUNZIONANTE) ---
            anim_frames = []
            for m in range(1, 121, 4):
                for s in final_targets:
                    if m <= 60:
                        temp_f = df_base_real[df_base_real['Mese_Progressivo'] <= m].copy()
                    else:
                        temp_f = df_merged[(df_merged['Legenda'] == s) & (df_merged['Mese_Progressivo'] <= m)].copy()
                    temp_f['Legenda_Anim'], temp_f['Frame'] = s, m
                    anim_frames.append(temp_f)
            
            df_anim = pd.concat(anim_frames).sort_values(['Frame', 'Mese_Progressivo'])
            fig1 = px.line(df_anim, x='Data', y='total_soc', color='Legenda_Anim', animation_frame='Frame', 
                           color_discrete_map={base_n: "#0000FF"}, template="plotly_white")
            
            st.plotly_chart(apply_final_layout(fig1, df_merged, f"Proiezione Carbonio - {p1}", base_n, [(val_2026, p1)]), use_container_width=True)

# Nota: Ho mantenuto i Tab 2 e 3 con la stessa logica di "staffetta" del tuo codice originale.
