# ==============================================================================
# PLANO FIT APP - COMPONENTES DE UI
# ==============================================================================
# Este arquivo é responsável por toda a renderização da interface do usuário (UI).
# Cada função `render_*` constrói uma parte específica da tela, como a tela de
# login ou uma das abas da aplicação. Manter toda a lógica de UI separada
# torna o código mais limpo, organizado e fácil de manter.
# ==============================================================================

from datetime import datetime, date, timedelta
from typing import Dict, Any
from streamlit_autorefresh import st_autorefresh
from pathlib import Path
import streamlit.components.v1 as components
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotting
import numpy as np
import config
import logic
import utils
import auth
import time

# ==============================================================================
# TELAS DE LOGIN / PERFIL
# ==============================================================================

def render_login_screen():
    """
    Renderiza a tela principal de login, que permite ao usuário logar,
    navegar para a criação de perfil ou para a redefinição de senha.
    Usa o st.session_state para controlar qual formulário é exibido.
    """
    st.title(f"Bem-vindo ao {config.APP_TITLE}")
    
    # Gerencia qual visualização (login, criar, resetar) está ativa.
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
    """Renderiza o formulário de login para um perfil existente."""
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
    """Renderiza o formulário para criação de um novo perfil de usuário."""
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
                
                # Loga o usuário automaticamente após criar o perfil.
                st.session_state.logged_in = True
                st.session_state.current_user = username
                auth.set_last_user(username)
                st.toast(f"Perfil '{username}' criado com sucesso!", icon="🎉")
                st.rerun()
            else:
                st.error("Nome de perfil inválido ou já existente.")
    
    if st.button("Voltar para o Login"):
        st.session_state.login_view = 'login'
        st.rerun()

def render_reset_password_form():
    """Renderiza o formulário para redefinir a senha de um perfil."""
    st.subheader("Redefinir Senha")
    username_to_reset = st.text_input("Digite o nome do seu perfil")

    if username_to_reset:
        df_users = auth.load_users()
        if username_to_reset in df_users['username'].tolist():
            with st.form("reset_password_form"):
                st.info(f"Perfil '{username_to_reset}' encontrado. Defina uma nova senha.")
                new_password = st.text_input("Nova Senha", type="password")
                confirm_password = st.text_input("Confirmar Nova Senha", type="password")
                
                submitted = st.form_submit_button("Redefinir Senha")
                if submitted:
                    if new_password and new_password == confirm_password:
                        new_hash = auth.hash_password(new_password) if new_password else None
                        df_users.loc[df_users['username'] == username_to_reset, 'password_hash'] = new_hash
                        auth.save_users(df_users)
                        st.toast("Senha redefinida com sucesso!", icon="🔑")
                        st.session_state.login_view = 'login'
                        st.rerun()
                    else:
                        st.error("As senhas não coincidem ou estão em branco.")
        else:
            st.warning("Perfil não encontrado. Verifique o nome digitado.")

    if st.button("Voltar para o Login"):
        st.session_state.login_view = 'login'
        st.rerun()

# ==============================================================================
# FUNÇÕES DAS ABAS
# ==============================================================================

def render_visao_geral_tab(user_data: Dict[str, Any], RECOMEND: pd.DataFrame):
    """
    Renderiza a aba de "Visão Geral", o dashboard principal da aplicação.
    """
    dados_pessoais = user_data.get("dados_pessoais", {})
    if not dados_pessoais:
        st.error("Preencha e salve seus dados pessoais na aba 'Dados Pessoais' para ver a Visão Geral.")
        return

    df_obj = user_data.get("df_objetivo", pd.DataFrame())
    dfe_final = user_data.get("df_evolucao", pd.DataFrame())
    dft_log = user_data.get("df_log_treinos", pd.DataFrame())
    objetivo_info = df_obj.iloc[0].to_dict() if not df_obj.empty else {}

    if not dfe_final.empty and objetivo_info:
        st.subheader("🏁 Progresso do Objetivo")
        metricas_evol = logic.calcular_metricas_saude(dados_pessoais, objetivo_info)
        meta_final = metricas_evol.get("peso_alvo_final")
        progresso = logic.analisar_progresso_objetivo(dfe_final, meta_final)
        if progresso:
            c1, c2, c3 = st.columns(3)
            label_meta = "Peso Alvo" if float(objetivo_info.get("PesoAlvo", 0.0)) > 0 else "Peso Ideal (IMC)"
            c1.metric(label_meta, f"{meta_final:.1f} kg", delta=f"{progresso.get('objetivo_total_kg', 0):+.1f} kg", help="Sua meta de peso atual.")
            c2.metric("Progresso Atual", f"{progresso.get('progresso_atual_kg', 0):+.1f} kg", delta=f"{progresso.get('progresso_percent', 0):.1f}%", help="Quanto você já progrediu em relação à meta total.")
            c3.metric("Restante para Meta", f"{progresso.get('restante_kg', 0):+.1f} kg", help="Quanto falta para atingir sua meta de peso.")
        try:
            dt_inicio = datetime.strptime(objetivo_info.get("DataInicio", ""), "%d/%m/%Y")
            dt_fim_str = metricas_evol.get("data_objetivo_fmt", "N/A")
            if dt_fim_str != "N/A":
                dt_fim = datetime.strptime(dt_fim_str, "%d/%m/%Y")
                total_dias = (dt_fim - dt_inicio).days
                dias_passados = (datetime.now() - dt_inicio).days
                progresso_tempo = min(dias_passados / total_dias, 1.0) if total_dias > 0 else 0
                st.progress(progresso_tempo)
                st.caption(f"Início: {dt_inicio.strftime('%d/%m/%Y')} | Conclusão Prevista: {dt_fim.strftime('%d/%m/%Y')} ({dias_passados}/{total_dias} dias)")
        except (ValueError, TypeError):
            st.caption("Timeline indisponível. Verifique as datas do objetivo.")
    st.markdown("---")

    st.subheader("🍎 Metas Alimentares")
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
    st.markdown("---")

    meso_ativo_info = None
    semana_no_mes = 0
    plano_semanal_ativo = pd.DataFrame()
    
    today = pd.to_datetime(date.today())
    df_macro = user_data.get("df_macrociclos", pd.DataFrame())
    df_meso = user_data.get("df_mesociclos", pd.DataFrame())
    df_plano_sem = user_data.get("df_plano_semanal", pd.DataFrame())
    macro_ativo = df_macro[(pd.to_datetime(df_macro['data_inicio']) <= today) & (pd.to_datetime(df_macro['data_fim']) >= today)] if 'data_inicio' in df_macro.columns else pd.DataFrame()

    if not macro_ativo.empty:
        id_macro_ativo = macro_ativo['id_macrociclo'].iloc[0]
        mesos_do_macro = df_meso[df_meso['id_macrociclo'] == id_macro_ativo] if 'id_macrociclo' in df_meso.columns else pd.DataFrame()
        if not mesos_do_macro.empty:
            data_inicio_macro = pd.to_datetime(macro_ativo['data_inicio'].iloc[0])
            dias_desde_inicio_macro = (today - data_inicio_macro).days
            semana_no_macro = (dias_desde_inicio_macro // 7) + 1 if dias_desde_inicio_macro >= 0 else 0
            semanas_acumuladas = 0
            if semana_no_macro > 0 and 'ordem' in mesos_do_macro.columns:
                for _, meso in mesos_do_macro.sort_values('ordem').iterrows():
                    duracao_meso = int(meso.get('duracao_semanas', 4))
                    if semana_no_macro <= semanas_acumuladas + duracao_meso:
                        meso_ativo_info = meso
                        semana_no_mes = semana_no_macro - semanas_acumuladas
                        id_meso_ativo = meso['id_mesociclo']
                        required_cols = ['id_mesociclo', 'semana_numero']
                        if not df_plano_sem.empty and all(col in df_plano_sem.columns for col in required_cols):
                            plano_semanal_ativo = df_plano_sem[(df_plano_sem['id_mesociclo'] == id_meso_ativo) & (df_plano_sem['semana_numero'] == semana_no_mes)]
                        break
                    semanas_acumuladas += duracao_meso

    stats = logic.analisar_historico_treinos(dft_log)
    if stats:
        st.subheader("💪 Histórico e Consistência")
        consistencia = logic.analisar_consistencia_habitos(dft_log, plano_semanal_ativo)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Sequência de Treinos", f"{consistencia['streak_dias']} dias")
        c2.metric("Adesão Semanal", f"{consistencia['adesao_percentual']}%")
        c3.metric("Treinos esta semana", f"{stats['treinos_semana_atual']}")
        c4.metric("Média/semana", f"{stats['media_treinos_semana']:.1f} treinos")
        c5.metric("Total de treinos", f"{stats['total_treinos']}")
        c6.metric("Último treino (kcal)", f"{stats['calorias_ultimo_treino']:.0f}")
    st.markdown("---")

    st.subheader(f"📅 Periodização do Treino {macro_ativo['nome'].iloc[0] if not macro_ativo.empty else ''}")
    if not macro_ativo.empty:
        id_macro_ativo = macro_ativo['id_macrociclo'].iloc[0]
        mesos_do_macro = df_meso[df_meso['id_macrociclo'] == id_macro_ativo] if 'id_macrociclo' in df_meso.columns else pd.DataFrame()
        if not mesos_do_macro.empty and 'ordem' in mesos_do_macro.columns:
            data_inicio_macro = pd.to_datetime(macro_ativo['data_inicio'].iloc[0])
            gantt_data = []
            start_date = data_inicio_macro
            for _, meso in mesos_do_macro.sort_values('ordem').iterrows():
                duracao_semanas = int(meso.get('duracao_semanas', 4))
                end_date = start_date + pd.DateOffset(weeks=duracao_semanas)
                gantt_data.append(dict(Task=meso['nome'], Start=start_date.strftime('%Y-%m-%d'), Finish=end_date.strftime('%Y-%m-%d'), Resource=meso['foco_principal']))
                start_date = end_date
            if gantt_data:
                fig = ff.create_gantt(gantt_data, index_col='Resource', show_colorbar=True, group_tasks=True, title='Fases do Treino (Mesociclos)')
                fig.add_vline(x=today, line_width=3, line_dash="dash", line_color="red", name="Hoje")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum macrociclo de treino ativo para o período atual. Crie um na aba 'Treino'.")

    if meso_ativo_info is not None:
        nome_meso = meso_ativo_info['nome']
        duracao_total_meso = int(meso_ativo_info.get('duracao_semanas', 4))
        st.subheader(f"🗓️ Plano da Semana Atual ({nome_meso} - Semana {semana_no_mes} de {duracao_total_meso})")
    else:
        st.subheader("🗓️ Plano da Semana Atual")
        
    if not plano_semanal_ativo.empty:
        cols = st.columns(7)
        dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        dias_map_local = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
        for i, dia in enumerate(dias_semana):
            treino_do_dia_series = plano_semanal_ativo[plano_semanal_ativo['dia_da_semana'] == dia]['plano_treino']
            treino_do_dia = treino_do_dia_series.iloc[0] if not treino_do_dia_series.empty else "Não Planejado"
            with cols[i]:
                st.markdown(f"**{dia}**")
                if dia == dias_map_local.get(date.today().weekday()):
                    st.success(treino_do_dia)
                else:
                    st.info(treino_do_dia)
    else:
        st.info("Nenhum plano de treino definido para a semana atual na aba 'Treino'.")
    st.markdown("---")
    
    st.subheader("🔥 Heatmap de Atividade")
    if not dft_log.empty and 'data' in dft_log.columns and 'calorias' in dft_log.columns:
        dft_heat = dft_log.copy()
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
        font_color = 'white' if st.get_option("theme.base") == "dark" else 'black'
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(showgrid=False, zeroline=False, autorange='reversed', tickmode='array', ticktext=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'], tickvals=list(range(7))), xaxis=dict(showgrid=False, zeroline=False, tickmode='array', ticktext=list(month_labels.keys()), tickvals=list(month_labels.values())), font=dict(color=font_color), height=250, margin=dict(l=30, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True, key="heatmap_geral")
    st.markdown("---")


def render_dados_pessoais_tab(user_data: Dict[str, Any]):
    """
    Renderiza a aba de Dados Pessoais com comportamento condicional:
    - Se não houver dados, mostra o formulário de cadastro inicial.
    - Se já houver dados, mostra um resumo e uma opção para editar.
    """
    # st.header("👤 Dados pessoais") # --- Removido para economizar espaço
    dados_pessoais = user_data.get("dados_pessoais", {})
    username = st.session_state.current_user

    def render_form_pessoais():
        """Função interna para renderizar o formulário e processar o envio."""
        
        # Tenta converter a data de nascimento salva (string) para um objeto de data
        # Se não conseguir, usa uma data padrão (30 anos atrás)
        default_nascimento = date.today() - timedelta(days=365*30)
        nascimento_str = dados_pessoais.get("nascimento", "")
        if nascimento_str:
            try:
                default_nascimento = datetime.strptime(nascimento_str, "%d/%m/%Y").date()
            except (ValueError, TypeError):
                pass

        # As variáveis dos widgets são definidas aqui
        with st.form("form_pessoais"):
            c1, c2, c3, c4 = st.columns(4)
            nome = c1.text_input("Nome", value=dados_pessoais.get("nome", ""))
            
            # ALTERADO: st.text_input para st.date_input
            nascimento_obj = c2.date_input(
                "Nascimento", 
                value=default_nascimento, 
                min_value=date(1920, 1, 1), 
                max_value=date.today(),
                format="DD/MM/YYYY"
            )

            altura = c3.number_input("Altura (m)", 0.5, 2.5, float(dados_pessoais.get("altura", 1.70) or 1.70), 0.01)
            sexo = c4.selectbox("Sexo", config.OPCOES_SEXO, index=config.OPCOES_SEXO.index(dados_pessoais.get("sexo", "M")))

            dfe_evol = user_data.get("df_evolucao", pd.DataFrame())
            peso_recente = float(dfe_evol[config.COL_PESO].iloc[-1]) if not dfe_evol.empty and config.COL_PESO in dfe_evol.columns else None
            peso_val = peso_recente if peso_recente is not None else float(dados_pessoais.get(config.COL_PESO, 70.0) or 70.0)
            
            c5, c6, c7, c8 = st.columns(4)
            peso = c5.number_input("Peso (kg)", 20.0, 400.0, peso_val, 0.1, help="Este peso inicial é usado como base. Para atualizações, use a aba 'Evolução'.")
            gord_corp = c6.number_input("Gordura corporal (%)", 0.0, 100.0, float(dados_pessoais.get("gordura_corporal", 0.0) or 0.0), 0.1)
            gord_visc = c7.number_input("Gordura visceral (nível)", 0.0, 100.0, float(dados_pessoais.get("gordura_visceral", 0.0) or 0.0), 0.1)
            musculo = c8.number_input("Massa muscular (%)", 0.0, 100.0, float(dados_pessoais.get("massa_muscular", 0.0) or 0.0), 0.1)
            
            # A variável 'submitted' é definida aqui, ao final do formulário
            submitted = st.form_submit_button("Salvar dados pessoais")
        
        if submitted:
            # ALTERADO: Lógica de idade e salvamento adaptada para o objeto de data
            nascimento_str_para_salvar = nascimento_obj.strftime("%d/%m/%Y")
            hoje = date.today()
            idade = hoje.year - nascimento_obj.year - ((hoje.month, hoje.day) < (nascimento_obj.month, nascimento_obj.day))
            
            df_novo = pd.DataFrame([{"nome": nome, "nascimento": nascimento_str_para_salvar, "altura": altura, "sexo": sexo, "peso": peso, "idade": idade, "gordura_corporal": gord_corp, "gordura_visceral": gord_visc, "massa_muscular": musculo}])
            utils.salvar_df(df_novo, utils.get_user_data_path(username, config.FILE_DADOS_PESSOAIS))
            
            # Adiciona o primeiro registro de peso na aba de evolução também
            if dfe_evol.empty:
                primeira_medida = pd.DataFrame([{"semana": 1, "data": date.today().strftime("%d/%m/%Y"), "peso": peso, "var": 0.0, "gordura_corporal": gord_corp, "gordura_visceral": gord_visc, "musculos_esqueleticos": musculo, "cintura": 0, "peito": 0, "braco": 0, "coxa": 0}])
                utils.salvar_df(primeira_medida, utils.get_user_data_path(username, config.FILE_EVOLUCAO))

            st.toast("Dados pessoais salvos!", icon="✅")
            st.rerun()

    # Lógica principal: decide se mostra o formulário ou o resumo
    if not dados_pessoais:
        st.info("👋 Bem-vindo! Por favor, preencha seus dados iniciais para começarmos.")
        render_form_pessoais()
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Nome", dados_pessoais.get("nome", "N/A"))
        col2.metric("Nascimento", dados_pessoais.get("nascimento", "N/A"))
        col3.metric("Altura", f"{dados_pessoais.get('altura', 0.0):.2f} m")
        col4.metric("Sexo", dados_pessoais.get("sexo", "N/A"))
        
        st.success("Para atualizar seu peso e medidas corporais, utilize a aba '📈 Evolução'.")
        
        with st.expander("Editar dados de base (Nome, Nascimento, etc.)"):
            st.warning("Atenção: A alteração destes dados pode afetar todos os cálculos futuros.")
            render_form_pessoais()

def render_objetivos_tab(user_data: Dict[str, Any]):
    """
    Renderiza a aba para definir objetivos e visualizar métricas de saúde.
    """
    dados_pessoais = user_data.get("dados_pessoais", {})
    if dados_pessoais:
        df_obj = user_data.get("df_objetivo", pd.DataFrame())
        objetivo_info = df_obj.iloc[0].to_dict() if not df_obj.empty else {}
        
        help_text_atividade = """
        Selecione seu nível de atividade física semanal:
        - **Sedentário**: pouco ou nenhum exercício
        - **Leve**: exercício leve 1-3 dias/sem
        - **Moderado**: 3-5 dias/sem
        - **Intenso**: 6-7 dias/sem
        - **Extremo**: exercício físico muito pesado ou trabalho físico
        """
        help_text_ambiente = """
        Ambiente predominante onde você treina (influencia a meta de hidratação):
        - **Quente**: > 28°C
        - **Ameno**: ~ 22°C
        - **Frio**: < 15°C
        """

        df_evolucao = user_data.get("df_evolucao", pd.DataFrame())
        peso_atual = 70.0
        if not df_evolucao.empty and config.COL_PESO in df_evolucao.columns:
            peso_atual = df_evolucao[config.COL_PESO].iloc[-1]
        elif config.COL_PESO in dados_pessoais and dados_pessoais[config.COL_PESO] > 0:
            peso_atual = dados_pessoais[config.COL_PESO]

        with st.form("form_obj"):
            c1, c2, c3, c4, c5 = st.columns(5)
            
            # Lógica para definir a data padrão para o widget
            default_inicio = date.today()
            inicio_str = objetivo_info.get("DataInicio", "")
            if inicio_str:
                try:
                    default_inicio = datetime.strptime(inicio_str, "%d/%m/%Y").date()
                except (ValueError, TypeError):
                    pass
            
            # ALTERADO: st.text_input para st.date_input
            inicio_objetivo_obj = c1.date_input(
                "Início", 
                value=default_inicio, 
                format="DD/MM/YYYY",
                help="Data de início da sua meta atual."
            )

            intensidade = c2.selectbox("Nível de atividade", config.OPCOES_NIVEL_ATIVIDADE, index=config.OPCOES_NIVEL_ATIVIDADE.index(objetivo_info.get("Atividade", "moderado")), help=help_text_atividade)
            ambiente = c3.selectbox("Ambiente", config.OPCOES_AMBIENTE, index=config.OPCOES_AMBIENTE.index(objetivo_info.get("Ambiente", "ameno")), help=help_text_ambiente)
            objetivo = c4.selectbox("Objetivo de peso", config.OPCOES_OBJETIVO_PESO, index=config.OPCOES_OBJETIVO_PESO.index(objetivo_info.get("ObjetivoPeso", "manutencao")), help="Selecione se seu foco é perder, manter ou ganhar peso.")
            peso_alvo = c5.number_input("Peso Alvo (kg)", min_value=0.0, max_value=200.0, value=float(objetivo_info.get("PesoAlvo", 0.0)), step=0.5, help="Defina sua meta de peso. Deixe em 0 para usar o Peso Ideal (IMC 24.9) como meta.")
            submitted = st.form_submit_button("Salvar objetivo")

        if submitted:
            # ALTERADO: Salva a data formatada como string
            df_obj_novo = pd.DataFrame([{"DataInicio": inicio_objetivo_obj.strftime("%d/%m/%Y"), "Atividade": intensidade, "Ambiente": ambiente, "ObjetivoPeso": objetivo, "PesoAlvo": peso_alvo}])
            utils.salvar_df(df_obj_novo, utils.get_user_data_path(st.session_state.current_user, config.FILE_OBJETIVO))
            st.toast("Objetivo salvo!", icon="🎯")
            st.rerun()

        # ALTERADO: Constrói o dicionário de informações com a data correta
        objetivo_info = {"DataInicio": inicio_objetivo_obj.strftime("%d/%m/%Y"), "Atividade": intensidade, "Ambiente": ambiente, "ObjetivoPeso": objetivo, "PesoAlvo": peso_alvo}
        metricas = logic.calcular_metricas_saude(dados_pessoais, objetivo_info)
        
        st.subheader("🔥 Alvo Calórico")
        plotting.plot_energy_composition(metricas['TMB'], metricas['TDEE'], metricas['alvo_calorico'])
    else:
        st.error("Preencha e salve seus dados pessoais na primeira aba.")

def render_alimentacao_tab(user_data: Dict[str, Any], TABELA_ALIM: pd.DataFrame, RECOMEND: pd.DataFrame):
    """
    Renderiza a aba de Alimentação, permitindo o registro diário,
    criação/gerenciamento de planos alimentares e visualização de totais.

    Args:
        user_data (Dict[str, Any]): Dicionário com os dados do usuário.
        TABELA_ALIM (pd.DataFrame): DataFrame com a composição dos alimentos.
        RECOMEND (pd.DataFrame): DataFrame com as recomendações nutricionais.
    """
    # st.header("🍽️ Alimentação") # --- Removido para economizar espaço
    username = st.session_state.current_user
    dados_pessoais = user_data.get("dados_pessoais", {})

    # Carregamento de Dados
    path_refeicoes = utils.get_user_data_path(username, config.FILE_REFEICOES)
    df_refeicoes = user_data.get("df_refeicoes", pd.DataFrame())
    path_planos = utils.get_user_data_path(username, config.FILE_PLANOS_ALIMENTARES)
    df_planos_alimentares = user_data.get("df_planos_alimentares", pd.DataFrame())

    col_refeicoes, col_assistente = st.columns([0.6, 0.4])

    with col_refeicoes:
        st.subheader("🔢 Totais Calculados",help='Total de calorias com base no objetivo. Demais macronutrientes com base no banco de dados de recomendações.')
        # Lógica para calcular os totais de macronutrientes do dia
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
        
        # Comparação com as metas diárias
        df_obj = user_data.get("df_objetivo", pd.DataFrame())
        objetivo_info_alim = df_obj.iloc[0].to_dict() if not df_obj.empty else {}
        
        if not objetivo_info_alim or RECOMEND.empty:
            st.warning("Defina seus objetivos e carregue as recomendações para visualizar o progresso em relação às metas.")
        else:
            metricas_alim = logic.calcular_metricas_saude(dados_pessoais, objetivo_info_alim)
            alvo_calorico = metricas_alim.get('alvo_calorico', 1) # Evita divisão por zero
            
            def obter_recomendacao_diaria(sexo, objetivo, intensidade):
                filt = RECOMEND[(RECOMEND["Sexo"].str.lower() == sexo.lower()) & (RECOMEND["Objetivo"].str.lower() == objetivo.lower()) & (RECOMEND["Atividade"].str.lower() == intensidade.lower())]
                return filt.iloc[0] if not filt.empty else None
            
            rec = obter_recomendacao_diaria(dados_pessoais.get('sexo'), objetivo_info_alim.get('ObjetivoPeso'), objetivo_info_alim.get('Atividade'))
            
            if rec is not None:
                peso = dados_pessoais.get(config.COL_PESO, 70.0)
                prot_obj, carb_obj, gord_obj, sod_obj = (float(rec.iloc[3]) * peso), (float(rec.iloc[4]) * peso), (float(rec.iloc[5]) * peso), float(rec.iloc[6])
                
                macros = {
                    "Calorias": (total[config.COL_ENERGIA], alvo_calorico, "kcal"),
                    "Proteína": (total[config.COL_PROTEINA], prot_obj, "g"),
                    "Carboidrato": (total[config.COL_CARBOIDRATO], carb_obj, "g"),
                    "Gorduras": (total[config.COL_LIPIDEOS], gord_obj, "g"),
                    "Sódio": (total[config.COL_SODIO], sod_obj, "mg")
                }

                # Cria 5 colunas para exibir os totais lado a lado.
                cols = st.columns(len(macros))
                
                # Itera sobre os macros e as colunas ao mesmo tempo.
                for i, (nome, (valor, meta, unidade)) in enumerate(macros.items()):
                    with cols[i]:
                        # Usa st.markdown para formatar o texto e deixá-lo mais limpo
                        st.markdown(f"**{nome}**")
                        st.markdown(f"<font size='2' color='grey'>{valor:.0f} / {meta:.0f} {unidade}</font>", unsafe_allow_html=True)
                        
                        # Calcula e exibe a barra de progresso.
                        percentual = (valor / meta) if meta > 0 else 0
                        st.progress(min(percentual, 1.0)) # Garante que a barra não passe de 100%

        st.markdown("---")

        st.subheader("📊 Análise das Refeições")

        # Calcula a distribuição de nutrientes por refeição usando a função da 'logic.py'
        df_distribuicao = logic.analisar_distribuicao_refeicoes(df_refeicoes, TABELA_ALIM)
        
        # Só exibe os gráficos se houver dados de refeições para analisar
        if not df_distribuicao.empty:
            # Dicionário para mapear os nomes amigáveis para as colunas do DataFrame
            metricas_opcoes = {
                "Calorias (kcal)": config.COL_ENERGIA,
                "Proteínas (g)": config.COL_PROTEINA,
                "Carboidratos (g)": config.COL_CARBOIDRATO,
                "Gorduras (g)": config.COL_LIPIDEOS,
                "Sódio (mg)": config.COL_SODIO
            }
            
            # Widget para o usuário selecionar qual nutriente visualizar no primeiro gráfico
            metrica_selecionada_label = st.selectbox(
                "Selecione o nutriente para visualizar a distribuição:",
                options=metricas_opcoes.keys(), width=300
            )
            coluna_selecionada = metricas_opcoes[metrica_selecionada_label]

            # Importa a função para criar subplots do Plotly
            from plotly.subplots import make_subplots

            # Cria a figura que conterá os dois gráficos de pizza (1 linha, 2 colunas)
            fig = make_subplots(
                rows=1, cols=2,
                specs=[[{'type':'domain'}, {'type':'domain'}]], # 'domain' especifica um gráfico de pizza/rosca
                subplot_titles=(f'Distribuição de {metrica_selecionada_label}', 'Distribuição de Peso (g)')
            )

            # --- Gráfico 1: Nutriente Selecionado ---
            fig.add_trace(go.Pie(
                labels=df_distribuicao.index,
                values=df_distribuicao[coluna_selecionada],
                name=metrica_selecionada_label,
                hole=.4, # Cria o efeito de "rosca" (donut)
                hovertemplate='<b>%{label}</b><br>%{value:,.1f} (' + coluna_selecionada.split('(')[-1] + '<br>%{percent}<extra></extra>'
            ), 1, 1)

            # --- Gráfico 2: Peso (g) ---
            fig.add_trace(go.Pie(
                labels=df_distribuicao.index,
                values=df_distribuicao['Quantidade'],
                name='Peso (g)',
                hole=.4,
                hovertemplate='<b>%{label}</b><br>%{value:,.0f}g<br>%{percent}<extra></extra>'
            ), 1, 2)

            # --- Layout e Estilização ---
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label', # Exibe o percentual e o nome da fatia
                textfont_size=14
            )
            fig.update_layout(
                height=400,
                margin=dict(t=50, b=20, l=20, r=20),
                plot_bgcolor='rgba(0,0,0,0)',
                legend_traceorder="reversed" # Garante que a ordem da legenda coincida com a dos gráficos
            )
            
            # Exibe o gráfico no Streamlit
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Adicione refeições para visualizar a análise gráfica.")

        st.subheader("Refeições do Dia")
        # Editor de dados para manipulação direta da lista de refeições
        edited_df = st.data_editor(
            df_refeicoes, num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "Refeicao": st.column_config.SelectboxColumn("Refeição", options=config.OPCOES_REFEICOES, required=True),
                "Alimento": st.column_config.TextColumn("Alimento", required=True),
                "Quantidade": st.column_config.NumberColumn("Qtd (g)", min_value=0.0, step=1.0)
            }, key="editor_refeicoes_dia"
        )
        if st.button("💾 Salvar Alterações Manuais",key='salvar_refeições'):
            utils.salvar_df(edited_df, path_refeicoes)
            st.toast("Alterações salvas!", icon="🍽️")
            st.rerun()

    with col_assistente:
        st.subheader("✨ Assistente de Adição", help = 'Refeições de acordo com a tabela TACO - Tabela Brasileira de Composição de Alimentos')
        alvo_adicao = st.radio("Adicionar para:", ("Refeições do Dia", "Plano Alimentar"), horizontal=True, key="alvo_adicao_radio")
        
        plano_alvo_nome = None
        if alvo_adicao == "Plano Alimentar":
            lista_planos_existentes = df_planos_alimentares['nome_plano'].unique().tolist() if 'nome_plano' in df_planos_alimentares.columns else []
            if not lista_planos_existentes:
                st.info("Crie um plano no gerenciador abaixo para poder adicionar alimentos a ele.")
                return 
            plano_alvo_nome = st.selectbox("Selecione o Plano Alvo:", options=lista_planos_existentes)
        
        refeicao_escolhida = st.selectbox("Adicionar à Refeição:", options=config.OPCOES_REFEICOES)
        termo_busca = st.text_input("Buscar Alimento:")
        
        # Lógica de busca e adição de alimentos
        if termo_busca and not TABELA_ALIM.empty:
            termo_proc = utils.normalizar_texto(termo_busca)
            resultados_df = TABELA_ALIM[TABELA_ALIM[config.COL_ALIMENTO_PROC].str.contains(termo_proc, na=False)].head(25)
            
            if not resultados_df.empty:
                def format_food_details(index):
                    row = resultados_df.loc[index]
                    return (f"{row[config.COL_ALIMENTO]} (100g: {row[config.COL_ENERGIA]:.0f}kcal, "
                            f"P:{row[config.COL_PROTEINA]:.1f}g, C:{row[config.COL_CARBOIDRATO]:.1f}g, G:{row[config.COL_LIPIDEOS]:.1f}g)")

                selected_index = st.radio(
                    "Selecione um alimento:", options=resultados_df.index,
                    format_func=format_food_details, key="radio_alimentos_termo_busca"
                )
                
                alimento_selecionado = resultados_df.loc[selected_index][config.COL_ALIMENTO]
                quantidade = st.number_input("Quantidade (g):", min_value=1, value=100, step=10, key="qtd_alimento_busca")

                if st.button("➕ Adicionar Alimento", type="primary", use_container_width=True):
                    if alvo_adicao == "Refeições do Dia":
                        nova_refeicao = pd.DataFrame([{"Refeicao": refeicao_escolhida, "Alimento": alimento_selecionado, "Quantidade": quantidade}])
                        utils.adicionar_registro_df(nova_refeicao, path_refeicoes)
                        st.toast(f"'{alimento_selecionado}' adicionado!", icon="👍")
                        st.rerun()
                    elif alvo_adicao == "Plano Alimentar" and plano_alvo_nome:
                        novo_item_plano = pd.DataFrame([{'nome_plano': plano_alvo_nome, 'Refeicao': refeicao_escolhida, 'Alimento': alimento_selecionado, 'Quantidade': quantidade}])
                        utils.adicionar_registro_df(novo_item_plano, path_planos)
                        st.session_state.sb_planos_alim = plano_alvo_nome
                        st.toast(f"Adicionado ao plano '{plano_alvo_nome}'!", icon="👍")
                        st.rerun()
            elif termo_busca:
                st.info("Nenhum alimento encontrado.")

    #    Esta função será chamada quando o botão "Criar" for clicado.
    def handle_create_plan(new_plan_name, current_plans_list):
        """
        Salva o novo plano alimentar e atualiza o session_state para que
        o selectbox selecione o novo plano no próximo rerun.
        """
        if new_plan_name and new_plan_name not in current_plans_list:
            novo_plano_df = pd.DataFrame([{'nome_plano': new_plan_name, 'Refeicao': config.OPCOES_REFEICOES[0], 'Alimento': 'Exemplo (edite)', 'Quantidade': 100.0}])
            utils.adicionar_registro_df(novo_plano_df, path_planos)
            
            # Esta é a ação chave: modificamos o estado para o próximo rerun.
            st.session_state.sb_planos_alim = new_plan_name
            st.toast(f"Plano '{new_plan_name}' criado!", icon="🎉")
        else:
            # Se o nome for inválido, podemos usar o session_state para mostrar um erro.
            st.session_state.form_error = "Nome de plano inválido ou já existente."

    with st.expander("Gerenciar Meus Planos Alimentares", expanded=True):
        lista_planos = ["-- Criar Novo Plano --"] + (df_planos_alimentares['nome_plano'].unique().tolist() if 'nome_plano' in df_planos_alimentares.columns else [])
        
        if 'sb_planos_alim' not in st.session_state or st.session_state.sb_planos_alim not in lista_planos:
            st.session_state.sb_planos_alim = lista_planos[0]
            
        plano_selecionado = st.selectbox("Selecione um plano para editar ou crie um novo:", options=lista_planos, key="sb_planos_alim")
        
        if plano_selecionado == "-- Criar Novo Plano --":
            novo_nome_plano = st.text_input("Nome do Novo Plano Alimentar (ex: Dia de Treino Intenso)")
            
            # 2. Usamos o on_click no botão para chamar o callback.
            #    O botão não precisa mais estar dentro de um `if`.
            st.button(
                "Criar Plano Alimentar",
                on_click=handle_create_plan,
                args=(novo_nome_plano, lista_planos) # Passa os argumentos para o callback
            )

            # Mostra o erro se ele foi definido no callback.
            if 'form_error' in st.session_state and st.session_state.form_error:
                st.error(st.session_state.form_error)
                del st.session_state.form_error # Limpa o erro para não mostrá-lo novamente.

        elif plano_selecionado != "-- Criar Novo Plano --":
            st.markdown(f"**Editando o plano: {plano_selecionado}**")
            itens_plano = df_planos_alimentares[df_planos_alimentares['nome_plano'] == plano_selecionado].copy()
            
            itens_editados = st.data_editor(
                itens_plano, num_rows="dynamic", use_container_width=True, key=f"editor_plano_{plano_selecionado}",
                column_config={
                    "nome_plano": None,
                    "Refeicao": st.column_config.SelectboxColumn("Refeição", options=config.OPCOES_REFEICOES, required=True),
                    "Alimento": st.column_config.TextColumn("Alimento", required=True),
                    "Quantidade": st.column_config.NumberColumn("Qtd (g)", min_value=0.0, step=1.0)
                }
            )
            c1, c2, c3 = st.columns([1, 1, 1.2])
            if c1.button("💾 Salvar Alterações no Plano", key=f"save_{plano_selecionado}"):
                df_outros_planos = df_planos_alimentares[df_planos_alimentares['nome_plano'] != plano_selecionado]
                df_final = pd.concat([df_outros_planos, itens_editados], ignore_index=True)
                utils.salvar_df(df_final, path_planos)
                st.toast(f"Plano '{plano_selecionado}' salvo!", icon="💾")
                st.rerun()
                
            if c2.button("🚀 Carregar para Hoje", key=f"load_{plano_selecionado}"):
                itens_para_carregar = itens_editados.drop(columns=['nome_plano'], errors='ignore')
                utils.salvar_df(itens_para_carregar, path_refeicoes)
                st.toast(f"Plano '{plano_selecionado}' carregado para hoje.", icon="🚀")
                st.rerun()
                
            if c3.button(f"🗑️ Apagar Plano", type="secondary", key=f"delete_{plano_selecionado}"):
                df_planos_alimentares = df_planos_alimentares[df_planos_alimentares['nome_plano'] != plano_selecionado]
                utils.salvar_df(df_planos_alimentares, path_planos)
                st.session_state.sb_planos_alim = lista_planos[0]
                st.toast(f"Plano '{plano_selecionado}' apagado.", icon="🗑️")
                st.rerun()

def render_treino_tab(user_data: Dict[str, Any]):
    """
    Renderiza a aba de Treino, com sub-abas para Visão Geral, Planejamento
    e Registro de treinos.

    Args:
        user_data (Dict[str, Any]): Dicionário com os dados do usuário.
    """
    #st.header("🏋️‍♀️ Treino") # --- Removido para economizar espaço
    
    if user_data.get("dados_pessoais"):
        username = st.session_state.current_user
        
        sub_tab_plan, sub_tab_reg = st.tabs([
            "🛠️ Planejamento Completo", "💪 Registrar Treino"
        ])

        with sub_tab_plan:
            render_planejamento_sub_tab(username, user_data)
        with sub_tab_reg:
            render_registro_sub_tab(username, user_data)
    else:
        st.error("Preencha e salve seus dados pessoais na primeira aba.")


def render_planejamento_sub_tab(username: str, user_data: Dict[str, Any]):
    """
    Renderiza a sub-aba de planejamento, com a adição do tipo de exercício.
    """
    st.subheader("Passo 1: Crie seus Modelos de Treino (Ex: Treino A, Treino B, Cardio)")

    # --- CARREGAMENTO DE DADOS ---
    df_planos_treino = user_data.get("df_planos_treino", pd.DataFrame())
    df_exercicios_todos = user_data.get("df_exercicios", pd.DataFrame())
    df_macro = user_data.get("df_macrociclos", pd.DataFrame())
    df_meso = user_data.get("df_mesociclos", pd.DataFrame())
    df_plano_sem = user_data.get("df_plano_semanal", pd.DataFrame())

    path_planos_treino = utils.get_user_data_path(username, config.FILE_PLANOS_TREINO)
    path_exercicios = utils.get_user_data_path(username, config.FILE_PLANOS_EXERCICIOS)
    path_macro = utils.get_user_data_path(username, config.FILE_MACROCICLOS)
    path_meso = utils.get_user_data_path(username, config.FILE_MESOCICLOS)
    path_plano_sem = utils.get_user_data_path(username, config.FILE_PLANO_SEMANAL)
    
    path_exercicios_db = config.DATA_DIR / "exercicios.json"
    exercisedb = utils.carregar_banco_exercicios(path_exercicios_db)

    with st.expander("Modelos de Treino", expanded=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            if 'id_plano' not in df_planos_treino.columns:
                df_planos_treino = pd.DataFrame(columns=['id_plano', 'nome_plano'])
            lista_planos = ["-- Criar Novo Plano --"] + df_planos_treino['nome_plano'].tolist()
            opcao_plano = st.selectbox("Selecione para editar ou crie um novo:", options=lista_planos, key="sb_planos_unificado")

            if opcao_plano == "-- Criar Novo Plano --":
                novo_nome_plano = st.text_input("Nome do Novo Modelo de Treino")
                if st.button("Criar Modelo"):
                    if novo_nome_plano and novo_nome_plano not in df_planos_treino['nome_plano'].tolist():
                        novo_id = df_planos_treino['id_plano'].max() + 1 if not df_planos_treino.empty else 1
                        novo_plano_df = pd.DataFrame([{'id_plano': novo_id, 'nome_plano': novo_nome_plano}])
                        df_planos_treino = pd.concat([df_planos_treino, novo_plano_df], ignore_index=True)
                        utils.salvar_df(df_planos_treino, path_planos_treino)
                        st.toast(f"Modelo '{novo_nome_plano}' criado!", icon="✅")
                        st.rerun()
                    else:
                        st.error("Nome de modelo inválido ou já existente.")

            elif opcao_plano != "-- Criar Novo Plano --":
                if st.button(f"🗑️ Apagar Modelo '{opcao_plano}'", type="secondary"):
                    st.session_state[f'confirm_delete_plano_{opcao_plano}'] = True
                if st.session_state.get(f'confirm_delete_plano_{opcao_plano}', False):
                    st.warning(f"Tem certeza? Isso apagará o modelo e todos os exercícios associados a ele.")
                    col_conf1, col_conf2 = st.columns(2)
                    if col_conf1.button("Sim, apagar", type="primary"):
                        id_plano_para_apagar = df_planos_treino[df_planos_treino['nome_plano'] == opcao_plano]['id_plano'].iloc[0]
                        df_planos_treino = df_planos_treino[df_planos_treino['id_plano'] != id_plano_para_apagar]
                        df_exercicios_todos = df_exercicios_todos[df_exercicios_todos['id_plano'] != id_plano_para_apagar]
                        utils.salvar_df(df_planos_treino, path_planos_treino)
                        utils.salvar_df(df_exercicios_todos, path_exercicios)
                        st.session_state[f'confirm_delete_plano_{opcao_plano}'] = False
                        st.toast(f"Modelo '{opcao_plano}' apagado.", icon="🗑️")
                        st.rerun()
                    if col_conf2.button("Cancelar"):
                        st.session_state[f'confirm_delete_plano_{opcao_plano}'] = False
                        st.rerun()

                # --- ASSISTENTE DE ADIÇÃO LOCAL ---
                st.markdown("---")
                st.subheader("Assistente de Adição")

                if exercisedb:
                    all_muscles = set()
                    for ex in exercisedb:
                        if isinstance(ex, dict):
                            for muscle in ex.get("primaryMuscles", []):
                                all_muscles.add(muscle.title())
                    
                    muscle_options = ["Todos"] + sorted(list(all_muscles))
                    selected_muscle = st.selectbox("Filtrar por grupo muscular:", options=muscle_options)
                    
                    search_term = st.text_input("Buscar exercício por nome:").lower()

                    if search_term or selected_muscle != "Todos":
                        filtered_exercises = []
                        for ex in exercisedb:
                            if not isinstance(ex, dict): continue

                            muscle_match = (selected_muscle == "Todos" or 
                                            any(m.title() == selected_muscle for m in ex.get("primaryMuscles", [])))
                            
                            name_match = search_term in ex.get("name", "").lower()
                            
                            if muscle_match and name_match:
                                filtered_exercises.append(ex)

                        if not filtered_exercises:
                            st.info("Nenhum exercício encontrado.")
                        
                        base_image_path = config.ASSETS_DIR / "exercises"
                        for i, ex in enumerate(filtered_exercises[:20]):
                            ex_name = ex.get("name")
                            instruction = ex.get("instructions", "No instructions available.")
                            if not ex_name: continue
                            
                            
                            with st.container(border=True):
                                col_1, col_2 = st.columns([1, 2])
                                with col_1:
                                    st.markdown(f"**{ex_name}**")
                                    
                                    images = ex.get("images", [])
                                    if len(images) == 2:
                                        image_path1 = base_image_path / Path(images[0])
                                        image_path2 = base_image_path / Path(images[1])
                                        
                                        if image_path1.exists() and image_path2.exists():
                                            anim_html = utils.get_image_animation_html(image_path1, image_path2, width=300)
                                            components.html(anim_html, height=330)

                                    elif images:
                                        image_path = base_image_path / Path(images[0])
                                        if image_path.exists():
                                            st.image(str(image_path), width=150)
                                
                                with col_2:
                                    st.markdown(f"**Grupo Muscular:** {', '.join(ex.get('primaryMuscles', []))}")
                                    st.markdown(f"**Músculo Secundário:** {', '.join(ex.get('secondaryMuscles', []))}")
                                    st.markdown(f"**Equipamento:** {ex.get('equipment', [])}")
                                    st.markdown(f"**Nível:** {ex.get('level', 'Desconhecido')}")

                                # Gráficos de músculos (HTML com sobreposição)
                                st.markdown(f"**Gráfico de Músculos:**")
                                image_1, image_2 = st.columns(2)
                                primary = ex.get("primaryMuscles", [])
                                secondary = ex.get("secondaryMuscles", [])

                                with image_1:
                                    # Filtra músculos para a vista frontal
                                    front_primary = [m for m in primary if m.lower() in config.FRONT_MUSCLES]
                                    front_secondary = [m for m in secondary if m.lower() in config.FRONT_MUSCLES]
                                    # Renderiza o diagrama frontal
                                    html_front = utils.render_muscle_diagram(config.PATH_GRAFICO_MUSCULOS_FRONT, front_primary, front_secondary, width=150)
                                    components.html(html_front, height=320)

                                with image_2:
                                    # Filtra músculos para a vista traseira
                                    back_primary = [m for m in primary if m.lower() in config.BACK_MUSCLES]
                                    back_secondary = [m for m in secondary if m.lower() in config.BACK_MUSCLES]
                                    # Renderiza o diagrama traseiro
                                    html_back = utils.render_muscle_diagram(config.PATH_GRAFICO_MUSCULOS_BACK, back_primary, back_secondary, width=150)
                                    components.html(html_back, height=320)

                                # Exibe as instruções, se houver
                                st.markdown('**Instruções:**') if instruction else None
                                for inst in instruction if instruction else []:
                                    st.markdown(f"{inst}\n")

                                if st.button("Adicionar ao plano", key=f"add_local_{i}_{ex.get('id', ex_name)}", use_container_width=True):
                                    id_plano_selecionado = df_planos_treino[df_planos_treino['nome_plano'] == opcao_plano]['id_plano'].iloc[0]
                                    novo_exercicio = pd.DataFrame([{
                                        'id_plano': id_plano_selecionado,
                                        'nome_exercicio': ex_name,
                                        'tipo_exercicio': 'Musculação',
                                        'series_planejadas': 3,
                                        'repeticoes_planejadas': '8-12'
                                    }])
                                    df_exercicios_todos = pd.concat([df_exercicios_todos, novo_exercicio], ignore_index=True)
                                    utils.salvar_df(df_exercicios_todos, path_exercicios)
                                    st.toast(f"'{ex_name}' adicionado ao plano '{opcao_plano}'!")
                                    st.rerun()

        with c2:
            if opcao_plano != "-- Criar Novo Plano --":
                st.markdown(f"##### Exercícios do Modelo: **{opcao_plano}**")
                id_plano_selecionado = df_planos_treino[df_planos_treino['nome_plano'] == opcao_plano]['id_plano'].iloc[0]
                
                if 'tipo_exercicio' not in df_exercicios_todos.columns:
                    df_exercicios_todos['tipo_exercicio'] = "Musculação"

                df_exercicios_plano = df_exercicios_todos[df_exercicios_todos['id_plano'] == id_plano_selecionado].copy()
                
                if 'repeticoes_planejadas' in df_exercicios_plano.columns:
                    df_exercicios_plano['repeticoes_planejadas'] = df_exercicios_plano['repeticoes_planejadas'].astype(str)

                exercicios_editados = st.data_editor(
                    df_exercicios_plano[['nome_exercicio', 'tipo_exercicio', 'series_planejadas', 'repeticoes_planejadas']],
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"editor_exercicios_{id_plano_selecionado}",
                    column_config={
                        "nome_exercicio": st.column_config.TextColumn("Exercício", required=True),
                        "tipo_exercicio": st.column_config.SelectboxColumn("Tipo", options=["Musculação", "Cardio"], required=True),
                        "series_planejadas": st.column_config.NumberColumn("Séries", min_value=1),
                        "repeticoes_planejadas": st.column_config.TextColumn("Meta (Reps ou Min)")
                    }
                )
                if st.button("💾 Salvar Exercícios neste Modelo"):
                    df_exercicios_outros = df_exercicios_todos[df_exercicios_todos['id_plano'] != id_plano_selecionado]
                    novos_exercicios = exercicios_editados.copy()
                    novos_exercicios['id_plano'] = id_plano_selecionado
                    df_final = pd.concat([df_exercicios_outros, novos_exercicios], ignore_index=True)
                    utils.salvar_df(df_final, path_exercicios)
                    st.toast("Exercícios do modelo salvos com sucesso!", icon="💾")
                    st.rerun()

    st.markdown("---")
    st.subheader("Passo 2: Estruture a Periodização (Macrociclo, Mesociclos e Semanas)")
    
    st.markdown("##### 1. Macrociclo")
    lista_macros = ["-- Criar Novo Macrociclo --"] + df_macro['nome'].tolist() if 'nome' in df_macro.columns else ["-- Criar Novo Macrociclo --"]
    macro_selecionado_nome = st.selectbox("Selecione um Macrociclo para gerenciar ou crie um novo", options=lista_macros, key="macro_select_planning")

    if macro_selecionado_nome == "-- Criar Novo Macrociclo --":
        with st.form("form_novo_macro"):
            st.write("Crie um novo grande ciclo de treino (ex: Preparação Verão 2025).")
            nome_macro = st.text_input("Nome do Macrociclo")
            objetivo_macro = st.text_area("Objetivo Principal")
            col1, col2 = st.columns(2)
            data_inicio_macro = col1.date_input("Data de Início", value=date.today())
            data_fim_macro = col2.date_input("Data de Fim", value=date.today() + pd.DateOffset(months=3))
            if st.form_submit_button("Criar Macrociclo"):
                if nome_macro and data_inicio_macro < data_fim_macro:
                    max_id = df_macro['id_macrociclo'].max() if not df_macro.empty and 'id_macrociclo' in df_macro.columns else 0
                    novo_macro = pd.DataFrame([{'id_macrociclo': max_id + 1, 'nome': nome_macro, 'objetivo_principal': objetivo_macro, 'data_inicio': data_inicio_macro.strftime('%Y-%m-%d'), 'data_fim': data_fim_macro.strftime('%Y-%m-%d')}])
                    df_macro = pd.concat([df_macro, novo_macro], ignore_index=True)
                    utils.salvar_df(df_macro, path_macro)
                    st.toast("Macrociclo criado!", icon="🎉")
                    st.rerun()
                else:
                    st.error("Preencha o nome e garanta que a data de início seja anterior à data de fim.")
    
    elif macro_selecionado_nome:
        id_macro_ativo = df_macro[df_macro['nome'] == macro_selecionado_nome]['id_macrociclo'].iloc[0]

        if st.button(f"🗑️ Apagar Macrociclo '{macro_selecionado_nome}'", type="secondary"):
            st.session_state[f'confirm_delete_macro_{id_macro_ativo}'] = True
        
        if st.session_state.get(f'confirm_delete_macro_{id_macro_ativo}', False):
            st.warning(f"Tem certeza que deseja apagar o macrociclo '{macro_selecionado_nome}'? Todos os mesociclos e planos semanais associados serão perdidos.")
            col_conf1, col_conf2 = st.columns(2)
            if col_conf1.button("Sim, apagar", type="primary"):
                ids_mesos_para_apagar = df_meso[df_meso['id_macrociclo'] == id_macro_ativo]['id_mesociclo'].tolist() if 'id_macrociclo' in df_meso.columns else []
                df_macro = df_macro[df_macro['id_macrociclo'] != id_macro_ativo]
                df_meso = df_meso[df_meso['id_macrociclo'] != id_macro_ativo]
                if ids_mesos_para_apagar and 'id_mesociclo' in df_plano_sem.columns:
                    df_plano_sem = df_plano_sem[~df_plano_sem['id_mesociclo'].isin(ids_mesos_para_apagar)]
                utils.salvar_df(df_macro, path_macro)
                utils.salvar_df(df_meso, path_meso)
                utils.salvar_df(df_plano_sem, path_plano_sem)
                st.session_state[f'confirm_delete_macro_{id_macro_ativo}'] = False
                st.toast(f"Macrociclo apagado.", icon="🗑️")
                st.rerun()
            if col_conf2.button("Cancelar"):
                st.session_state[f'confirm_delete_macro_{id_macro_ativo}'] = False
                st.rerun()

        st.markdown("---")
        st.markdown(f"##### 2. Mesociclos (As Fases do Plano '{macro_selecionado_nome}')")
        mesos_do_macro = df_meso[df_meso['id_macrociclo'] == id_macro_ativo].copy() if 'id_macrociclo' in df_meso.columns else pd.DataFrame()
        colunas_meso = {'id_mesociclo': pd.Series(dtype='Int64'), 'id_macrociclo': pd.Series(dtype='Int64'), 'nome': pd.Series(dtype='str'), 'ordem': pd.Series(dtype='Int64'), 'duracao_semanas': pd.Series(dtype='Int64'), 'foco_principal': pd.Series(dtype='str')}
        for col, dtype_series in colunas_meso.items():
            if col not in mesos_do_macro.columns:
                mesos_do_macro[col] = dtype_series
        mesos_do_macro['duracao_semanas'] = mesos_do_macro['duracao_semanas'].fillna(4)
        mesos_do_macro = mesos_do_macro.astype({'nome': str, 'foco_principal': str, 'ordem': 'Int64', 'duracao_semanas': 'Int64'})
        mesos_editados = st.data_editor(mesos_do_macro, num_rows="dynamic", use_container_width=True, key="editor_meso", column_config={"id_mesociclo": None, "id_macrociclo": None, "nome": st.column_config.TextColumn("Nome do Mesociclo", required=True), "ordem": st.column_config.NumberColumn("Ordem", min_value=1, required=True), "duracao_semanas": st.column_config.NumberColumn("Duração (Semanas)", min_value=1, required=True, default=4), "foco_principal": st.column_config.TextColumn("Foco Principal")})
        if st.button("Salvar Mesociclos"):
            df_meso_outros = df_meso[df_meso['id_macrociclo'] != id_macro_ativo] if 'id_macrociclo' in df_meso.columns else pd.DataFrame(columns=df_meso.columns)
            max_id = df_meso['id_mesociclo'].max() if not df_meso.empty and 'id_mesociclo' in df_meso.columns else 0
            novos_mesos = mesos_editados.copy().dropna(subset=['nome', 'ordem', 'duracao_semanas'])
            novos_mesos['id_mesociclo'] = novos_mesos['id_mesociclo'].fillna(0)
            final_mesos_list = []
            for _, row in novos_mesos.iterrows():
                if row['id_mesociclo'] == 0:
                    max_id += 1
                    row['id_mesociclo'] = max_id
                final_mesos_list.append(row)
            novos_mesos_com_ids = pd.DataFrame(final_mesos_list)
            novos_mesos_com_ids['id_macrociclo'] = id_macro_ativo
            df_final_meso = pd.concat([df_meso_outros, novos_mesos_com_ids], ignore_index=True)
            utils.salvar_df(df_final_meso, path_meso)
            st.toast("Mesociclos salvos!", icon="🗓️")
            st.rerun()

        st.markdown("---")
        st.markdown("##### 3. Plano Semanal (A Rotina da Semana)")
        lista_mesos_nomes = mesos_do_macro['nome'].dropna().tolist() if not mesos_do_macro.empty else []
        if lista_mesos_nomes:
            meso_selecionado_nome = st.selectbox("Selecione um Mesociclo para planejar as semanas", options=lista_mesos_nomes)
            meso_selecionado_info = mesos_do_macro[mesos_do_macro['nome'] == meso_selecionado_nome]
            if not meso_selecionado_info.empty:
                id_meso_ativo = meso_selecionado_info['id_mesociclo'].iloc[0]
                duracao_meso = meso_selecionado_info['duracao_semanas'].iloc[0]
                semana_num = st.number_input(f"Selecione a Semana para planejar (1 a {int(duracao_meso)})", min_value=1, max_value=int(duracao_meso), step=1, key=f"semana_num_{id_meso_ativo}")
                dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
                planos_disponiveis = ["Descanso"] + (df_planos_treino['nome_plano'].tolist() if 'nome_plano' in df_planos_treino.columns else [])
                plano_semanal_salvo = df_plano_sem[(df_plano_sem['id_mesociclo'] == id_meso_ativo) & (df_plano_sem['semana_numero'] == semana_num)] if 'id_mesociclo' in df_plano_sem.columns else pd.DataFrame()
                if plano_semanal_salvo.empty:
                    plano_semanal_atual = pd.DataFrame({'dia_da_semana': dias_semana, 'plano_treino': ["Descanso"]*7})
                else:
                    plano_semanal_atual = plano_semanal_salvo[['dia_da_semana', 'plano_treino']].set_index('dia_da_semana').reindex(dias_semana).fillna("Descanso").reset_index()
                plano_semanal_editado = st.data_editor(plano_semanal_atual, use_container_width=True, hide_index=True, key=f"editor_semana_{id_meso_ativo}_{semana_num}", column_config={"dia_da_semana": st.column_config.TextColumn("Dia da Semana", disabled=True), "plano_treino": st.column_config.SelectboxColumn("Modelo de Treino", options=planos_disponiveis, required=True)})
                
                col_save, col_clear = st.columns(2)
                with col_save:
                    if st.button("💾 Salvar Plano da Semana"):
                        df_plano_sem_outros = df_plano_sem.drop(plano_semanal_salvo.index) if not plano_semanal_salvo.empty else df_plano_sem
                        novo_plano_semanal = plano_semanal_editado.copy()
                        novo_plano_semanal['id_mesociclo'] = id_meso_ativo
                        novo_plano_semanal['semana_numero'] = semana_num
                        df_final_semanal = pd.concat([df_plano_sem_outros, novo_plano_semanal], ignore_index=True)
                        utils.salvar_df(df_final_semanal, path_plano_sem)
                        st.toast(f"Plano para a Semana {semana_num} salvo!", icon="✅")
                        st.rerun()
                with col_clear:
                    if st.button("🧹 Limpar Plano desta Semana", type="secondary"):
                        if not plano_semanal_salvo.empty:
                            df_plano_sem = df_plano_sem.drop(plano_semanal_salvo.index)
                            utils.salvar_df(df_plano_sem, path_plano_sem)
                            st.toast(f"Plano para a Semana {semana_num} limpo.", icon="🧹")
                            st.rerun()
        else:
            st.info("Crie e salve um mesociclo acima para poder planejar as semanas.")

def render_registro_avulso_form(username: str, user_data: Dict[str, Any]):
    """Renderiza o formulário simples para registrar um treino avulso."""
    st.subheader("Registrar Treino Avulso")
    df_planos_treino = user_data.get("df_planos_treino", pd.DataFrame()) #
    dados_pessoais = user_data.get("dados_pessoais", {}) #
    path_treinos = utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES) #

    lista_planos = ["Nenhum (Avulso)"] + (df_planos_treino['nome_plano'].tolist() if 'nome_plano' in df_planos_treino.columns else []) #
    plano_executado = st.selectbox("Qual plano de treino você executou?", options=lista_planos, key="plano_avulso") #

    default_cardio = "cardio" in plano_executado.lower() if plano_executado != "Nenhum (Avulso)" else False #

    c1, c2, c3, c4 = st.columns(4) #
    cardio = c1.toggle("Cardio?", value=default_cardio, key="cardio_reg_avulso") #
    intensidade_tr = c2.selectbox("Intensidade", config.OPCOES_INTENSIDADE_TREINO, index=1, key="intensidade_reg_avulso") #
    duracao_min = c3.number_input("Duração (min)", 0, 600, 60, 5, key="duracao_reg_avulso") #
    carga_total = c4.number_input("Carga total (kg)", 0.0, step=5.0, value=5000.0, key="carga_reg_avulso", disabled=cardio) #

    gasto_est = logic.calcular_gasto_treino(cardio, intensidade_tr, duracao_min, carga_total, dados_pessoais.get(config.COL_PESO, 70.0)) #
    st.metric("Gasto calórico estimado", f"{gasto_est:.0f} kcal") #

    with st.form("form_add_treino_avulso"): #
        data_treino = st.date_input("Data do treino", value=date.today()) #
        if st.form_submit_button("Adicionar Treino Avulso", type="primary"): #
            novo_treino = pd.DataFrame([{ #
                config.COL_DATA: data_treino.strftime("%d/%m/%Y"), #
                "plano_executado": plano_executado if plano_executado != "Nenhum (Avulso)" else "Avulso", #
                "tipo treino": "Cardio" if cardio else "Musculação", #
                "duracao min": duracao_min, #
                "calorias": round(gasto_est, 2) #
            }]) #
            utils.adicionar_registro_df(novo_treino, path_treinos) #
            st.toast("Treino avulso adicionado com sucesso!", icon="💪") #
            st.rerun() #

def render_registro_sub_tab(username: str, user_data: Dict[str, Any]):
    """
    Renderiza a sub-aba para registrar treinos, com um painel de controle
    customizado para corresponder fielmente ao layout do usuário.
    """
    # --- LÓGICA DE DADOS E TIMERS (INICIALIZAÇÃO) ---
    workout_today = logic.get_workout_for_day(user_data, date.today())
    df_log_exercicios = user_data.get("df_log_exercicios", pd.DataFrame())

    # --- Carrega o banco de dados de exercícios para buscar as imagens ---
    path_exercicios_db = config.DATA_DIR / "exercises.json"
    exercisedb_data = utils.carregar_banco_exercicios(path_exercicios_db)
    
    exercisedb = []
    if isinstance(exercisedb_data, list):
        exercisedb = exercisedb_data
    elif isinstance(exercisedb_data, dict) and "exercises" in exercisedb_data:
        exercisedb = exercisedb_data["exercises"]
    
    # Cria um mapa de consulta para encontrar imagens rapidamente
    exercise_image_map = {}
    base_image_path = config.ASSETS_DIR / "exercises"
    if exercisedb:
        for ex_data in exercisedb:
            if isinstance(ex_data, dict) and ex_data.get("name") and ex_data.get("images"):
                normalized_name = utils.normalizar_texto(ex_data["name"])
                image_paths = [base_image_path / Path(img_file) for img_file in ex_data["images"]]
                exercise_image_map[normalized_name] = image_paths

    if 'timer_started' not in st.session_state:
        st.session_state.timer_started = False
        st.session_state.start_time = None
        st.session_state.elapsed_minutes = 0.0
    if 'rest_timer_running' not in st.session_state:
        st.session_state.rest_timer_running = False
        st.session_state.rest_end_time = None
    if 'total_rest_seconds' not in st.session_state:
        st.session_state.total_rest_seconds = 0

    # --- ALTERAÇÃO AQUI: Componente movido para a sidebar da forma correta ---
    # Colocamos a chamada dentro de um bloco "with st.sidebar:"
    with st.sidebar:
        if st.session_state.timer_started or st.session_state.rest_timer_running:
            st_autorefresh(interval=1000, key="global_timer_refresher")

    # --- PAINEL DE CONTROLE DO TREINO ---
    with st.container(border=True):
        col1, col2, col3 = st.columns([2.5, 3, 3])
        with col1:
            if st.session_state.timer_started and st.session_state.start_time:
                elapsed = datetime.now() - st.session_state.start_time
                hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                minutes_total = int(st.session_state.elapsed_minutes)
                seconds_total = int((st.session_state.elapsed_minutes * 60) % 60)
                time_str = f"00:{minutes_total:02}:{seconds_total:02}"
            st.markdown("<p style='font-size: 0.9rem; color: rgba(250, 250, 250, 0.7);'>Tempo Total</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size: 2.5rem; font-weight: bold; margin-top: -10px;'>{time_str}</p>", unsafe_allow_html=True)
            btn_c1, btn_c2, btn_c3 = st.columns(3)
            if btn_c1.button("▶️ Iniciar", use_container_width=True, disabled=st.session_state.timer_started):
                st.session_state.timer_started = True
                st.session_state.start_time = datetime.now()
                st.rerun()
            if btn_c2.button("⏸️ Parar", use_container_width=True, disabled=not st.session_state.timer_started):
                if st.session_state.start_time:
                    elapsed_time = datetime.now() - st.session_state.start_time
                    st.session_state.elapsed_minutes = elapsed_time.total_seconds() / 60
                st.session_state.timer_started = False
                st.rerun()
            if btn_c3.button("🔄 Zerar", use_container_width=True):
                st.session_state.timer_started = False
                st.session_state.start_time = None
                st.session_state.elapsed_minutes = 0.0
                st.session_state.total_rest_seconds = 0
                st.rerun()
        with col2:
            if workout_today:
                plan_name = workout_today['nome_plano']
                st.markdown(f"""
                <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;'>
                    <p style='font-size: 1.5rem; font-weight: bold; text-align: center; margin-bottom: -5px;'>Plano de hoje:</p>
                    <p style='font-size: 1.5rem; font-weight: bold; text-align: center;'>{plan_name}</p>
                </div>
                """, unsafe_allow_html=True)
        with col3:
            rest_controls_col, rest_display_col = st.columns(2)
            with rest_controls_col:
                st.markdown("<p style='font-size: 0.9rem; color: rgba(250, 250, 250, 0.7);'>Timer de Descanso</p>", unsafe_allow_html=True)
                default_rest_time = st.number_input("Segundos", min_value=10, max_value=300, value=60, step=5, label_visibility="collapsed")
                if st.button("Iniciar Descanso", use_container_width=True, disabled=st.session_state.rest_timer_running, key="start_rest_button_final_v3"):
                    st.session_state.rest_timer_running = True
                    st.session_state.rest_end_time = time.time() + default_rest_time
                    st.session_state.total_rest_seconds += default_rest_time
                    st.rerun()
            with rest_display_col:
                total_rest_min, total_rest_sec = divmod(st.session_state.total_rest_seconds, 60)
                total_rest_str = f"{total_rest_min:02d}:{total_rest_sec:02d}"
                if st.session_state.rest_timer_running and st.session_state.rest_end_time:
                    remaining_time = st.session_state.rest_end_time - time.time()
                    if remaining_time > 0:
                        minutes, seconds = divmod(int(remaining_time), 60)
                        time_str = f"{minutes:02}:{seconds:02}"
                        color = "#FF4B4B" if remaining_time <= 11 else "inherit"
                        st.markdown(f"""
                        <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;'>
                            <p style='font-size: 3.5rem; color: {color}; font-weight: bold;'>{time_str}</p>
                            <p style='font-size: 0.9rem; color: rgba(250, 250, 250, 0.7); margin-bottom: 10px;'>Descanso total: {total_rest_str}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.session_state.rest_timer_running = False
                        st.rerun()
                else:
                    st.markdown(f"""
                    <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;'>
                        <p style='font-size: 0.9rem; color: rgba(250, 250, 250, 0.7);'>Aguardando início</p>
                        <p style='font-family: monospace; font-size: 2rem; margin-top: -10px; margin-bottom: 5px;'>-- : --</p>
                        <p style='font-size: 0.9rem; color: rgba(250, 250, 250, 0.7);'>Descanso total: {total_rest_str}</p>
                    </div>
                    """, unsafe_allow_html=True)

    # --- LÓGICA PARA RENDERIZAR O PLANO DE TREINO ---
    if workout_today:
        exercicios_df = workout_today['exercicios']
        with st.form("form_log_treino_detalhado"):
            for index, exercicio in exercicios_df.iterrows():
                with st.popover(f"**{exercicio['nome_exercicio']}**"):
                    st.markdown(f"#### {exercicio['nome_exercicio']}")
                    
                    nome_normalizado = utils.normalizar_texto(exercicio['nome_exercicio'])
                    image_paths = exercise_image_map.get(nome_normalizado)

                    if image_paths and len(image_paths) == 2:
                        image_path1, image_path2 = image_paths[0], image_paths[1]
                        if image_path1.exists() and image_path2.exists():
                            anim_html = utils.get_image_animation_html(image_path1, image_path2, width=300)
                            components.html(anim_html, height=310)
                        else:
                            st.warning(f"Ficheiros de imagem não encontrados para '{exercicio['nome_exercicio']}'.")
                    elif image_paths and image_paths[0].exists():
                        st.image(str(image_paths[0]))
                    else:
                        st.warning(f"Imagem não encontrada para '{exercicio['nome_exercicio']}'.")

                tipo_exercicio = exercicio.get('tipo_exercicio', 'Musculação')
                previous_performance = logic.get_previous_performance(df_log_exercicios, exercicio['nome_exercicio'])

                if tipo_exercicio == 'Cardio':
                    col_header = st.columns([0.8, 2, 2, 2.4, 0.8])
                    col_header[0].write("**Série**")
                    col_header[1].write("**Anterior**")
                    col_header[2].write("**Meta**")
                    col_header[3].write("**Minutos**")
                    col_header[4].write("✔")
                    num_series = int(exercicio.get('series_planejadas', 1))
                    for i in range(1, num_series + 1):
                        cols = st.columns([0.8, 2, 2, 2.4, 0.8])
                        key_base = f"{exercicio['nome_exercicio']}_{i}"
                        cols[0].markdown(f"**{i}**")
                        cols[1].markdown(f"`{previous_performance}`")
                        cols[2].markdown(f"`{exercicio['repeticoes_planejadas']}`")
                        cols[3].number_input("Min", key=f"min_{key_base}", min_value=0, step=1, label_visibility="collapsed")
                        cols[4].checkbox("Feito", key=f"done_{key_base}", label_visibility="collapsed")
                
                else: # Musculação
                    col_header = st.columns([0.8, 2, 2, 1.2, 1.2, 0.8])
                    col_header[0].write("**Série**")
                    col_header[1].write("**Anterior**")
                    col_header[2].write("**Meta**")
                    col_header[3].write("**kg**")
                    col_header[4].write("**Reps**")
                    col_header[5].write("✔")
                    num_series = int(exercicio.get('series_planejadas', 1))
                    for i in range(1, num_series + 1):
                        cols = st.columns([0.8, 2, 2, 1.2, 1.2, 0.8])
                        key_base = f"{exercicio['nome_exercicio']}_{i}"
                        cols[0].markdown(f"**{i}**")
                        cols[1].markdown(f"`{previous_performance}`")
                        cols[2].markdown(f"`{exercicio['repeticoes_planejadas']} reps`")
                        cols[3].number_input("kg", key=f"kg_{key_base}", min_value=0.0, step=0.5, label_visibility="collapsed")
                        cols[4].number_input("reps", key=f"reps_{key_base}", min_value=0, step=1, label_visibility="collapsed")
                        cols[5].checkbox("Feito", key=f"done_{key_base}", label_visibility="collapsed")
                st.markdown("---")
            st.subheader("Resumo da Sessão")
            
            c1_sum, c2_sum, c3_sum = st.columns(3)
            duracao_min_total = c1_sum.number_input(
                "Duração Total do Treino (min)", 
                min_value=0, 
                value=int(round(st.session_state.elapsed_minutes, 0)), 
                step=1
            )
            intensidade_tr = c2_sum.selectbox("Intensidade Percebida", config.OPCOES_INTENSIDADE_TREINO, index=1)
            data_treino = c3_sum.date_input("Data do treino", value=date.today())

            submitted = st.form_submit_button("Salvar Treino", type="primary", use_container_width=True)

            if submitted:
                new_log_entries = []
                total_carga = 0
                is_cardio_session = True 

                for index, exercicio in exercicios_df.iterrows():
                    tipo_exercicio = exercicio.get('tipo_exercicio', 'Musculação')
                    num_series = int(exercicio.get('series_planejadas', 1))
                    for i in range(1, num_series + 1):
                        key_base = f"{exercicio['nome_exercicio']}_{i}"
                        if st.session_state[f'done_{key_base}']:
                            log_entry = {'data': data_treino.strftime("%d/%m/%Y"), 'nome_exercicio': exercicio['nome_exercicio'], 'set': i}
                            if tipo_exercicio == 'Cardio':
                                log_entry['minutos_realizados'] = st.session_state[f'min_{key_base}']
                                log_entry['kg_realizado'] = 0
                                log_entry['reps_realizadas'] = 0
                            else: # Musculação
                                is_cardio_session = False
                                kg = st.session_state[f'kg_{key_base}']
                                reps = st.session_state[f'reps_{key_base}']
                                log_entry['kg_realizado'] = kg
                                log_entry['reps_realizadas'] = reps
                                log_entry['minutos_realizados'] = 0
                                total_carga += (kg * reps)
                            new_log_entries.append(log_entry)
                
                if not new_log_entries:
                    st.warning("Nenhuma série foi marcada como 'Feito'. O treino não foi salvo.")
                    return

                path_log_exercicios = utils.get_user_data_path(username, config.FILE_LOG_EXERCICIOS)
                utils.adicionar_registro_df(pd.DataFrame(new_log_entries), path_log_exercicios)

                dados_pessoais = user_data.get("dados_pessoais", {})
                peso_usuario = dados_pessoais.get(config.COL_PESO, 70.0)
                gasto_est = logic.calcular_gasto_treino(
                    cardio=is_cardio_session, intensidade=intensidade_tr,
                    duracao=duracao_min_total, carga=total_carga, peso=peso_usuario
                )
                path_treinos_simples = utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES)
                novo_treino_simples = pd.DataFrame([{'data': data_treino.strftime("%d/%m/%Y"), 'plano_executado': workout_today['nome_plano'], 'tipo treino': "Cardio" if is_cardio_session else "Musculação", 'duracao min': duracao_min_total, 'calorias': round(gasto_est, 2)}])
                utils.adicionar_registro_df(novo_treino_simples, path_treinos_simples)

                st.session_state.timer_started = False
                st.session_state.start_time = None
                st.session_state.elapsed_minutes = 0.0
                st.session_state.rest_timer_running = False
                st.session_state.rest_end_time = None

                st.toast("Treino salvo com sucesso!", icon="🎉")
                st.rerun()
    else:
        st.info("Nenhum treino planejado para hoje. Registre um treino avulso abaixo.")
        render_registro_avulso_form(username, user_data)
    
    dft_simples = user_data.get("df_log_treinos", pd.DataFrame())
    with st.expander("Histórico de Treinos Realizados (clique para editar/apagar)"):
        if not dft_simples.empty:
            dft_simples[config.COL_DATA] = pd.to_datetime(dft_simples[config.COL_DATA], format="%d/%m/%Y")
            dft_simples_sorted = dft_simples.sort_values(by=config.COL_DATA, ascending=False)
            dft_editado = st.data_editor(dft_simples_sorted, num_rows="dynamic", use_container_width=True, key="editor_treinos_realizados")
            
            if st.button("💾 Salvar Alterações no Histórico", key="salvar_historico_treino"):
                dft_editado[config.COL_DATA] = pd.to_datetime(dft_editado[config.COL_DATA]).dt.strftime('%d/%m/%Y')
                utils.salvar_df(dft_editado, utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES))
                st.toast("Histórico de treinos atualizado!", icon="💾")
                st.rerun()

def render_evolucao_tab(user_data: Dict[str, Any]):
    """
    Renderiza a aba de Evolução, agora com os gráficos de composição corporal e IMC.
    """
    dados_pessoais = user_data.get("dados_pessoais", {})
    if not dados_pessoais:
        st.error("Preencha e salve seus dados pessoais na primeira aba.")
        return

    username = st.session_state.current_user
    path_evolucao = utils.get_user_data_path(username, config.FILE_EVOLUCAO)
    dfe_final = user_data.get("df_evolucao", pd.DataFrame())
    df_obj = user_data.get("df_objetivo", pd.DataFrame())
    objetivo_info = df_obj.iloc[0].to_dict() if not df_obj.empty else {}

    with st.expander("Adicionar novas medidas", expanded=False):
        with st.form("form_add_medida"):
            c1, c2 = st.columns(2)
            data_med = c1.date_input("Data da Medição", value=date.today())
            peso_in = c2.number_input("Peso (kg)", 0.0, step=0.1, value=dados_pessoais.get(config.COL_PESO, 70.0))
            c3, c4, c5 = st.columns(3)
            gord_corp = c3.number_input("Gordura corporal (%)", 0.0, step=0.1, value=dados_pessoais.get("gordura_corporal", 0.0))
            gord_visc = c4.number_input("Gordura visceral (%)", 0.0, step=0.1, value=dados_pessoais.get("gordura_visceral", 0.0))
            musc_esq = c5.number_input("Músculos (%)", 0.0, step=0.1, value=dados_pessoais.get("massa_muscular", 0.0))
            c6, c7, c8, c9 = st.columns(4)
            cintura = c6.number_input("Cintura (cm)", 0.0, step=0.1)
            peito = c7.number_input("Peito (cm)", 0.0, step=0.1)
            braco = c8.number_input("Braço (cm)", 0.0, step=0.1)
            coxa = c9.number_input("Coxa (cm)", 0.0, step=0.1)
            if st.form_submit_button("Adicionar medida"):
                var = float(peso_in - dfe_final[config.COL_PESO].iloc[-1]) if not dfe_final.empty else 0.0
                nova_medida = pd.DataFrame([{"semana": len(dfe_final) + 1, "data": data_med.strftime("%d/%m/%Y"), "peso": peso_in, "var": var, "gordura_corporal": gord_corp, "gordura_visceral": gord_visc, "musculos_esqueleticos": musc_esq, "cintura": cintura, "peito": peito, "braco": braco, "coxa": coxa}])
                utils.adicionar_registro_df(nova_medida, path_evolucao)
                path_pessoais = utils.get_user_data_path(username, config.FILE_DADOS_PESSOAIS)
                dfp = utils.carregar_df(path_pessoais)
                if not dfp.empty:
                    dfp.loc[0, config.COL_PESO] = float(peso_in)
                    utils.salvar_df(dfp, path_pessoais)
                st.toast("Medida adicionada com sucesso!", icon="📏")
                st.rerun()

    if not dfe_final.empty:
        st.subheader("📊 Composição Corporal e Métricas")
        metricas = logic.calcular_metricas_saude(dados_pessoais, objetivo_info)
        st.info(f"Variação semanal estimada: **{metricas['var_semanal_kg']:+.2f} kg** ({metricas['var_semanal_percent']:+.2f}%) • Conclusão prevista: **{metricas['data_objetivo_fmt']}** ({metricas['dias_restantes']} dias restantes)")
        def classificar_imc(v):
            if v < 18.5: return "Abaixo do peso"
            if v <= 24.9: return "Peso normal"
            if v <= 29.9: return "Sobrepeso"
            return "Obesidade"
        sexo_atual = dados_pessoais.get('sexo', 'M')
        idade_atual = dados_pessoais.get('idade', 30)
        classificacoes = logic.classificar_composicao_corporal(dados_pessoais.get('gordura_corporal', 0), dados_pessoais.get('gordura_visceral', 0), dados_pessoais.get('massa_muscular', 0), sexo_atual, idade_atual)
        ranges_gordura = logic.obter_faixa_gordura_ideal(sexo_atual, idade_atual)
        ranges_visceral = (0, 9)
        ranges_musculo = {"M": (34, 39), "F": (24, 29)}.get(sexo_atual)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.info(f"IMC: **{metricas['IMC']:.1f}** — {classificar_imc(metricas['IMC'])}")
            plotting.plot_composition_range("Índice de Massa Corporal (IMC)", metricas['IMC'], (18.5, 24.9), (15, 40))
        with col2:
            st.info(f"Gordura corporal: **{dados_pessoais.get('gordura_corporal', 0):.1f}%** — {classificacoes['gordura']}")
            plotting.plot_composition_range("Gordura Corporal (%)", dados_pessoais.get('gordura_corporal', 0), ranges_gordura, (0, 50))
        with col3:
            st.info(f"Gordura visceral: **{dados_pessoais.get('gordura_visceral', 0):.1f}** — {classificacoes['visceral']}")
            plotting.plot_composition_range("Gordura Visceral (%)", dados_pessoais.get('gordura_visceral', 0), ranges_visceral, (0, 20))
        with col4:
            st.info(f"Massa muscular: **{dados_pessoais.get('massa_muscular', 0):.1f}%** — {classificacoes['musculo']}")
            plotting.plot_composition_range("Massa Muscular (%)", dados_pessoais.get('massa_muscular', 0), ranges_musculo, (15, 60))
        
        st.subheader("📈 Evolução de medidas")
        cols_to_clean = ['gordura_corporal', 'gordura_visceral', 'musculos_esqueleticos', 'cintura', 'peito', 'braco', 'coxa']
        dfe_plot = dfe_final.copy()
        for col in cols_to_clean:
            if col in dfe_plot.columns:
                dfe_plot[col] = dfe_plot[col].replace(0, np.nan)
        dfe_plot['data_dt'] = pd.to_datetime(dfe_plot[config.COL_DATA], format="%d/%m/%Y")
        dfe_plot = dfe_plot.sort_values('data_dt')
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=dfe_plot['data_dt'], y=dfe_plot[config.COL_PESO], mode='lines+markers', name='Peso (kg)'))
        fig1.add_trace(go.Scatter(x=dfe_plot['data_dt'], y=dfe_plot['gordura_corporal'], mode='lines+markers', name='Gordura Corporal (%)', yaxis="y2"))
        fig1.add_trace(go.Scatter(x=dfe_plot['data_dt'], y=dfe_plot['musculos_esqueleticos'], mode='lines+markers', name='Massa Muscular (%)', yaxis="y2"))
        fig1.update_layout(title="Evolução da Composição Corporal", xaxis_title="Data", yaxis_title="Peso (kg)", yaxis2=dict(title="Percentual (%)", overlaying="y", side="right"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig1, use_container_width=True)
        fig2 = go.Figure()
        medidas = ["cintura", "peito", "braco", "coxa"]
        for medida in medidas:
            if medida in dfe_plot.columns:
                fig2.add_trace(go.Scatter(x=dfe_plot['data_dt'], y=dfe_plot[medida], mode='lines+markers', name=f'{medida.capitalize()} (cm)'))
        if fig2.data:
            fig2.update_layout(title="Evolução das Medidas Corporais (cm)", xaxis_title="Data", yaxis_title="Medida (cm)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig2, use_container_width=True)
            
        with st.expander("Histórico de medições (clique para editar/apagar)", expanded=False):
            dfe_editado = st.data_editor(dfe_final.sort_values("semana", ascending=False), num_rows="dynamic", use_container_width=True, hide_index=True, key="editor_evolucao")
            if st.button("💾 Salvar Alterações no Histórico", key="salvar_historico_evolucao"):
                df_para_salvar = dfe_editado.sort_values("semana", ascending=True)
                utils.salvar_df(df_para_salvar, path_evolucao)
                st.toast("Histórico de evolução atualizado!", icon="✅")
                st.rerun()
    else:
        st.info("Adicione sua primeira medida para começar a ver a evolução.")
