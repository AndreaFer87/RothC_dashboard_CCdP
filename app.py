import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Casalasco Decarb - Comparazione", layout="wide")

# --- CSS PER TESTI GRANDI ---
st.markdown("""
    <style>
    .stSelectbox label, .stRadio label, .stMultiSelect label { font-size: 20px !important; font-weight: bold !important; color: #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

st.title("🌱 Comparazione Impatto Ammendanti")
st.markdown("Analisi incrociata: **Stesso Scenario** con e senza Ammendante")

# --- MAPPATURA SCENARI ---
def decode_scenario_exact(name):
    mapping = {
        "Baseline (CT)": "Gestione Tradizionale (Baseline)",
        "CC (CT)": "Cover crop (CT)",
        "Res (CT)": "Residui (CT)",
        "CC + Res (CT)": "Cover + Residui (Tradizionale)",
        "MT": "Minima Lavorazione",
        "MT + Res": "Minima + Residui",
        "MT + CC": "Minima + Cover",
        "MT + CC + Res": "Minima + Cover + Residui"
    }
    return mapping.get(name.strip(), name.strip())

# --- CARICAMENTO DOPPIO FILE ---
@st.cache_data
def load_comparison_data(provincia):
    files = {
        "Cremona": ("Cremona_digestate.xlsx", "Cremona_NOdigestate.xlsx", "Digestato"),
        "Mantova": ("Mantova_slurry.xlsx", "Mantova_NOslurry.xlsx", "Slurry"),
        "Piacenza": ("Piacenza_manure.xlsx", "Piacenza_NOmanure.xlsx", "Letame")
    }
    f_si, f_no, label = files[provincia]
    
    try:
        df_si = pd.read_excel(f_si)
        df_si['Ammendante'] = f"Sì {label}"
        
        df_no = pd.read_excel(f_no)
        df_no['Ammendante'] = "No Ammendante"
        
        df_total = pd.concat([df_si, df_no])
        df_total.columns = df_total.columns.str.strip()
        start_date = pd.to_datetime("2021-01-01")
        df_total['Data'] = df_total['Mese_Progressivo'].apply(lambda x: start_date + pd.DateOffset(months=int(x-1)))
        df_total['Scenario_Esteso'] = df_total['Scenario'].apply(decode_scenario_exact)
        
        # Creiamo un'etichetta unica per la legenda
        df_total['Strategia_Completa'] = df_total['Scenario_Esteso'] + " (" + df_total['Ammendante'] + ")"
        return df_total, label
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return None, None

# --- FILTRI ---
col1, col2 = st.columns(2)
with col1:
    prov = st.selectbox("📍 Seleziona Provincia", ["Cremona", "Mantova", "Piacenza"])
    df_comp, amm_name = load_comparison_data(prov)

with col2:
    if df_comp is not None:
        rot_scelta = st.selectbox("🚜 Rotazione Agricola", df_comp['Rotazione'].unique())

if df_comp is not None:
    df_filtered = df_comp[df_comp['Rotazione'] == rot_scelta].copy()
    
    # Scelta dello scenario da comparare
    scenari_unici = [s for s in df_comp['Scenario_Esteso'].unique() if "Baseline" not in s]
    scen_da_comparare = st.selectbox("✨ Scegli lo Scenario Rigenerativo da analizzare", scenari_unici)

    # Definiamo i 4 protagonisti della simulazione
    base_si = f"Gestione Tradizionale (Baseline) (Sì {amm_name})"
    base_no = "Gestione Tradizionale (Baseline) (No Ammendante)"
    scen_si = f"{scen_da_comparare} (Sì {amm_name})"
    scen_no = f"{scen_da_comparare} (No Ammendante)"
    
    scenari_attivi = [base_no, base_si, scen_no, scen_si]

    # --- LOGICA ANIMAZIONE ---
    animation_list = []
    for m in range(1, 121, 4):
        for s_label in scenari_attivi:
            # Identifichiamo i dati originali
            is_amm = "Sì" in s_label
            is_baseline = "Baseline" in s_label
            
            orig_scen = "Gestione Tradizionale (Baseline)" if is_baseline else scen_da_comparare
            orig_amm = f"Sì {amm_name}" if is_amm else "No Ammendante"
            
            if m <= 60:
                # Fino al 2026: mostriamo solo le due Baseline (Sì/No Ammendante)
                # Anche gli scenari rigenerativi ricalcano la loro rispettiva baseline
                target_scen = "Gestione Tradizionale (Baseline)"
                temp = df_filtered[(df_filtered['Scenario_Esteso'] == target_scen) & 
                                   (df_filtered['Ammendante'] == orig_amm) & 
                                   (df_filtered['Mese_Progressivo'] <= m)].copy()
            else:
                # Dopo il 2026: ognuno segue il suo dato reale
                temp = df_filtered[(df_filtered['Scenario_Esteso'] == orig_scen) & 
                                   (df_filtered['Ammendante'] == orig_amm) & 
                                   (df_filtered['Mese_Progressivo'] <= m)].copy()
            
            temp['Legenda'] = s_label
            temp['Frame'] = m
            animation_list.append(temp)

    df_anim = pd.concat(animation_list)

    # --- GRAFICO COMPARATIVO ---
    # Colori logici: Blu per Baseline, Arancio/Verde per Scenari
    color_map = {
        base_no: "#B0C4DE", # Azzurro chiaro
        base_si: "#0000FF", # Blu scuro
        scen_no: "#FF7F0E", # Arancio
        scen_si: "#2CA02C"  # Verde
    }

    fig = px.line(
        df_anim, x='Data', y='total_soc', color='Legenda',
        animation_frame='Frame',
        range_x=[df_filtered['Data'].min(), df_filtered['Data'].max()],
        range_y=[df_filtered['total_soc'].min()*0.95, df_filtered['total_soc'].max()*1.05],
        title=f"Impatto {amm_name} su {scen_da_comparare} ({prov})",
        labels={'total_soc': 'Stock di C (ton/ha)', 'Legenda': 'Combinazione'},
        color_discrete_map=color_map,
        template="plotly_white"
    )

    fig.layout.updatemenus = [dict(
        type="buttons", showactive=False, x=0, y=-0.2,
        buttons=[dict(label="▶ AVVIA COMPARAZIONE", method="animate", args=[None, {"frame": {"duration": 40}}])]
    )]
    fig.layout.sliders = [dict(visible=False)]
    
    # Linea 2026
    split_date = pd.to_datetime("2026-01-01")
    fig.add_shape(type="line", x0=split_date, x1=split_date, y0=0, y1=1, yref="paper", line=dict(color="Red", width=2, dash="dot"))

    st.plotly_chart(fig, use_container_width=True)

    # --- METRICHE DI COMPARAZIONE ---
    st.divider()
    c1, c2, c3 = st.columns(3)
    
    finali = df_filtered[df_filtered['Mese_Progressivo'] == 120]
    val_base_no = finali[finali['Strategia_Completa'] == base_no]['total_soc'].values[0]
    val_scen_si = finali[finali['Strategia_Completa'] == scen_si]['total_soc'].values[0]
    
    c1.metric("Stock Massimo (Rigenerativo + Ammendante)", f"{val_scen_si:.2f} t/ha")
    c2.metric("Differenza vs Baseline Semplice", f"{(val_scen_si - val_base_no):.2f} t/ha", delta_color="normal")
    c3.info(f"L'uso di {amm_name} potenzia l'efficacia della pratica rigenerativa.")
