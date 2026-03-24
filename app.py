# --- LIVELLO 1 ---
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: 
        p1 = st.selectbox("📍 Provincia", ["Cremona", "Mantova", "Piacenza"], key="p1")
    with c2: 
        a1 = st.radio(f"Ammendante ({p1})?", ["Sì", "No"], horizontal=True, key="a1")
    
    df1 = load_data(p1, a1)
    
    if df1 is not None:
        with c3:
            # Puliamo i nomi delle rotazioni per evitare errori di spazi
            available_rots = [str(r).strip() for r in df1['Rotazione'].unique()]
            
            # Cerchiamo la rotazione che contiene sia "Pomodoro" che "Frumento"
            target_rot_name = next((r for r in available_rots if "Pomodoro" in r and "Frumento" in r), available_rots[0])
            
            rot1 = st.selectbox("🚜 Rotazione", [target_rot_name], key="rot1")
        
        # Filtriamo il dataframe con la rotazione trovata
        df1_f = df1[df1['Rotazione'].str.strip() == rot1].copy()
        
        # Mappiamo gli scenari
        all_scens = [s for s in df1_f['Scenario_Esteso'].unique() if s != base_n]
        final_targets = []

        # --- LOGICA FREQUENZA CC ---
        st.markdown("---")
        modalita_cc = st.radio(
            "🧐 **Vuoi analizzare l'effetto della frequenza di coltivazione delle Cover Crop?**",
            ["No, simulazione standard", "Sì, confronta annate CC"],
            horizontal=True,
            key="radio_freq_cc"
        )

        # Definiamo le parole chiave per identificare i 5 scenari temporali
        # Usiamo termini molto brevi per essere sicuri di "prenderli" tutti
        cc_keywords = ["anno 1", "anno 3", "anno 5", "anni 1"]

        if modalita_cc == "Sì, confronta annate CC":
            # Filtriamo gli scenari che contengono le parole chiave
            scenari_temporali = [s for s in all_scens if any(k in s.lower() for k in cc_keywords)]
            
            if not scenari_temporali:
                st.warning("Attenzione: Non ho trovato scenari con 'anno 1, 3, 5' nel file. Controlla i nomi nel file Excel.")
            
            scen_cc_scelti = st.multiselect("📅 Varianti temporali Cover Crop", scenari_temporali, key="m_cc_only")
            final_targets = scen_cc_scelti + [base_n]
        else:
            # Escludiamo i temporali per mostrare solo gli standard (MT, residui, ecc)
            scenari_standard = [s for s in all_scens if not any(k in s.lower() for k in cc_keywords)]
            
            scen_std_scelti = st.multiselect("✨ Seleziona Scenari Rigenerativi Standard", scenari_standard, key="m1_std")
            final_targets = scen_std_scelti + [base_n]
        
        # --- GENERAZIONE GRAFICO ---
        if len(final_targets) > 1:
            df_snapshot = df1_f[df1_f['Scenario_Esteso'].isin(final_targets)]
            
            try:
                # Cerchiamo il valore del 2026 (Mese 61) della Baseline
                val_2026 = df1_f[(df1_f['Scenario_Esteso'] == base_n) & (df1_f['Mese_Progressivo'] == 61)]['total_soc'].values[0]
            except:
                val_2026 = df_snapshot['total_soc'].iloc[0]
            
            anim1 = []
            for m in range(1, 118, 4):
                for s in final_targets:
                    source = base_n if m <= 60 else s
                    temp = df1_f[(df1_f['Scenario_Esteso'] == source) & (df1_f['Mese_Progressivo'] <= m)].copy()
                    temp['Scenario_Visualizzato'], temp['Frame'] = s, m
                    anim1.append(temp)
            
            if anim1:
                fig1 = px.line(pd.concat(anim1), x='Data', y='total_soc', color='Scenario_Visualizzato', 
                               animation_frame='Frame', color_discrete_map={base_n: "#0000FF"}, template="plotly_white")
                
                fig1 = apply_final_layout(fig1, df_snapshot, f"Analisi Scenari - {p1}", base_n, [(val_2026, p1)])
                st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Scegli uno o più scenari per attivare la proiezione.")
