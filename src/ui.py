# ==============================================================================
# PLANO FIT APP - COMPONENTES DE UI
# ==============================================================================

from datetime import datetime, date

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.figure_factory as ff
import numpy as np
import matplotlib.pyplot as plt

import config
import logic
import plotting
import utils
import auth

# ==============================================================================
# TELAS DE LOGIN / PERFIL
# ==============================================================================

def render_login_screen():
    """Renderiza a tela de login, criação de perfil e reset de senha."""
    st.title(f"Bem-vindo ao {config.APP_TITLE}")
    
    if 'login_view' not in st.session_state:
        st.session_state.login_view = 'login'

    view = st.session_state.login_view

    if view == 'login':
        render_login_form()
    elif view == 'create_profile':
        render_create_profile_form()
    elif view == 'reset_password':
        render_reset_password_form()

def render_login_form():
    st.subheader("Login")
    df_users = auth.load_users()
    
    if df_users.empty:
        st.info("Nenhum perfil encontrado. Crie o primeiro perfil para começar.")
        if st.button("Criar Primeiro Perfil"):
            st.session_state.login_view = 'create_profile'
            st.rerun()
        return

    users_list = df_users['username'].tolist()
    last_login_df = df_users.sort_values('last_login', ascending=False)
    
    try:
        last_user = last_login_df['username'].iloc[0] if not last_login_df.empty else users_list[0]
        default_index = users_list.index(last_user)
    except (ValueError, IndexError):
        default_index = 0
    
    selected_user = st.selectbox("Selecione seu perfil", options=users_list, index=default_index)
    password = st.text_input("Senha", type="password")
    remember_me = st.checkbox("Permanecer conectado")

    if st.button("Entrar", type="primary"):
        user_data = df_users[df_users['username'] == selected_user]
        if not user_data.empty:
            hashed_password = user_data['password_hash'].iloc[0]
            if pd.isna(hashed_password) or auth.verify_password(password, hashed_password):
                st.session_state.logged_in = True
                st.session_state.current_user = selected_user
                
                df_users.loc[df_users['username'] == selected_user, 'last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                auth.save_users(df_users)

                if remember_me:
                    auth.set_last_user(selected_user)
                else:
                    auth.clear_last_user()
                st.rerun()
            else:
                st.error("Senha incorreta.")
        else:
            st.error("Usuário não encontrado.")

    col1, col2 = st.columns(2)
    if col1.button("Criar Novo Perfil"):
        st.session_state.login_view = 'create_profile'
        st.rerun()
    if col2.button("Esqueceu a senha?"):
        st.session_state.login_view = 'reset_password'
        st.rerun()

def render_create_profile_form():
    st.subheader("Criar Novo Perfil")
    with st.form("create_profile_form"):
        username = st.text_input("Nome do Perfil")
        password = st.text_input("Senha (deixe em branco se não desejar)", type="password")
        
        submitted = st.form_submit_button("Criar e Entrar")
        if submitted:
            df_users = auth.load_users()
            if username and username not in df_users['username'].tolist():
                new_user = pd.DataFrame([{
                    'username': username,
                    'password_hash': auth.hash_password(password) if password else None,
                    'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }])
                df_users = pd.concat([df_users, new_user], ignore_index=True)
                auth.save_users(df_users)
                
                st.session_state.logged_in = True
                st.session_state.current_user = username
                auth.set_last_user(username)
                st.success(f"Perfil '{username}' criado com sucesso!")
                st.rerun()
            else:
                st.error("Nome de perfil inválido ou já existente.")
    
    if st.button("Voltar para o Login"):
        st.session_state.login_view = 'login'
        st.rerun()

def render_reset_password_form():
    st.subheader("Redefinir Senha")
    username_to_reset = st.text_input("Digite o nome do seu perfil")

    if username_to_reset:
        df_users = auth.load_users()
        if username_to_reset in df_users['username'].tolist():
            with st.form("reset_password_form"):
                st.success(f"Perfil '{username_to_reset}' encontrado. Por favor, defina uma nova senha.")
                new_password = st.text_input("Nova Senha", type="password")
                confirm_password = st.text_input("Confirmar Nova Senha", type="password")
                
                submitted = st.form_submit_button("Redefinir Senha")
                if submitted:
                    if new_password == confirm_password:
                        new_hash = auth.hash_password(new_password) if new_password else None
                        df_users.loc[df_users['username'] == username_to_reset, 'password_hash'] = new_hash
                        auth.save_users(df_users)
                        st.success("Senha redefinida com sucesso!")
                        st.session_state.login_view = 'login'
                        st.rerun()
                    else:
                        st.error("As senhas não coincidem.")
        else:
            st.warning("Perfil não encontrado. Verifique o nome digitado.")

    if st.button("Voltar para o Login"):
        st.session_state.login_view = 'login'
        st.rerun()

# ==============================================================================
# FUNÇÕES DAS ABAS
# ==============================================================================

def render_visao_geral_tab(dados_pessoais, RECOMEND):
    """Renderiza a aba de Visão Geral."""
    st.header("✨ Visão Geral")
    
    if not dados_pessoais:
        st.error("Preencha e salve seus dados pessoais na primeira aba para ver a Visão Geral.")
        return

    username = st.session_state.current_user

    # --- Carregar Dados Necessários ---
    df_obj = utils.carregar_df(utils.get_user_data_path(username, config.FILE_OBJETIVO))
    dfe_final = utils.carregar_df(utils.get_user_data_path(username, config.FILE_EVOLUCAO))
    dft_simples = utils.carregar_df(utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES))
    objetivo_info = df_obj.iloc[0].to_dict() if not df_obj.empty else {}

    # --- 1. Progresso do Objetivo ---
    if not dfe_final.empty and objetivo_info:
        metricas_evol = logic.calcular_metricas_saude(dados_pessoais, objetivo_info)
        progresso = logic.analisar_progresso_objetivo(dfe_final, metricas_evol)
        if progresso:
            st.subheader("🏁 Progresso do Objetivo")
            c1, c2, c3 = st.columns(3)
            c1.metric("Meta de Peso", f"{metricas_evol['peso_ideal']:.1f} kg", delta=f"{progresso['objetivo_total_kg']:+.1f} kg")
            c2.metric("Progresso Atual", f"{progresso['progresso_atual_kg']:+.1f} kg", delta=f"{progresso['progresso_percent']:.1f}%")
            c3.metric("Restante para Meta", f"{progresso['restante_kg']:+.1f} kg")
            try:
                dt_inicio = datetime.strptime(objetivo_info.get("DataInicio"), "%d/%m/%Y")
                dt_fim = datetime.strptime(metricas_evol.get("data_objetivo_fmt"), "%d/%m/%Y")
                total_dias = (dt_fim - dt_inicio).days; dias_passados = (datetime.now() - dt_inicio).days
                progresso_tempo = min(dias_passados / total_dias, 1.0) if total_dias > 0 else 0
                st.progress(progresso_tempo)
                st.caption(f"Início: {dt_inicio.strftime('%d/%m/%Y')} | Conclusão Prevista: {dt_fim.strftime('%d/%m/%Y')} ({dias_passados}/{total_dias} dias)")
            except (ValueError, TypeError): 
                st.caption("Timeline indisponível. Verifique as datas do objetivo.")
    
    # --- 2. Metas de Nutrientes ---
    st.subheader("🍎 Metas de Nutrientes")
    if objetivo_info and not RECOMEND.empty:
        metricas = logic.calcular_metricas_saude(dados_pessoais, objetivo_info)
        def obter_recomendacao_diaria(sexo, objetivo, intensidade):
            filt = RECOMEND[(RECOMEND["Sexo"].str.lower() == sexo.lower()) & (RECOMEND["Objetivo"].str.lower() == objetivo.lower()) & (RECOMEND["Atividade"].str.lower() == intensidade.lower())]
            return filt.iloc[0] if not filt.empty else None
        rec = obter_recomendacao_diaria(dados_pessoais.get('sexo'), objetivo_info.get('ObjetivoPeso'), objetivo_info.get('Atividade'))
        if rec is not None:
            peso = dados_pessoais.get(config.COL_PESO, 70.0)
            prot_obj, carb_obj, gord_obj, sod_obj = float(rec.iloc[3]) * peso, float(rec.iloc[4]) * peso, float(rec.iloc[5]) * peso, float(rec.iloc[6])
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Calorias", f"{metricas.get('alvo_calorico', 0):.0f} kcal")
            c2.metric("Proteínas", f"{prot_obj:.1f} g")
            c3.metric("Carboidratos", f"{carb_obj:.1f} g")
            c4.metric("Gorduras", f"{gord_obj:.1f} g")
            c5.metric("Sódio", f"{sod_obj:.0f} mg")
            c6.metric("Água", f"{metricas.get('meta_agua_l', 0):.2f} L")

    # --- 3. Carregar Dados de Treino ---
    df_macro = utils.carregar_df(utils.get_user_data_path(username, config.FILE_MACROCICLOS))
    df_meso = utils.carregar_df(utils.get_user_data_path(username, config.FILE_MESOCICLOS))
    df_plano_sem = utils.carregar_df(utils.get_user_data_path(username, config.FILE_PLANO_SEMANAL))
    today = pd.to_datetime(date.today())
    plano_semanal_ativo = pd.DataFrame() 

    # --- 4. Histórico e Consistência ---
    stats = logic.analisar_historico_treinos(dft_simples)
    if stats:
        st.subheader("🏋️‍♂️ Histórico e Consistência")
        
        macro_ativo = df_macro[(pd.to_datetime(df_macro['data_inicio']) <= today) & (pd.to_datetime(df_macro['data_fim']) >= today)] if 'data_inicio' in df_macro.columns else pd.DataFrame()
        if not macro_ativo.empty:
            id_macro_ativo = macro_ativo['id_macrociclo'].iloc[0]
            mesos_do_macro = df_meso[df_meso['id_macrociclo'] == id_macro_ativo] if 'id_macrociclo' in df_meso.columns else pd.DataFrame()
            semanas_acumuladas, meso_ativo_info, semana_no_mes = 0, None, 0
            data_inicio_macro = pd.to_datetime(macro_ativo['data_inicio'].iloc[0])
            dias_desde_inicio_macro = (today - data_inicio_macro).days
            semana_no_macro = (dias_desde_inicio_macro // 7) + 1 if dias_desde_inicio_macro >= 0 else 0
            if semana_no_macro > 0 and not mesos_do_macro.empty and 'ordem' in mesos_do_macro.columns:
                for _, meso in mesos_do_macro.sort_values('ordem').iterrows():
                    duracao_meso = int(meso.get('duracao_semanas', 4))
                    if semana_no_macro <= semanas_acumuladas + duracao_meso:
                        meso_ativo_info = meso; semana_no_mes = semana_no_macro - semanas_acumuladas; break
                    semanas_acumuladas += duracao_meso
            if meso_ativo_info is not None:
                id_meso_ativo = meso_ativo_info['id_mesociclo']
                plano_semanal_ativo = df_plano_sem[(df_plano_sem['id_mesociclo'] == id_meso_ativo) & (df_plano_sem['semana_numero'] == semana_no_mes)]

        consistencia = logic.analisar_consistencia_habitos(dft_simples, plano_semanal_ativo)

        # KPIs organizados em duas linhas
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Sequência de Treinos", f"{consistencia['streak_dias']} dias", help="Número de dias consecutivos em que um treino foi registrado.")
        c2.metric("Adesão Semanal", f"{consistencia['adesao_percentual']}%", help=f"Percentual de treinos realizados vs. planejados na semana atual ({consistencia['dias_treinados_semana']} de {consistencia['dias_planejados_semana']}).")
        c3.metric("Treinos esta semana", f"{stats['treinos_semana_atual']}")
        c4.metric("Média/semana", f"{stats['media_treinos_semana']:.1f} treinos")
        c5.metric("Total de treinos", f"{stats['total_treinos']}")
        c6.metric("Último treino (kcal)", f"{stats['calorias_ultimo_treino']:.0f}")
        
    # --- 5. Plano da Semana ---
    macro_ativo = df_macro[(pd.to_datetime(df_macro['data_inicio']) <= today) & (pd.to_datetime(df_macro['data_fim']) >= today)] if 'data_inicio' in df_macro.columns else pd.DataFrame()
    if not macro_ativo.empty:
        id_macro_ativo = macro_ativo['id_macrociclo'].iloc[0]
        mesos_do_macro = df_meso[df_meso['id_macrociclo'] == id_macro_ativo] if 'id_macrociclo' in df_meso.columns else pd.DataFrame()
        semanas_acumuladas, meso_ativo_info, semana_no_mes = 0, None, 0
        data_inicio_macro = pd.to_datetime(macro_ativo['data_inicio'].iloc[0])
        dias_desde_inicio_macro = (today - data_inicio_macro).days
        semana_no_macro = (dias_desde_inicio_macro // 7) + 1 if dias_desde_inicio_macro >= 0 else 0
        if semana_no_macro > 0 and not mesos_do_macro.empty and 'ordem' in mesos_do_macro.columns:
            for _, meso in mesos_do_macro.sort_values('ordem').iterrows():
                duracao_meso = int(meso.get('duracao_semanas', 4))
                if semana_no_macro <= semanas_acumuladas + duracao_meso:
                    meso_ativo_info = meso; semana_no_mes = semana_no_macro - semanas_acumuladas; break
                semanas_acumuladas += duracao_meso
        if meso_ativo_info is not None:
            nome_meso_ativo = meso_ativo_info['nome']
            duracao_total_meso = int(meso_ativo_info.get('duracao_semanas', 4))
            st.subheader(f"🗓️ Plano da Semana ({nome_meso_ativo} - Semana {semana_no_mes} de {duracao_total_meso})")
            id_meso_ativo = meso_ativo_info['id_mesociclo']
            plano_semanal = df_plano_sem[(df_plano_sem['id_mesociclo'] == id_meso_ativo) & (df_plano_sem['semana_numero'] == semana_no_mes)]
            cols = st.columns(7)
            dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            dias_map_local = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
            for i, dia in enumerate(dias_semana):
                treino_do_dia = plano_semanal[plano_semanal['dia_da_semana'] == dia]['plano_treino'].iloc[0] if not plano_semanal[plano_semanal['dia_da_semana'] == dia].empty else "Não Planejado"
                with cols[i]:
                    st.markdown(f"**{dia}**")
                    # --- CÓDIGO RESTAURADO ---
                    if dia == dias_map_local.get(date.today().weekday()):
                        st.success(treino_do_dia)
                    else:
                        st.info(treino_do_dia)
    
    # --- 6. Heatmap de Atividade Anual ---
    st.subheader("🔥 Heatmap de Atividade")
    if not dft_simples.empty and 'data' in dft_simples.columns and 'calorias' in dft_simples.columns:
        dft_heat = dft_simples.copy()
        dft_heat['date'] = pd.to_datetime(dft_heat[config.COL_DATA], format="%d/%m/%Y")
        today_ts = pd.Timestamp.now().normalize()
        start_date = pd.Timestamp(date(today_ts.year, 1, 1))
        daily_activity = dft_heat.groupby(dft_heat['date'].dt.date)['calorias'].sum()
        all_days = pd.date_range(start=start_date, end=today_ts, freq='D')
        activity_values = all_days.to_series(index=all_days, name='calorias').dt.date.map(daily_activity).fillna(0)
        first_day_of_year_weekday = start_date.weekday()
        total_weeks = ((all_days.max() - all_days.min()).days + first_day_of_year_weekday) // 7 + 2
        heatmap_z = np.full((7, total_weeks), np.nan)
        heatmap_text = np.full((7, total_weeks), '', dtype=object)
        month_labels = {}
        for date_ts, activity in activity_values.items():
            weekday = date_ts.weekday()
            week_num = (date_ts.dayofyear - 1 + first_day_of_year_weekday) // 7
            heatmap_z[weekday, week_num] = activity
            heatmap_text[weekday, week_num] = f"{date_ts.strftime('%d/%m/%Y')}: {activity:.0f} kcal"
            month_name = date_ts.strftime('%b')
            if week_num > 0 and date_ts.day < 8 and month_name not in month_labels:
                month_labels[month_name] = week_num
        fig = go.Figure(data=go.Heatmap(z=heatmap_z, text=heatmap_text, hoverinfo='text', colorscale='YlGnBu', showscale=False, xgap=3, ygap=3))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(showgrid=False, zeroline=False, autorange='reversed', tickmode='array', ticktext=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'], tickvals=list(range(7))), xaxis=dict(showgrid=False, zeroline=False, tickmode='array', ticktext=list(month_labels.keys()), tickvals=list(month_labels.values())), font=dict(color='white'), height=250, margin=dict(l=30, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True, key="heatmap_geral")

def render_dados_pessoais_tab(dados_pessoais):
    """Renderiza a aba de Dados Pessoais."""
    st.header("👤 Dados pessoais")
    row = dados_pessoais if dados_pessoais else {}
    with st.form("form_pessoais"):
        c1, c2, c3, c4 = st.columns(4)
        nome = c1.text_input("Nome", value=row.get("nome", ""))
        nascimento = c2.text_input("Nascimento (DD/MM/AAAA)", value=row.get("nascimento", ""))
        altura = c3.number_input("Altura (m)", 0.5, 2.5, float(row.get("altura", 1.70) or 1.70), 0.01)
        sexo = c4.selectbox("Sexo", config.OPCOES_SEXO, index=config.OPCOES_SEXO.index(row.get("sexo", "M")))
        
        user_path = utils.get_user_data_path(st.session_state.current_user, config.FILE_EVOLUCAO)
        dfe_evol = utils.carregar_df(user_path)
        peso_recente = float(dfe_evol[config.COL_PESO].iloc[-1]) if not dfe_evol.empty and config.COL_PESO in dfe_evol.columns else None
        peso_val = peso_recente if peso_recente is not None else float(row.get(config.COL_PESO, 70.0) or 70.0)
        
        c5, c6, c7 = st.columns(3)
        peso = c5.number_input("Peso (kg)", 20.0, 400.0, peso_val, 0.1)
        gord_corp = c6.number_input("Gordura corporal (%)", 0.0, 80.0, float(row.get("gordura_corporal", 0.0) or 0.0), 0.1)
        gord_visc = c7.number_input("Gordura visceral (%)", 0.0, 100.0, float(row.get("gordura_visceral", 0.0) or 0.0), 0.1)
        musculo = st.number_input("Massa muscular (%)", 0.0, 100.0, float(row.get("massa_muscular", 0.0) or 0.0), 0.1)
        
        submitted = st.form_submit_button("Salvar dados pessoais")
    
    if submitted:
        try:
            data_nasc = datetime.strptime(nascimento, "%d/%m/%Y")
            hoje = datetime.today()
            idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
        except ValueError:
            idade = 0
            st.warning("Formato de data de nascimento inválido.")
        
        df_novo = pd.DataFrame([{"nome": nome, "nascimento": nascimento, "altura": altura, "sexo": sexo, "peso": peso, "idade": idade, "gordura_corporal": gord_corp, "gordura_visceral": gord_visc, "massa_muscular": musculo}])
        utils.salvar_df(df_novo, utils.get_user_data_path(st.session_state.current_user, config.FILE_DADOS_PESSOAIS))
        st.success("Dados pessoais salvos!")
        st.rerun()

def render_objetivos_tab(dados_pessoais):
    """Renderiza a aba de Objetivos e Metas."""
    st.header("🎯 Objetivo & Metas")
    if dados_pessoais:
        df_obj = utils.carregar_df(utils.get_user_data_path(st.session_state.current_user, config.FILE_OBJETIVO))
        objetivo_info = df_obj.iloc[0].to_dict() if not df_obj.empty else {}
        with st.form("form_obj"):
            c1, c2, c3, c4 = st.columns(4)
            inicio_objetivo = c1.text_input("Início do objetivo (DD/MM/AAAA)", value=objetivo_info.get("DataInicio", date.today().strftime("%d/%m/%Y")))
            intensidade = c2.selectbox("Nível de atividade", config.OPCOES_NIVEL_ATIVIDADE, index=config.OPCOES_NIVEL_ATIVIDADE.index(objetivo_info.get("Atividade", "moderado")))
            ambiente = c3.selectbox("Ambiente", config.OPCOES_AMBIENTE, index=config.OPCOES_AMBIENTE.index(objetivo_info.get("Ambiente", "ameno")))
            objetivo = c4.selectbox("Objetivo de peso", config.OPCOES_OBJETIVO_PESO, index=config.OPCOES_OBJETIVO_PESO.index(objetivo_info.get("ObjetivoPeso", "manutencao")))
            if st.form_submit_button("Salvar objetivo"):
                df_obj_novo = pd.DataFrame([{"DataInicio": inicio_objetivo, "Atividade": intensidade, "Ambiente": ambiente, "ObjetivoPeso": objetivo}])
                utils.salvar_df(df_obj_novo, utils.get_user_data_path(st.session_state.current_user, config.FILE_OBJETIVO))
                st.success("Objetivo salvo!")
                st.rerun()

        objetivo_info = {"DataInicio": inicio_objetivo, "Atividade": intensidade, "Ambiente": ambiente, "ObjetivoPeso": objetivo}
        metricas = logic.calcular_metricas_saude(dados_pessoais, objetivo_info)
        
        def classificar_imc(v):
            if v < 18.5: return "(Abaixo do peso)"
            if v <= 24.9: return "(Peso normal)"
            if v <= 29.9: return "(Sobrepeso)"
            if v <= 35: return "(Obesidade grau I)"
            if v <= 40: return "(Obesidade grau II)"
            return "(Obesidade grau III)"
            
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("IMC", f"{metricas['IMC']:.2f}", classificar_imc(metricas['IMC']))
        m2.metric("TMB (Repouso)", f"{metricas['TMB']:.0f} kcal")
        m3.metric("Gasto Diário (TDEE)", f"{metricas['TDEE']:.0f} kcal")
        m4.metric("Alvo Calórico", f"{metricas['alvo_calorico']:.0f} kcal")
        m5.metric("Água/dia", f"{metricas['meta_agua_l']:.2f} L")
        m6.metric("Peso Ideal (IMC 24.9)", f"{metricas['peso_ideal']:.1f} kg")
        st.info(f"Variação semanal: **{metricas['var_semanal_kg']:+.2f} kg** ({metricas['var_semanal_percent']:+.2f}%) • Conclusão: **{metricas['data_objetivo_fmt']}** ({metricas['dias_restantes']} dias)")
        
        st.subheader("🧪 Classificações e Análises Visuais")
        classificacoes = logic.classificar_composicao_corporal(dados_pessoais.get('gordura_corporal', 0), dados_pessoais.get('gordura_visceral', 0), dados_pessoais.get('massa_muscular', 0), dados_pessoais.get('sexo', 'M'))
        
        colX, colY, colZ = st.columns(3)
        ranges_gordura = {"M": (11, 20), "F": (21, 30)}
        ranges_visceral = {"M": (0, 9), "F": (0, 9)} 
        ranges_musculo = {"M": (34, 39), "F": (24, 29)}

        with colX:
            st.info(f"Gordura corporal: **{dados_pessoais.get('gordura_corporal', 0):.1f}%** — {classificacoes['gordura']}")
            plotting.plot_composition_range("Faixa de Gordura Corporal (%)", dados_pessoais.get('gordura_corporal', 0), ranges_gordura[dados_pessoais.get('sexo','M')], (0, 50))
        with colY:
            st.info(f"Gordura visceral: **{dados_pessoais.get('gordura_visceral', 0):.1f}%** — {classificacoes['visceral']}")
            plotting.plot_composition_range("Faixa de Gordura Visceral", dados_pessoais.get('gordura_visceral', 0), ranges_visceral[dados_pessoais.get('sexo','M')], (0, 30))
        with colZ:
            st.info(f"Massa muscular: **{dados_pessoais.get('massa_muscular', 0):.1f}%** — {classificacoes['musculo']}")
            plotting.plot_composition_range("Faixa de Massa Muscular (%)", dados_pessoais.get('massa_muscular', 0), ranges_musculo[dados_pessoais.get('sexo','M')], (0, 60))

        st.markdown("---")
        st.subheader("📊 Composição Energética")
        plotting.plot_energy_composition(metricas['TMB'], metricas['TDEE'], metricas['alvo_calorico'])
    else:
        st.error("Preencha e salve seus dados pessoais na primeira aba.")

def render_alimentacao_tab(dados_pessoais, TABELA_ALIM, RECOMEND):
    """Renderiza a aba de Alimentação com o Assistente de Adição mostrando detalhes nutricionais."""
    st.header("🍽️ Alimentação")
    username = st.session_state.current_user

    # --- Carregamento de Dados ---
    path_refeicoes = utils.get_user_data_path(username, config.FILE_REFEICOES)
    df_refeicoes = utils.carregar_df(path_refeicoes)
    path_planos = utils.get_user_data_path(username, config.FILE_PLANOS_ALIMENTARES)
    df_planos_alimentares = utils.carregar_df(path_planos)

    # --- Layout Principal ---
    col_refeicoes, col_assistente = st.columns([0.6, 0.4])

    with col_refeicoes:
        st.subheader("🔢 Totais Consumidos")
        total = {config.COL_ENERGIA: 0.0, config.COL_PROTEINA: 0.0, config.COL_CARBOIDRATO: 0.0, config.COL_LIPIDEOS: 0.0, config.COL_SODIO: 0.0}
        alimentos_nao_encontrados = []

        if not df_refeicoes.empty and not TABELA_ALIM.empty:
            for _, row in df_refeicoes.iterrows():
                alimento, qtd = str(row.get("Alimento", "")), float(row.get("Quantidade", 0.0) or 0.0)
                if not alimento or qtd <= 0: continue
                proc = utils.normalizar_texto(alimento)
                linha = TABELA_ALIM[TABELA_ALIM[config.COL_ALIMENTO_PROC].str.contains(proc, na=False)]
                if not linha.empty:
                    fator = qtd / 100.0
                    for col in total.keys():
                        if col in linha.columns:
                            valor = utils.limpar_valor_numerico(linha.iloc[0][col])
                            total[col] += valor * fator
                else:
                    alimentos_nao_encontrados.append(alimento)
        
        if alimentos_nao_encontrados:
            st.warning(f"Alimentos não encontrados na base: {', '.join(set(alimentos_nao_encontrados))}")
        
        df_obj = utils.carregar_df(utils.get_user_data_path(username, config.FILE_OBJETIVO))
        objetivo_info_alim = df_obj.iloc[0].to_dict() if not df_obj.empty else {}
        
        if not objetivo_info_alim:
            st.warning("Defina seus objetivos na aba 'Objetivos & Metas' para visualizar o progresso em relação às metas.")
        elif RECOMEND.empty:
            st.info("Carregue o arquivo de recomendações na barra lateral para ver o progresso das metas.")
        else:
            metricas_alim = logic.calcular_metricas_saude(dados_pessoais, objetivo_info_alim)
            alvo_calorico = metricas_alim.get('alvo_calorico', 0)
            
            def obter_recomendacao_diaria(sexo, objetivo, intensidade):
                filt = RECOMEND[(RECOMEND["Sexo"].str.lower() == sexo.lower()) & (RECOMEND["Objetivo"].str.lower() == objetivo.lower()) & (RECOMEND["Atividade"].str.lower() == intensidade.lower())]
                return filt.iloc[0] if not filt.empty else None
            
            rec = obter_recomendacao_diaria(dados_pessoais.get('sexo'), objetivo_info_alim.get('ObjetivoPeso'), objetivo_info_alim.get('Atividade'))
            
            if rec is not None:
                peso = dados_pessoais.get(config.COL_PESO, 70.0)
                prot_obj, carb_obj, gord_obj, sod_obj = float(rec.iloc[3]) * peso, float(rec.iloc[4]) * peso, float(rec.iloc[5]) * peso, float(rec.iloc[6])
                
                total[config.COL_ENERGIA] = 0 if pd.isna(total[config.COL_ENERGIA]) else total[config.COL_ENERGIA]
                total[config.COL_PROTEINA] = 0 if pd.isna(total[config.COL_PROTEINA]) else total[config.COL_PROTEINA]
                total[config.COL_CARBOIDRATO] = 0 if pd.isna(total[config.COL_CARBOIDRATO]) else total[config.COL_CARBOIDRATO]
                total[config.COL_LIPIDEOS] = 0 if pd.isna(total[config.COL_LIPIDEOS]) else total[config.COL_LIPIDEOS]
                total[config.COL_SODIO] = 0 if pd.isna(total[config.COL_SODIO]) else total[config.COL_SODIO]
                alvo_calorico = 0 if pd.isna(alvo_calorico) else alvo_calorico
                prot_obj = 0 if pd.isna(prot_obj) else prot_obj
                carb_obj = 0 if pd.isna(carb_obj) else carb_obj
                gord_obj = 0 if pd.isna(gord_obj) else gord_obj
                sod_obj = 0 if pd.isna(sod_obj) else sod_obj

                percent_cal = round((total[config.COL_ENERGIA] / alvo_calorico * 100) if alvo_calorico > 0 else 0, 2)
                color_cal, arrow_cal = ("#28a745", "✓") if 90 <= percent_cal <= 110 else ("#dc3545", "↑" if percent_cal > 110 else "↓")
                percent_prot = round((total[config.COL_PROTEINA] / prot_obj * 100) if prot_obj > 0 else 0, 2)
                color_prot, arrow_prot = ("#28a745", "✓") if 90 <= percent_prot <= 110 else ("#dc3545", "↑" if percent_prot > 110 else "↓")
                percent_carb = round((total[config.COL_CARBOIDRATO] / carb_obj * 100) if carb_obj > 0 else 0, 2)
                color_carb, arrow_carb = ("#28a745", "✓") if 90 <= percent_carb <= 110 else ("#dc3545", "↑" if percent_carb > 110 else "↓")
                percent_gord = round((total[config.COL_LIPIDEOS] / gord_obj * 100) if gord_obj > 0 else 0, 2)
                color_gord, arrow_gord = ("#28a745", "✓") if 90 <= percent_gord <= 110 else ("#dc3545", "↑" if percent_gord > 110 else "↓")
                percent_sod = round((total[config.COL_SODIO] / sod_obj * 100) if sod_obj > 0 else 0, 2)
                color_sod, arrow_sod = ("#28a745", "✓") if percent_sod <= 100 else ("#dc3545", "↑")
                
                cA, cB, cC, cD, cE = st.columns(5)
                with cA:
                    st.metric("Calorias", f"{total[config.COL_ENERGIA]:.0f} kcal"); st.markdown(f'<p style="color:{color_cal}; margin-top:-10px;">{arrow_cal} {percent_cal:.0f}% do alvo</p>', unsafe_allow_html=True)
                with cB:
                    st.metric("Proteína", f"{total[config.COL_PROTEINA]:.1f} g"); st.markdown(f'<p style="color:{color_prot}; margin-top:-10px;">{arrow_prot} {percent_prot:.0f}% do alvo</p>', unsafe_allow_html=True)
                with cC:
                    st.metric("Carboidrato", f"{total[config.COL_CARBOIDRATO]:.1f} g"); st.markdown(f'<p style="color:{color_carb}; margin-top:-10px;">{arrow_carb} {percent_carb:.0f}% do alvo</p>', unsafe_allow_html=True)
                with cD:
                    st.metric("Gorduras", f"{total[config.COL_LIPIDEOS]:.1f} g"); st.markdown(f'<p style="color:{color_gord}; margin-top:-10px;">{arrow_gord} {percent_gord:.0f}% do alvo</p>', unsafe_allow_html=True)
                with cE:
                    st.metric("Sódio", f"{total[config.COL_SODIO]:.0f} mg"); st.markdown(f'<p style="color:{color_sod}; margin-top:-10px;">{arrow_sod} {percent_sod:.0f}% do alvo</p>', unsafe_allow_html=True)

        st.markdown("---")

        st.subheader("Refeições do Dia")
        edited_df = st.data_editor(
            df_refeicoes,
            num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "Refeicao": st.column_config.SelectboxColumn("Refeição", options=config.OPCOES_REFEICOES, required=True),
                "Alimento": st.column_config.TextColumn("Alimento", required=True),
                "Quantidade": st.column_config.NumberColumn("Quantidade (g)", min_value=0.0, step=1.0)
            }, key="editor_refeicoes_dia"
        )
        if st.button("💾 Salvar Alterações Manuais"):
            utils.salvar_df(edited_df, path_refeicoes)
            st.success("Alterações salvas!")
            st.rerun()

    with col_assistente:
        st.subheader("✨ Assistente de Adição")
        alvo_adicao = st.radio("Adicionar para:", ("Refeições do Dia", "Plano Alimentar"), horizontal=True)
        plano_alvo_nome = None
        if alvo_adicao == "Plano Alimentar":
            lista_planos_existentes = df_planos_alimentares['nome_plano'].unique().tolist() if 'nome_plano' in df_planos_alimentares.columns else []
            if not lista_planos_existentes:
                st.info("Crie um plano no gerenciador abaixo para poder adicionar alimentos a ele.")
                return 
            plano_alvo_nome = st.selectbox("Selecione o Plano Alvo:", options=lista_planos_existentes)
        
        refeicao_escolhida = st.selectbox("Adicionar à Refeição:", options=config.OPCOES_REFEICOES)
        termo_busca = st.text_input("Buscar Alimento:")
        
        resultados_df = pd.DataFrame()
        if termo_busca and not TABELA_ALIM.empty:
            termo_proc = utils.normalizar_texto(termo_busca)
            resultados_df = TABELA_ALIM[TABELA_ALIM[config.COL_ALIMENTO_PROC].str.contains(termo_proc, na=False)].head(10)
        
        if not resultados_df.empty:
            # --- NOVA LÓGICA DE EXIBIÇÃO ---
            def format_food_details(index):
                row = resultados_df.loc[index]
                return (
                    f"{row[config.COL_ALIMENTO]} "
                    f"(100g: {row[config.COL_ENERGIA]:.0f}kcal, "
                    f"P:{row[config.COL_PROTEINA]:.1f}g, "
                    f"C:{row[config.COL_CARBOIDRATO]:.1f}g, "
                    f"G:{row[config.COL_LIPIDEOS]:.1f}g)"
                )

            selected_index = st.radio(
                "Selecione um alimento:",
                options=resultados_df.index,
                format_func=format_food_details,
                key=f"radio_details_{termo_busca}"
            )
            
            alimento_selecionado = resultados_df.loc[selected_index][config.COL_ALIMENTO]
            quantidade = st.number_input("Quantidade (g):", min_value=1, value=100, step=10)

            if st.button("➕ Adicionar Alimento", type="primary", use_container_width=True):
                if alvo_adicao == "Refeições do Dia":
                    nova_refeicao = pd.DataFrame([{"Refeicao": refeicao_escolhida, "Alimento": alimento_selecionado, "Quantidade": quantidade}])
                    df_atualizado = pd.concat([df_refeicoes, nova_refeicao], ignore_index=True)
                    utils.salvar_df(df_atualizado, path_refeicoes)
                    st.success(f"'{alimento_selecionado}' adicionado às refeições do dia!")
                    st.rerun()
                elif alvo_adicao == "Plano Alimentar" and plano_alvo_nome:
                    novo_item_plano = pd.DataFrame([{'nome_plano': plano_alvo_nome, 'Refeicao': refeicao_escolhida, 'Alimento': alimento_selecionado, 'Quantidade': quantidade}])
                    df_planos_atualizado = pd.concat([df_planos_alimentares, novo_item_plano], ignore_index=True)
                    utils.salvar_df(df_planos_atualizado, path_planos)
                    st.session_state.sb_planos_alim = plano_alvo_nome
                    st.success(f"'{alimento_selecionado}' adicionado ao plano '{plano_alvo_nome}'!")
                    st.rerun()
        elif termo_busca:
            st.info("Nenhum alimento encontrado.")

    # --- Gerenciamento de Planos ---
    with st.expander("Gerenciar Meus Planos Alimentares", expanded=True):
        lista_planos = ["-- Criar Novo Plano --"] + (df_planos_alimentares['nome_plano'].unique().tolist() if 'nome_plano' in df_planos_alimentares.columns else [])
        if 'sb_planos_alim' not in st.session_state or st.session_state.sb_planos_alim not in lista_planos:
            st.session_state.sb_planos_alim = lista_planos[0]
        plano_selecionado = st.selectbox("Selecione um plano para editar ou crie um novo:", options=lista_planos, key="sb_planos_alim")
        if plano_selecionado == "-- Criar Novo Plano --":
            novo_nome_plano = st.text_input("Nome do Novo Plano Alimentar (ex: Dia de Treino Intenso)")
            if st.button("Criar Plano Alimentar"):
                if novo_nome_plano and novo_nome_plano not in lista_planos:
                    novo_plano_df = pd.DataFrame([{'nome_plano': novo_nome_plano, 'Refeicao': config.OPCOES_REFEICOES[0], 'Alimento': 'Exemplo (edite)', 'Quantidade': 100.0}])
                    df_planos_atualizado = pd.concat([df_planos_alimentares, novo_plano_df], ignore_index=True)
                    utils.salvar_df(df_planos_atualizado, path_planos)
                    st.session_state.sb_planos_alim = novo_nome_plano
                    st.success(f"Plano '{novo_nome_plano}' criado!")
                    st.rerun()
                else:
                    st.error("Nome de plano inválido ou já existente.")
        elif plano_selecionado != "-- Criar Novo Plano --":
            st.markdown(f"**Editando o plano: {plano_selecionado}**")
            itens_plano = df_planos_alimentares[df_planos_alimentares['nome_plano'] == plano_selecionado].copy()
            itens_para_editar = itens_plano[["Refeicao", "Alimento", "Quantidade"]].copy()
            itens_editados = st.data_editor(
                itens_para_editar, num_rows="dynamic", use_container_width=True, key=f"editor_plano_alim_{plano_selecionado}",
                column_config={
                    "Refeicao": st.column_config.SelectboxColumn("Refeição", options=config.OPCOES_REFEICOES, required=True),
                    "Alimento": st.column_config.TextColumn("Alimento", required=True),
                    "Quantidade": st.column_config.NumberColumn("Quantidade (g)", min_value=0.0, step=1.0)
                }
            )
            c1, c2, c3 = st.columns(3)
            if c1.button("💾 Salvar Alterações no Plano"):
                df_outros_planos = df_planos_alimentares[df_planos_alimentares['nome_plano'] != plano_selecionado]
                novos_itens = itens_editados.copy().dropna(subset=['Alimento'])
                novos_itens['nome_plano'] = plano_selecionado
                df_final = pd.concat([df_outros_planos, novos_itens], ignore_index=True)
                utils.salvar_df(df_final, path_planos)
                st.success(f"Plano '{plano_selecionado}' salvo com sucesso!")
                st.rerun()
            if c2.button("🚀 Carregar este Plano para Hoje"):
                utils.salvar_df(itens_editados, path_refeicoes)
                st.success(f"Plano '{plano_selecionado}' carregado no dia de hoje.")
                st.rerun()
            if c3.button(f"🗑️ Apagar Plano '{plano_selecionado}'", type="secondary"):
                df_planos_alimentares = df_planos_alimentares[df_planos_alimentares['nome_plano'] != plano_selecionado]
                utils.salvar_df(df_planos_alimentares, path_planos)
                st.session_state.sb_planos_alim = lista_planos[0]
                st.success(f"Plano '{plano_selecionado}' apagado.")
                st.rerun()

def render_treino_tab(dados_pessoais):
    """Renderiza a aba de Treino."""
    st.header("🏋️‍♀️ Treino")
    
    if dados_pessoais:
        username = st.session_state.current_user
        
        df_planos_treino = utils.carregar_df(utils.get_user_data_path(username, config.FILE_PLANOS_TREINO))
        dft_simples = utils.carregar_df(utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES))

        sub_tab_vis, sub_tab_plan, sub_tab_reg = st.tabs([
            "Visão Geral", "Planejamento Completo", "Registrar Treino Realizado"
        ])

        with sub_tab_vis:
            render_visao_geral_sub_tab(username)

        with sub_tab_plan:
            render_planejamento_sub_tab(username, df_planos_treino)

        with sub_tab_reg:
            render_registro_sub_tab(username, dados_pessoais, dft_simples, df_planos_treino)
    
    else:
        st.error("Preencha e salve seus dados pessoais na primeira aba.")
        
def render_visao_geral_sub_tab(username):
    df_macro = utils.carregar_df(utils.get_user_data_path(username, config.FILE_MACROCICLOS))
    df_meso = utils.carregar_df(utils.get_user_data_path(username, config.FILE_MESOCICLOS))
    df_plano_sem = utils.carregar_df(utils.get_user_data_path(username, config.FILE_PLANO_SEMANAL))
    today = pd.to_datetime(date.today())

    macro_ativo = df_macro[
        (pd.to_datetime(df_macro['data_inicio']) <= today) & 
        (pd.to_datetime(df_macro['data_fim']) >= today)
    ] if 'data_inicio' in df_macro.columns else pd.DataFrame()

    if not macro_ativo.empty:
        id_macro_ativo = macro_ativo['id_macrociclo'].iloc[0]
        nome_macro_ativo = macro_ativo['nome'].iloc[0]
        st.markdown(f"#### Plano Ativo: **{nome_macro_ativo}**")

        mesos_do_macro = df_meso[df_meso['id_macrociclo'] == id_macro_ativo] if 'id_macrociclo' in df_meso.columns else pd.DataFrame()
        if not mesos_do_macro.empty and 'ordem' in mesos_do_macro.columns:
            data_inicio_macro = pd.to_datetime(macro_ativo['data_inicio'].iloc[0])
            gantt_data = []
            start_date = data_inicio_macro
            
            for _, meso in mesos_do_macro.sort_values('ordem').iterrows():
                duracao_semanas = int(meso.get('duracao_semanas', 4))
                end_date = start_date + pd.DateOffset(weeks=duracao_semanas)
                gantt_data.append(dict(Task=meso['nome'], Start=start_date, Finish=end_date, Resource=meso['foco_principal']))
                start_date = end_date

            if gantt_data:
                fig = ff.create_gantt(gantt_data, index_col='Task', show_colorbar=False, group_tasks=True, title='Fases do Treino (Mesociclos)')
                fig.add_vline(x=today, y0=0.1, y1=0.9, line_width=2, line_dash="dash", line_color="red", name="Hoje")
                fig.update_layout(xaxis_title="Tempo", yaxis_title="Mesociclo")
                st.plotly_chart(fig, use_container_width=True)

        semanas_acumuladas = 0
        meso_ativo_info = None
        semana_no_mes = 0
        data_inicio_macro = pd.to_datetime(macro_ativo['data_inicio'].iloc[0])
        dias_desde_inicio_macro = (today - data_inicio_macro).days
        semana_no_macro = (dias_desde_inicio_macro // 7) + 1 if dias_desde_inicio_macro >= 0 else 0

        if semana_no_macro > 0 and not mesos_do_macro.empty and 'ordem' in mesos_do_macro.columns:
            for _, meso in mesos_do_macro.sort_values('ordem').iterrows():
                duracao_meso = int(meso.get('duracao_semanas', 4))
                if semana_no_macro <= semanas_acumuladas + duracao_meso:
                    meso_ativo_info = meso
                    semana_no_mes = semana_no_macro - semanas_acumuladas
                    break
                semanas_acumuladas += duracao_meso
        
        if meso_ativo_info is not None:
            nome_meso_ativo = meso_ativo_info['nome']
            duracao_total_meso = int(meso_ativo_info.get('duracao_semanas', 4))
            st.markdown(f"##### Plano da Semana Atual ({nome_meso_ativo} - Semana {semana_no_mes} de {duracao_total_meso})")

            id_meso_ativo = meso_ativo_info['id_mesociclo']
            plano_semanal = df_plano_sem[(df_plano_sem['id_mesociclo'] == id_meso_ativo) & (df_plano_sem['semana_numero'] == semana_no_mes)]
            
            cols = st.columns(7)
            dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            dias_map_local = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
            
            for i, dia in enumerate(dias_semana):
                treino_do_dia = plano_semanal[plano_semanal['dia_da_semana'] == dia]['plano_treino'].iloc[0] if not plano_semanal[plano_semanal['dia_da_semana'] == dia].empty else "Não Planejado"
                with cols[i]:
                    st.markdown(f"**{dia}**")
                    if dia == dias_map_local[date.today().weekday()]:
                        st.success(treino_do_dia)
                    else:
                        st.info(treino_do_dia)
        else:
            st.warning("Nenhum mesociclo encontrado para a semana atual.")
    else:
        st.info("Nenhum macrociclo ativo para a data de hoje. Crie e planeje um na aba 'Planejamento Completo'.")

def render_planejamento_sub_tab(username, df_planos_treino):
    st.subheader("Planejamento Completo do Treino")

    with st.expander("Passo 1: Crie e Gerencie seus Modelos de Plano de Treino (Ex: Treino A, Treino B)", expanded=True):
        df_planos = df_planos_treino
        
        c1, c2 = st.columns([1,2])
        with c1:
            if 'id_plano' not in df_planos.columns:
                df_planos = pd.DataFrame(columns=['id_plano', 'nome_plano'])
            lista_planos = ["-- Criar Novo Plano --"] + df_planos['nome_plano'].tolist()
            opcao_plano = st.selectbox("Selecione um plano para editar ou crie um novo", options=lista_planos, key="sb_planos_unificado")

            if opcao_plano == "-- Criar Novo Plano --":
                novo_nome_plano = st.text_input("Nome do Novo Plano")
                if st.button("Criar Plano"):
                    if novo_nome_plano and novo_nome_plano not in df_planos['nome_plano'].tolist():
                        novo_id = df_planos['id_plano'].max() + 1 if not df_planos.empty else 1
                        novo_plano_df = pd.DataFrame([{'id_plano': novo_id, 'nome_plano': novo_nome_plano}])
                        df_planos = pd.concat([df_planos, novo_plano_df], ignore_index=True)
                        utils.salvar_df(df_planos, utils.get_user_data_path(username, config.FILE_PLANOS_TREINO))
                        st.success(f"Plano '{novo_nome_plano}' criado!")
                        st.rerun()
                    else:
                        st.error("Nome de plano inválido ou já existente.")
            
            elif opcao_plano != "-- Criar Novo Plano --":
                if st.button(f"🗑️ Apagar Plano '{opcao_plano}'"):
                    st.session_state[f'confirm_delete_plano_{opcao_plano}'] = True
                
                if st.session_state.get(f'confirm_delete_plano_{opcao_plano}', False):
                    st.warning(f"Tem certeza que deseja apagar o plano '{opcao_plano}'?")
                    col_conf1, col_conf2 = st.columns(2)
                    if col_conf1.button("Sim, apagar", type="primary"):
                        id_plano_para_apagar = df_planos[df_planos['nome_plano'] == opcao_plano]['id_plano'].iloc[0]
                        df_planos = df_planos[df_planos['id_plano'] != id_plano_para_apagar]
                        utils.salvar_df(df_planos, utils.get_user_data_path(username, config.FILE_PLANOS_TREINO))
                        st.success(f"Plano '{opcao_plano}' apagado.")
                        st.session_state[f'confirm_delete_plano_{opcao_plano}'] = False
                        st.rerun()
                    if col_conf2.button("Cancelar"):
                        st.session_state[f'confirm_delete_plano_{opcao_plano}'] = False
                        st.rerun()

        with c2:
            if opcao_plano != "-- Criar Novo Plano --":
                st.markdown(f"**Exercícios do Plano: {opcao_plano}**")
                id_plano_selecionado = df_planos[df_planos['nome_plano'] == opcao_plano]['id_plano'].iloc[0]
                df_exercicios_todos = utils.carregar_df(utils.get_user_data_path(username, config.FILE_PLANOS_EXERCICIOS))
                if 'id_plano' not in df_exercicios_todos.columns:
                   df_exercicios_todos = pd.DataFrame(columns=['id_plano', 'nome_exercicio', 'series_planejadas', 'repeticoes_planejadas'])

                df_exercicios_plano = df_exercicios_todos[df_exercicios_todos['id_plano'] == id_plano_selecionado].copy()
                
                exercicios_editados = st.data_editor(
                    df_exercicios_plano[['nome_exercicio', 'series_planejadas', 'repeticoes_planejadas']],
                    num_rows="dynamic", use_container_width=True, key=f"editor_exercicios_unificado_{id_plano_selecionado}",
                    column_config={ "nome_exercicio": "Exercício", "series_planejadas": "Séries", "repeticoes_planejadas": "Repetições (ex: 8-12)"}
                )

                if st.button("💾 Salvar Exercícios neste Plano"):
                    df_exercicios_outros = df_exercicios_todos[df_exercicios_todos['id_plano'] != id_plano_selecionado]
                    novos_exercicios = exercicios_editados.copy()
                    novos_exercicios['id_plano'] = id_plano_selecionado
                    df_final = pd.concat([df_exercicios_outros, novos_exercicios], ignore_index=True)
                    utils.salvar_df(df_final, utils.get_user_data_path(username, config.FILE_PLANOS_EXERCICIOS))
                    st.success("Exercícios do plano salvos com sucesso!")

    st.markdown("---")
    
    st.markdown("### Passo 2: Estruture a Periodização (Macro, Meso, Micro)")
    
    df_macro = utils.carregar_df(utils.get_user_data_path(username, config.FILE_MACROCICLOS))
    df_meso = utils.carregar_df(utils.get_user_data_path(username, config.FILE_MESOCICLOS))
    df_plano_sem = utils.carregar_df(utils.get_user_data_path(username, config.FILE_PLANO_SEMANAL))
    
    st.markdown("##### 1. Macrociclo")
    lista_macros = ["-- Criar Novo --"] + df_macro['nome'].tolist() if 'nome' in df_macro.columns else ["-- Criar Novo --"]
    
    col1_macro, col2_macro = st.columns([3, 1])
    macro_selecionado_nome = col1_macro.selectbox("Selecione o Macrociclo", options=lista_macros, key="macro_select_planning")

    if macro_selecionado_nome != "-- Criar Novo --":
        with col2_macro:
            st.write("") 
            st.write("")
            if st.button(f"🗑️ Apagar Macrociclo '{macro_selecionado_nome}'"):
                st.session_state[f'confirm_delete_macro_{macro_selecionado_nome}'] = True

            if st.session_state.get(f'confirm_delete_macro_{macro_selecionado_nome}', False):
                st.warning(f"Tem certeza que deseja remover o macrociclo '{macro_selecionado_nome}' e TUDO associado a ele?")
                col_conf1, col_conf2 = st.columns(2)
                if col_conf1.button("Sim, apagar", type="primary", key="del_macro"):
                    id_macro_para_apagar = df_macro[df_macro['nome'] == macro_selecionado_nome]['id_macrociclo'].iloc[0]
                    
                    ids_meso_para_apagar = df_meso[df_meso['id_macrociclo'] == id_macro_para_apagar]['id_mesociclo'].tolist() if 'id_macrociclo' in df_meso.columns else []
                    if ids_meso_para_apagar and 'id_mesociclo' in df_plano_sem.columns:
                        df_plano_sem = df_plano_sem[~df_plano_sem['id_mesociclo'].isin(ids_meso_para_apagar)]
                        utils.salvar_df(df_plano_sem, utils.get_user_data_path(username, config.FILE_PLANO_SEMANAL))
                    
                    if 'id_macrociclo' in df_meso.columns:
                        df_meso = df_meso[df_meso['id_macrociclo'] != id_macro_para_apagar]
                        utils.salvar_df(df_meso, utils.get_user_data_path(username, config.FILE_MESOCICLOS))
                    
                    df_macro = df_macro[df_macro['id_macrociclo'] != id_macro_para_apagar]
                    utils.salvar_df(df_macro, utils.get_user_data_path(username, config.FILE_MACROCICLOS))

                    st.success(f"Macrociclo '{macro_selecionado_nome}' apagado.")
                    st.session_state[f'confirm_delete_macro_{macro_selecionado_nome}'] = False
                    st.rerun()
                if col_conf2.button("Cancelar", key="cancel_del_macro"):
                    st.session_state[f'confirm_delete_macro_{macro_selecionado_nome}'] = False
                    st.rerun()

    if macro_selecionado_nome == "-- Criar Novo --":
        with st.form("form_novo_macro"):
            st.write("Crie um novo grande ciclo de treino.")
            nome_macro = st.text_input("Nome do Macrociclo (ex: Preparação Verão 2025)")
            objetivo_macro = st.text_area("Objetivo Principal")
            col1, col2 = st.columns(2)
            data_inicio_macro = col1.date_input("Data de Início", value=date.today())
            data_fim_macro = col2.date_input("Data de Fim", value=date.today() + pd.DateOffset(months=3))
            
            if st.form_submit_button("Criar Macrociclo"):
                if nome_macro and data_inicio_macro and data_fim_macro:
                    max_id = df_macro['id_macrociclo'].max() if not df_macro.empty and 'id_macrociclo' in df_macro.columns else 0
                    novo_macro = pd.DataFrame([{'id_macrociclo': max_id + 1, 'nome': nome_macro, 'objetivo_principal': objetivo_macro, 'data_inicio': data_inicio_macro.strftime('%Y-%m-%d'), 'data_fim': data_fim_macro.strftime('%Y-%m-%d')}])
                    df_macro = pd.concat([df_macro, novo_macro], ignore_index=True)
                    utils.salvar_df(df_macro, utils.get_user_data_path(username, config.FILE_MACROCICLOS))
                    st.success("Macrociclo criado!")
                    st.rerun()
                else:
                    st.error("Preencha todos os campos para criar o macrociclo.")
    
    elif macro_selecionado_nome:
        id_macro_ativo = df_macro[df_macro['nome'] == macro_selecionado_nome]['id_macrociclo'].iloc[0]
        
        st.markdown("---")
        st.markdown("##### 2. Mesociclos (Fases Mensais)")
        st.caption(f"Adicione ou edite as fases do macrociclo '{macro_selecionado_nome}'")
        
        mesos_do_macro = df_meso[df_meso['id_macrociclo'] == id_macro_ativo].copy() if 'id_macrociclo' in df_meso.columns else pd.DataFrame()
        
        colunas_meso = {'id_mesociclo': pd.Series(dtype='Int64'), 'id_macrociclo': pd.Series(dtype='Int64'), 'nome': pd.Series(dtype='str'), 'ordem': pd.Series(dtype='Int64'), 'duracao_semanas': pd.Series(dtype='Int64'), 'foco_principal': pd.Series(dtype='str')}
        for col, dtype_series in colunas_meso.items():
            if col not in mesos_do_macro.columns:
                mesos_do_macro[col] = dtype_series

        mesos_do_macro['duracao_semanas'] = mesos_do_macro['duracao_semanas'].fillna(4)
        mesos_do_macro = mesos_do_macro.astype({'nome': str, 'foco_principal': str, 'ordem': 'Int64', 'duracao_semanas': 'Int64'})
        
        mesos_editados = st.data_editor(
            mesos_do_macro, num_rows="dynamic", use_container_width=True, key="editor_meso",
            column_config={
                "id_mesociclo": None, "id_macrociclo": None,
                "nome": st.column_config.TextColumn("Nome", required=True),
                "ordem": st.column_config.NumberColumn("Ordem", min_value=1, required=True),
                "duracao_semanas": st.column_config.NumberColumn("Duração (Semanas)", min_value=1, required=True, default=4),
                "foco_principal": st.column_config.TextColumn("Foco Principal")
            }
        )
        
        if st.button("Salvar Mesociclos"):
            df_meso_outros = df_meso[df_meso['id_macrociclo'] != id_macro_ativo] if 'id_macrociclo' in df_meso.columns else pd.DataFrame(columns=df_meso.columns)
            
            if not df_meso.empty and 'id_mesociclo' in df_meso.columns:
                numeric_ids = pd.to_numeric(df_meso['id_mesociclo'], errors='coerce').dropna()
                max_id = numeric_ids.max() if not numeric_ids.empty else 0
            else:
                max_id = 0
            
            novos_mesos = mesos_editados.copy().dropna(subset=['nome', 'ordem', 'duracao_semanas'])
            
            if not novos_mesos.empty:
                new_id_counter = int(max_id)
                final_mesos_list = []
                for index, row in novos_mesos.iterrows():
                    row_dict = row.to_dict()
                    if pd.isna(row_dict.get('id_mesociclo')) or row_dict.get('id_mesociclo') == 0:
                        new_id_counter += 1
                        row_dict['id_mesociclo'] = new_id_counter
                    final_mesos_list.append(row_dict)
                
                novos_mesos_com_ids = pd.DataFrame(final_mesos_list)
                novos_mesos_com_ids['id_macrociclo'] = id_macro_ativo
                
                df_final_meso = pd.concat([df_meso_outros, novos_mesos_com_ids], ignore_index=True)
                utils.salvar_df(df_final_meso, utils.get_user_data_path(username, config.FILE_MESOCICLOS))
                st.success("Mesociclos salvos!")
                st.rerun()

        st.markdown("---")
        st.markdown("##### 3. Plano Semanal (Microciclos)")
        
        lista_mesos_nomes_original = mesos_do_macro['nome'].dropna().tolist()

        if lista_mesos_nomes_original:
            meso_selecionado_nome = st.selectbox("Selecione um Mesociclo para planejar as semanas", options=lista_mesos_nomes_original)
            
            if meso_selecionado_nome:
                id_meso_ativo_series = mesos_do_macro.loc[mesos_do_macro['nome'] == meso_selecionado_nome, 'id_mesociclo']
                
                if not id_meso_ativo_series.empty and pd.notna(id_meso_ativo_series.iloc[0]):
                    id_meso_ativo = id_meso_ativo_series.iloc[0]
                    
                    semana_num = st.number_input("Selecione a Semana para planejar", min_value=1, max_value=8, step=1, key=f"semana_num_{id_meso_ativo}")
                    st.caption(f"Atribua os Planos de Treino para a Semana {semana_num} do mesociclo '{meso_selecionado_nome}'")
                    
                    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
                    planos_disponiveis = ["Descanso"] + (df_planos_treino['nome_plano'].tolist() if 'nome_plano' in df_planos_treino.columns else [])
                    
                    plano_semanal_salvo = df_plano_sem[(df_plano_sem['id_mesociclo'] == id_meso_ativo) & (df_plano_sem['semana_numero'] == semana_num)] if 'id_mesociclo' in df_plano_sem.columns else pd.DataFrame()
                    
                    if plano_semanal_salvo.empty:
                        plano_semanal_atual = pd.DataFrame({'dia_da_semana': dias_semana, 'plano_treino': ["Descanso"]*7})
                    else:
                        plano_semanal_atual = plano_semanal_salvo[['dia_da_semana', 'plano_treino']].set_index('dia_da_semana').reindex(dias_semana).reset_index()

                    plano_semanal_editado = st.data_editor(
                        plano_semanal_atual, use_container_width=True, hide_index=True, key=f"editor_semana_{id_meso_ativo}_{semana_num}",
                        column_config={
                            "dia_da_semana": st.column_config.TextColumn("Dia da Semana", disabled=True),
                            "plano_treino": st.column_config.SelectboxColumn("Plano de Treino", options=planos_disponiveis, required=True)
                        }
                    )

                    if st.button("Salvar Plano da Semana"):
                        df_plano_sem_outros = df_plano_sem.drop(plano_semanal_salvo.index) if not plano_semanal_salvo.empty else df_plano_sem
                        novo_plano_semanal = plano_semanal_editado.copy()
                        novo_plano_semanal['id_mesociclo'] = id_meso_ativo
                        novo_plano_semanal['semana_numero'] = semana_num
                        
                        df_final_semanal = pd.concat([df_plano_sem_outros, novo_plano_semanal], ignore_index=True)
                        utils.salvar_df(df_final_semanal, utils.get_user_data_path(username, config.FILE_PLANO_SEMANAL))
                        st.success("Plano da semana salvo!")
                        st.rerun()

                    with st.expander("⚠️ Apagar este planejamento semanal"):
                        st.warning(f"Isso removerá o planejamento da Semana {semana_num} do mesociclo '{meso_selecionado_nome}'.")
                        if st.button("Confirmar Exclusão da Semana", type="primary", key=f"del_semana_{id_meso_ativo}_{semana_num}"):
                            if not plano_semanal_salvo.empty:
                                df_plano_sem = df_plano_sem.drop(plano_semanal_salvo.index)
                                utils.salvar_df(df_plano_sem, utils.get_user_data_path(username, config.FILE_PLANO_SEMANAL))
                                st.success("Planejamento da semana apagado com sucesso!")
                                st.rerun()
                            else:
                                st.info("Não há planejamento salvo para esta semana.")
        else:
            st.info("Crie e salve um mesociclo acima para poder planejar as semanas.")

def render_registro_sub_tab(username, dados_pessoais, dft_simples, df_planos_treino):
    stats = logic.analisar_historico_treinos(dft_simples)
    if stats:
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("Total treinos", f"{stats['total_treinos']}")
        c2.metric("Total kcal", f"{stats['total_calorias']:.0f}")
        c3.metric("Média/semana", f"{stats['media_treinos_semana']:.1f}")
        c4.metric("Treinos esta semana", f"{stats['treinos_semana_atual']}")
        c5.metric("kcal/semana (média)", f"{stats['media_semanal_kcal']:.0f}")
        c6.metric("kcal/dia (média)", f"{stats['media_diaria_kcal']:.0f}")
        c7.metric("Último treino (kcal)", f"{stats['calorias_ultimo_treino']:.0f}")

    # --- HEATMAP DE ATIVIDADE ANUAL ---
    st.subheader("🔥 Heatmap de atividade")
    if not dft_simples.empty and 'data' in dft_simples.columns and 'calorias' in dft_simples.columns:
        dft_heat = dft_simples.copy()
        dft_heat['date'] = pd.to_datetime(dft_heat[config.COL_DATA], format="%d/%m/%Y")

        today = pd.Timestamp.now().normalize()
        start_date = pd.Timestamp(date(today.year, 1, 1))
            
        daily_activity = dft_heat.groupby(dft_heat['date'].dt.date)['calorias'].sum()
        all_days = pd.date_range(start=start_date, end=today, freq='D')
        activity_values = all_days.to_series(index=all_days, name='calorias').dt.date.map(daily_activity).fillna(0)
        
        # CORREÇÃO: A lógica para calcular o número da semana foi ajustada para alinhar corretamente com o calendário
        first_day_of_year_weekday = start_date.weekday()
        
        total_weeks = ((all_days.max() - all_days.min()).days + first_day_of_year_weekday) // 7 + 2
        heatmap_z = np.full((7, total_weeks), np.nan)
        heatmap_text = np.full((7, total_weeks), '', dtype=object)
        month_labels = {}

        for date_ts, activity in activity_values.items():
            weekday = date_ts.weekday()
            week_num = (date_ts.dayofyear - 1 + first_day_of_year_weekday) // 7
            
            heatmap_z[weekday, week_num] = activity
            heatmap_text[weekday, week_num] = f"{date_ts.strftime('%d/%m/%Y')}: {activity:.0f} kcal"
            
            month_name = date_ts.strftime('%b')
            if week_num > 0 and date_ts.day < 8 and month_name not in month_labels:
                month_labels[month_name] = week_num

        fig = go.Figure(data=go.Heatmap(
            z=heatmap_z,
            text=heatmap_text,
            hoverinfo='text',
            colorscale='YlGnBu', #Greens, Reds, Blues, Oranges, Viridis, Cividis, Plasma, Magma, Inferno, YlGnBu, YlOrRd, RdPu, PuRd, BuPu
            showscale=False,
            xgap=3, ygap=3
        ))

        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(
                showgrid=False, zeroline=False, autorange='reversed',
                tickmode='array',
                ticktext=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
                tickvals=list(range(7))
            ),
            xaxis=dict(
                showgrid=False, zeroline=False,
                tickmode='array',
                ticktext=list(month_labels.keys()),
                tickvals=list(month_labels.values())
            ),
            font=dict(color='white'),
            height=250,
            margin=dict(l=30, r=10, t=50, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Registre treinos para visualizar o heatmap de atividade.")
    
    st.markdown("---")

    st.subheader("Registrar Treino Realizado")
    
    lista_planos = ["Nenhum (Avulso)"] + (df_planos_treino['nome_plano'].tolist() if 'nome_plano' in df_planos_treino.columns else [])
    plano_executado = st.selectbox("Qual plano de treino você executou?", options=lista_planos)

    default_cardio = False
    if plano_executado and "cardio" in plano_executado.lower():
        default_cardio = True

    c1, c2, c3, c4 = st.columns(4)
    cardio = c1.toggle("Cardio?", value=default_cardio, key="cardio_reg")
    intensidade_tr = c2.selectbox("Intensidade", config.OPCOES_INTENSIDADE_TREINO, index=1, key="intensidade_reg")
    duracao_min = c3.number_input("Duração (min)", 0, 600, 60, 5, key="duracao_reg")
    carga_total = c4.number_input("Carga total (kg)", 0.0, step=5.0, value=5000.0, key="carga_reg")

    gasto_est = logic.calcular_gasto_treino(cardio, intensidade_tr, duracao_min, carga_total, dados_pessoais.get(config.COL_PESO, 70.0))
    st.metric("Gasto estimado", f"{gasto_est:.0f} kcal")

    with st.form("form_add_treino_realizado"):
        data_treino = st.text_input(f"Data (DD/MM/AAAA) — vazio = hoje", value="", key="data_reg")
        if st.form_submit_button(f"Adicionar Treino Realizado"):
            data_reg = date.today().strftime("%d/%m/%Y") if not data_treino else datetime.strptime(data_treino, "%d/%m/%Y").strftime("%d/%m/%Y")
            
            novo_treino = pd.DataFrame([{
                "data": data_reg, 
                "plano_executado": plano_executado if plano_executado != "Nenhum (Avulso)" else "Avulso",
                "tipo treino": "Cardio" if cardio else "Musculação", 
                "duracao min": duracao_min, 
                "calorias": round(gasto_est, 2)
            }])
            
            utils.adicionar_registro_df(novo_treino, utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES))
            st.success("Treino adicionado!")
            st.rerun()
    
    with st.expander("Histórico de Treinos Realizados (clique para editar/apagar)"):
        if not dft_simples.empty:
            dft_simples_sorted = dft_simples.sort_values(config.COL_DATA, ascending=False)
            dft_editado = st.data_editor(
                dft_simples_sorted,
                num_rows="dynamic",
                use_container_width=True,
                key="editor_treinos_realizados"
            )
            if st.button("💾 Salvar Alterações no Histórico"):
                utils.salvar_df(dft_editado, utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES))
                st.success("Histórico de treinos atualizado!")
                st.rerun()
        else:
            st.write("Nenhum treino simples registrado ainda.")

def render_evolucao_tab(dados_pessoais):
    st.header("📈 Evolução")
    if dados_pessoais:
        username = st.session_state.current_user
        with st.expander("Adicionar medidas", expanded=False):
            with st.form("form_add_medida"):
                c1, c2 = st.columns(2)
                data_med = c1.text_input("Data (DD/MM/AAAA) — vazio = hoje", value="")
                peso_in = c2.number_input("Peso (kg)", 0.0, step=0.1, value=dados_pessoais.get(config.COL_PESO, 70.0))
                c3, c4, c5, c6 = st.columns(4)
                gord_corp = c3.number_input("Gordura corporal (%)", 0.0, step=0.1, value=dados_pessoais.get("gordura_corporal", 0.0))
                gord_visc = c4.number_input("Gordura visceral (%)", 0.0, step=0.1, value=dados_pessoais.get("gordura_visceral", 0.0))
                musc_esq = c5.number_input("Músculos (%)", 0.0, step=0.1, value=dados_pessoais.get("massa_muscular", 0.0))
                cintura = c6.number_input("Cintura (cm)", 0.0, step=0.1, value=0.0)
                peito = c3.number_input("Peito (cm)", 0.0, step=0.1, value=0.0)
                braco = c4.number_input("Braço (cm)", 0.0, step=0.1, value=0.0)
                coxa = c5.number_input("Coxa (cm)", 0.0, step=0.1, value=0.0)
                obs = st.text_input("Observações", value="")
                if st.form_submit_button("Adicionar medida"):
                    data_fmt = date.today().strftime("%d/%m/%Y") if not data_med else datetime.strptime(data_med, "%d/%m/%Y").strftime("%d/%m/%Y")
                    dfe_atual = utils.carregar_df(utils.get_user_data_path(username, config.FILE_EVOLUCAO))
                    var = float(peso_in - float(dfe_atual[config.COL_PESO].iloc[-1])) if not dfe_atual.empty and config.COL_PESO in dfe_atual.columns else 0.0
                    nova_medida = pd.DataFrame([{"semana": len(dfe_atual) + 1, "data": data_fmt, "peso": peso_in, "var": var, "gordura_corporal": gord_corp, "gordura_visceral": gord_visc, "musculos_esqueleticos": musc_esq, "cintura": cintura, "peito": peito, "braco": braco, "coxa": coxa, "observacoes": obs}])
                    utils.adicionar_registro_df(nova_medida, utils.get_user_data_path(username, config.FILE_EVOLUCAO))
                    dfp = utils.carregar_df(utils.get_user_data_path(username, config.FILE_DADOS_PESSOAIS))
                    if not dfp.empty:
                        dfp.loc[0, config.COL_PESO] = float(peso_in)
                        utils.salvar_df(dfp, utils.get_user_data_path(username, config.FILE_DADOS_PESSOAIS))
                    st.success("Medida adicionada!"); st.rerun()
        dfe_final = utils.carregar_df(utils.get_user_data_path(username, config.FILE_EVOLUCAO))
        if not dfe_final.empty:
            df_obj = utils.carregar_df(utils.get_user_data_path(username, config.FILE_OBJETIVO)); objetivo_info_evol = df_obj.iloc[0].to_dict() if not df_obj.empty else {}
            metricas_evol = logic.calcular_metricas_saude(dados_pessoais, objetivo_info_evol)
            progresso = logic.analisar_progresso_objetivo(dfe_final, metricas_evol)
            if progresso:
                st.subheader("🏁 Progresso do Objetivo")
                c1, c2, c3 = st.columns(3)
                c1.metric("Meta de Peso", f"{metricas_evol['peso_ideal']:.1f} kg", delta=f"{progresso['objetivo_total_kg']:+.1f} kg")
                c2.metric("Progresso Atual", f"{progresso['progresso_atual_kg']:+.1f} kg", delta=f"{progresso['progresso_percent']:.1f}%")
                c3.metric("Restante para Meta", f"{progresso['restante_kg']:+.1f} kg")
                try:
                    dt_inicio = datetime.strptime(objetivo_info_evol.get("DataInicio"), "%d/%m/%Y")
                    dt_fim = datetime.strptime(metricas_evol.get("data_objetivo_fmt"), "%d/%m/%Y")
                    total_dias = (dt_fim - dt_inicio).days; dias_passados = (datetime.now() - dt_inicio).days
                    progresso_tempo = min(dias_passados / total_dias, 1.0) if total_dias > 0 else 0
                    st.progress(progresso_tempo)
                    st.caption(f"Início: {dt_inicio.strftime('%d/%m/%Y')} | Conclusão Prevista: {dt_fim.strftime('%d/%m/%Y')} ({dias_passados}/{total_dias} dias)")
                except (ValueError, TypeError): st.caption("Timeline indisponível. Verifique as datas do objetivo.")
            st.subheader("📊 Gráficos de Evolução")
            with st.expander("Histórico de medições", expanded=False):
                st.dataframe(dfe_final.sort_values("semana", ascending=False), use_container_width=True)
            
            dfe_final[config.COL_DATA] = pd.to_datetime(dfe_final[config.COL_DATA], format="%d/%m/%Y")
            dfe_final = dfe_final.sort_values(config.COL_DATA)

            fig, ax1 = plt.subplots(figsize=(8, 3))
            
            df_plot_peso = dfe_final[dfe_final[config.COL_PESO] > 0]
            df_plot_gordura = dfe_final[dfe_final["gordura_corporal"] > 0]
            df_plot_musculos = dfe_final[dfe_final["musculos_esqueleticos"] > 0]

            ax1.plot(df_plot_peso["semana"], df_plot_peso[config.COL_PESO], marker="o", label="Peso (kg)")
            ax1.set_xlabel("Semanas"); ax1.set_ylabel("Peso (kg)"); ax1.grid(True)
            
            ax2 = ax1.twinx()
            ax2.plot(df_plot_gordura["semana"], df_plot_gordura["gordura_corporal"], marker="o", label="Gordura corporal (%)", linestyle="--")
            ax2.plot(df_plot_musculos["semana"], df_plot_musculos["musculos_esqueleticos"], marker="o", label="Músculos (%)", linestyle="--")
            ax2.set_ylabel("%")
            
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2); st.pyplot(fig)

            fig2, ax = plt.subplots(figsize=(8, 3))

            medidas = ["cintura", "peito", "braco", "coxa"]
            labels_medidas = {"cintura": "Cintura (cm)", "peito": "Peito (cm)", "braco": "Braço (cm)", "coxa": "Coxa (cm)"}

            for medida in medidas:
                if medida in dfe_final.columns:
                    df_plot_medida = dfe_final[dfe_final[medida] > 0]
                    if not df_plot_medida.empty:
                        ax.plot(df_plot_medida["semana"], df_plot_medida[medida], marker="o", label=labels_medidas[medida])

            ax.set_title("Medidas corporais (cm)"); ax.set_xlabel("Semanas"); ax.set_ylabel("cm")
            ax.grid(True); ax.legend(); st.pyplot(fig2)
            
        else:
            st.info("Adicione sua primeira medida para ver a evolução.")
    else:
        st.error("Preencha e salve seus dados pessoais na primeira aba.")