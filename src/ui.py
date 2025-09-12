# ==============================================================================
# PLANO FIT APP - COMPONENTES DE UI
# ==============================================================================
# Este arquivo é responsável por toda a renderização da interface do usuário (UI).
# Cada função `render_*` constrói uma parte específica da tela, como a tela de
# login ou uma das abas da aplicação.
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
# ARMAZENAMENTO DE CACHE DA PÁGINA
# ==============================================================================

@st.cache_data
def _get_cached_meal_analysis(df_refeicoes, _tabela_alim):
    """
    Executa os cálculos pesados para a aba de alimentação e armazena o resultado em cache.
    """
    # 1. Cálculo dos totais diários
    total = {config.COL_ENERGIA: 0.0, config.COL_PROTEINA: 0.0, config.COL_CARBOIDRATO: 0.0, config.COL_LIPIDEOS: 0.0, config.COL_SODIO: 0.0}
    alimentos_nao_encontrados = []
    if not df_refeicoes.empty and not _tabela_alim.empty:
        for _, row in df_refeicoes.iterrows():
            alimento, qtd = str(row.get("Alimento", "")), float(row.get("Quantidade", 0.0) or 0.0)
            if not alimento or qtd <= 0: continue
            
            proc = utils.normalizar_texto(alimento)
            linha = _tabela_alim[_tabela_alim[config.COL_ALIMENTO_PROC].str.contains(proc, na=False)]
            
            if not linha.empty:
                fator = qtd / 100.0
                for col in total.keys():
                    if col in linha.columns:
                        valor = utils.limpar_valor_numerico(linha.iloc[0][col])
                        total[col] += valor * fator
            else:
                alimentos_nao_encontrados.append(alimento)

    # 2. Análise da distribuição por refeição
    df_distribuicao = logic.analisar_distribuicao_refeicoes(df_refeicoes, _tabela_alim)

    return total, alimentos_nao_encontrados, df_distribuicao

@st.cache_data
def _get_cached_evolution_charts(_dfe_final, _dados_pessoais, _objetivo_info):
    """
    Gera as figuras dos gráficos para a aba de evolução e armazena em cache.
    """
    if _dfe_final.empty:
        return None, None

    # Gráfico 1: Composição Corporal
    cols_to_clean = ['gordura_corporal', 'gordura_visceral', 'musculos_esqueleticos', 'cintura', 'peito', 'braco', 'coxa']
    dfe_plot = _dfe_final.copy()
    for col in cols_to_clean:
        if col in dfe_plot.columns:
            dfe_plot[col] = dfe_plot[col].replace(0, np.nan)
    
    date_col = config.COL_DATA if config.COL_DATA in dfe_plot.columns else 'data'
    dfe_plot['data_dt'] = pd.to_datetime(dfe_plot[date_col], format="%d/%m/%Y")
    dfe_plot = dfe_plot.sort_values('data_dt')
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=dfe_plot['data_dt'], y=dfe_plot[config.COL_PESO], mode='lines+markers', name='Peso (kg)'))
    fig1.add_trace(go.Scatter(x=dfe_plot['data_dt'], y=dfe_plot['gordura_corporal'], mode='lines+markers', name='Gordura Corporal (%)', yaxis="y2"))
    fig1.add_trace(go.Scatter(x=dfe_plot['data_dt'], y=dfe_plot['musculos_esqueleticos'], mode='lines+markers', name='Massa Muscular (%)', yaxis="y2"))
    fig1.update_layout(title="Evolução da Composição Corporal", xaxis_title="Data", yaxis_title="Peso (kg)", yaxis2=dict(title="Percentual (%)", overlaying="y", side="right"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

    # Gráfico 2: Medidas Corporais
    fig2 = go.Figure()
    medidas = ["cintura", "peito", "braco", "coxa"]
    for medida in medidas:
        if medida in dfe_plot.columns:
            fig2.add_trace(go.Scatter(x=dfe_plot['data_dt'], y=dfe_plot[medida], mode='lines+markers', name=f'{medida.capitalize()} (cm)'))
    
    if fig2.data:
        fig2.update_layout(title="Evolução das Medidas Corporais (cm)", xaxis_title="Data", yaxis_title="Medida (cm)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    else:
        fig2 = None
        
    return fig1, fig2

# ==============================================================================
# TELAS DE LOGIN / PERFIL
# ==============================================================================

def render_login_screen():
    """
    Renderiza a tela principal de login, que permite ao usuário logar,
    navegar para a criação de perfil ou para a redefinição de senha.
    Usa o st.session_state para controlar qual formulário é exibido.
    """
    # Simula o layout "centered" usando colunas
    _, col_center, _ = st.columns([1, 1.5, 1])

    with col_center:
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
                
                # >>>>>>>> ALTERAÇÃO AQUI <<<<<<<<<<
                # A linha 'st.session_state.new_user_redirect = True' foi removida.
                
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

    # --- MODIFICAÇÃO: Usa a nova função para obter os dados mais recentes e válidos ---
    dados_atuais = logic.get_latest_metrics(dados_pessoais, dfe_final)

    if not dfe_final.empty and objetivo_info:
        st.subheader("🏁 Progresso do Objetivo")
        
        metricas_evol = logic.calcular_metricas_saude(dados_atuais, objetivo_info)
        
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
                st.caption(f"Início: {dt_inicio.strftime('%d/%m/%Y')} | Conclusão Prevista: {dt_fim.strftime('%d/%m/%Y')} ({dias_passados}/{total_dias} dias)", help='Atualize sua evolução para recalcular a **data de conclusão**¹. \n\n ¹A quantidade de dias finais é acrescida todos os dias (só há progresso quando ocorre algum registro).')
        except (ValueError, TypeError):
            st.caption("Timeline indisponível. Verifique as datas do objetivo.")
    st.markdown("---")

    st.subheader("🍎 Metas Alimentares")
    if objetivo_info and not RECOMEND.empty:
        metricas = logic.calcular_metricas_saude(dados_atuais, objetivo_info)
        
        def obter_recomendacao_diaria(sexo, objetivo, intensidade):
            # CORREÇÃO: Adicionado .str.strip() para remover espaços em branco
            # que podem existir no arquivo CSV e quebrar a lógica de filtro.
            sexo_clean = sexo.strip().lower()
            objetivo_clean = objetivo.strip().lower()
            intensidade_clean = intensidade.strip().lower()
            
            filt = RECOMEND[
                (RECOMEND["Sexo"].str.strip().str.lower() == sexo_clean) &
                (RECOMEND["Objetivo"].str.strip().str.lower() == objetivo_clean) &
                (RECOMEND["Atividade"].str.strip().str.lower() == intensidade_clean)
            ]
            return filt.iloc[0] if not filt.empty else None
        
        rec = obter_recomendacao_diaria(dados_atuais.get('sexo'), objetivo_info.get('ObjetivoPeso'), objetivo_info.get('Atividade'))
        
        if rec is not None:
            peso = dados_atuais.get(config.COL_PESO, 70.0)
            
            prot_obj = float(rec[config.COL_REC_PROTEINA]) * peso
            carb_obj = float(rec[config.COL_REC_CARBOIDRATO]) * peso
            gord_obj = float(rec[config.COL_REC_GORDURA]) * peso
            sod_obj = float(rec[config.COL_REC_SODIO])
            
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Calorias", f"{metricas.get('alvo_calorico', 0):.0f} kcal")
            c2.metric("Proteínas", f"{prot_obj:.1f} g")
            c3.metric("Carboidratos", f"{carb_obj:.1f} g")
            c4.metric("Gorduras", f"{gord_obj:.1f} g")
            c5.metric("Sódio", f"{sod_obj:.0f} mg")
            c6.metric("Água", f"{metricas.get('meta_agua_l', 0):.2f} L")
        else:
            st.warning("Não foi possível encontrar uma recomendação de macronutrientes para a combinação de sexo, objetivo e nível de atividade definidos na aba 'Objetivos'.")

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
                foco_principal_text = str(meso.get('foco_principal', ''))
                words = foco_principal_text.split(' ')
                lines = []
                current_line = ""
                wrap_width = 60
                for word in words:
                    if len(current_line) + len(word) + 1 > wrap_width:
                        lines.append(current_line)
                        current_line = word
                    else:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                lines.append(current_line)
                wrapped_text = "<br>".join(lines)
                gantt_data.append(dict(Task=meso['nome'], Start=start_date.strftime('%Y-%m-%d'), Finish=end_date.strftime('%Y-%m-%d'), Resource=wrapped_text))
                start_date = end_date
                
            if gantt_data:
                fig = ff.create_gantt(gantt_data, index_col='Resource', show_colorbar=True, group_tasks=True, title='Fases do Treino (Mesociclos)')
                fig.add_vline(x=today, line_width=3, line_dash="dash", line_color="red", name="Hoje")
                st.plotly_chart(fig, width="stretch")
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
    if not dft_log.empty and 'Data' in dft_log.columns and 'Calorias Gastas' in dft_log.columns:
        dft_heat = dft_log.copy()
        dft_heat['date'] = pd.to_datetime(dft_heat[config.COL_DATA], format="%d/%m/%Y")
        today_ts = pd.Timestamp.now().normalize()
        start_date = pd.Timestamp(date(today_ts.year, 1, 1))
        daily_activity = dft_heat.groupby(dft_heat['date'].dt.date)['Calorias Gastas'].sum()
        all_days = pd.date_range(start=start_date, end=today_ts, freq='D')
        activity_values = all_days.to_series(index=all_days, name='Calorias Gastas').dt.date.map(daily_activity).fillna(0)
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
        st.plotly_chart(fig, width="stretch", key="heatmap_geral")
    else:
        st.info("Registre seu primeiro treino na aba 'Treino' para começar a visualizar seu heatmap de atividades.")

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
        
        default_nascimento = date.today() - timedelta(days=365*30)
        nascimento_str = dados_pessoais.get("nascimento", "")
        if nascimento_str:
            try:
                default_nascimento = datetime.strptime(nascimento_str, "%d/%m/%Y").date()
            except (ValueError, TypeError):
                pass

        with st.form("form_pessoais"):
            c1, c2, c3, c4 = st.columns(4)
            nome = c1.text_input("Nome", value=dados_pessoais.get("nome", ""))
            
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
            
            submitted = st.form_submit_button("Salvar dados pessoais")
            
            if submitted:
                nascimento_str_para_salvar = nascimento_obj.strftime("%d/%m/%Y")
                hoje = date.today()
                idade = hoje.year - nascimento_obj.year - ((hoje.month, hoje.day) < (nascimento_obj.month, nascimento_obj.day))
                
                df_novo = pd.DataFrame([{"nome": nome, "nascimento": nascimento_str_para_salvar, "altura": altura, "sexo": sexo, "peso": peso, "idade": idade, "gordura_corporal": gord_corp, "gordura_visceral": gord_visc, "massa_muscular": musculo}])
                utils.salvar_df(df_novo, utils.get_user_data_path(username, config.FILE_DADOS_PESSOAIS))
                
                if dfe_evol.empty:
                    primeira_medida = pd.DataFrame([{"semana": 1, "data": date.today().strftime("%d/%m/%Y"), "peso": peso, "var": 0.0, "gordura_corporal": gord_corp, "gordura_visceral": gord_visc, "musculos_esqueleticos": musculo, "cintura": 0, "peito": 0, "braco": 0, "coxa": 0}])
                    utils.salvar_df(primeira_medida, utils.get_user_data_path(username, config.FILE_EVOLUCAO))

                st.toast("Dados pessoais salvos!", icon="📋")
                
                # >>>>>>>> ALTERAÇÃO AQUI <<<<<<<<<<
                # A linha 'st.session_state.new_user_redirect = True' foi removida.
                
                st.rerun()

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
            st.warning("⚠️Atenção: A alteração destes dados pode afetar todos os cálculos futuros.")
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
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            
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
            fator_dieta = c6.slider(label='Intensidade da dieta', min_value=0.5, max_value=1.5, step=0.05, value=float(objetivo_info.get("FatorDieta", 1.0)), help="Agressividade da dieta (influencia no **Alvo calórico** para **perda** e **ganho**).")
            submitted = st.form_submit_button("Salvar objetivo")

        if submitted:
            # ALTERADO: Salva a data formatada como string
            df_obj_novo = pd.DataFrame([{"DataInicio": inicio_objetivo_obj.strftime("%d/%m/%Y"), "Atividade": intensidade, "Ambiente": ambiente, "ObjetivoPeso": objetivo, "PesoAlvo": peso_alvo, "FatorDieta": fator_dieta}])
            utils.salvar_df(df_obj_novo, utils.get_user_data_path(st.session_state.current_user, config.FILE_OBJETIVO))
            st.toast("Objetivo salvo!", icon="🎯")
            st.rerun()

        # ALTERADO: Constrói o dicionário de informações com a data correta
        objetivo_info = {"DataInicio": inicio_objetivo_obj.strftime("%d/%m/%Y"), "Atividade": intensidade, "Ambiente": ambiente, "ObjetivoPeso": objetivo, "PesoAlvo": peso_alvo, "FatorDieta": fator_dieta}
        metricas = logic.calcular_metricas_saude(dados_pessoais, objetivo_info)
        
        st.subheader("🔥 Alvo Calórico")
        plotting.plot_energy_composition(metricas['TMB'], metricas['TDEE'], metricas['alvo_calorico'])
    else:
        st.error("Preencha e salve seus dados pessoais na primeira aba.")

def render_alimentacao_tab(user_data: Dict[str, Any], TABELA_ALIM: pd.DataFrame, RECOMEND: pd.DataFrame):
    """
    Renderiza a aba de Alimentação, agora com sub-abas para Planejamento e Cadastro.
    """
    sub_tab_plan, sub_tab_cadastro = st.tabs([
        "📅 Planejamento Alimentar", "✍️ Cadastro de Alimentos"
    ])

    with sub_tab_plan:
        # A lógica antiga da aba foi movida para esta nova função
        render_planejamento_alimentar_sub_tab(user_data, TABELA_ALIM, RECOMEND)
    
    with sub_tab_cadastro:
        # A nova funcionalidade de edição da tabela de alimentos fica aqui
        render_cadastro_alimentos_sub_tab(TABELA_ALIM)

def render_planejamento_alimentar_sub_tab(user_data: Dict[str, Any], TABELA_ALIM: pd.DataFrame, RECOMEND: pd.DataFrame):
    """
    Renderiza a sub-aba de Planejamento Alimentar, com o registro diário e
    gerenciamento de planos.
    """
    # Garante que a seleção do plano alimentar seja mantida após um rerun.
    if "_preserve_plan_selection_on_rerun" in st.session_state:
        st.session_state.sb_planos_alim = st.session_state._preserve_plan_selection_on_rerun
        del st.session_state._preserve_plan_selection_on_rerun
    
    if "_preserve_assistant_state" in st.session_state:
        assistant_state = st.session_state._preserve_assistant_state
        st.session_state.alvo_adicao_radio = assistant_state.get("alvo")
        st.session_state.refeicao_assistente_select = assistant_state.get("refeicao")
        st.session_state.busca_alimento_input = assistant_state.get("busca")
        del st.session_state._preserve_assistant_state

    username = st.session_state.current_user
    dados_pessoais = user_data.get("dados_pessoais", {})

    path_refeicoes = utils.get_user_data_path(username, config.FILE_REFEICOES)
    df_refeicoes = user_data.get("df_refeicoes", pd.DataFrame())
    path_planos = utils.get_user_data_path(username, config.FILE_PLANOS_ALIMENTARES)
    df_planos_alimentares = user_data.get("df_planos_alimentares", pd.DataFrame())

    col_refeicoes, col_assistente = st.columns([0.6, 0.4])

    with col_refeicoes:
        st.subheader("🔢 Totais Calculados",help='Total de calorias com base no objetivo. Demais macronutrientes com base no banco de dados de recomendações.')
        
        total, alimentos_nao_encontrados, df_distribuicao = _get_cached_meal_analysis(df_refeicoes, TABELA_ALIM)
        
        if alimentos_nao_encontrados:
            st.warning(f"Alimentos não encontrados na base: {', '.join(set(alimentos_nao_encontrados))}")
        
        df_obj = user_data.get("df_objetivo", pd.DataFrame())
        objetivo_info_alim = df_obj.iloc[0].to_dict() if not df_obj.empty else {}
        
        if not objetivo_info_alim or RECOMEND.empty:
            st.warning("Defina seus objetivos e carregue as recomendações para visualizar o progresso em relação às metas.")
        else:
            metricas_alim = logic.calcular_metricas_saude(dados_pessoais, objetivo_info_alim)
            alvo_calorico = metricas_alim.get('alvo_calorico', 1)
            
            def obter_recomendacao_diaria(sexo, objetivo, intensidade):
                filt = RECOMEND[(RECOMEND["Sexo"].str.lower() == sexo.lower()) & (RECOMEND["Objetivo"].str.lower() == objetivo.lower()) & (RECOMEND["Atividade"].str.lower() == intensidade.lower())]
                return filt.iloc[0] if not filt.empty else None
            
            rec = obter_recomendacao_diaria(dados_pessoais.get('sexo'), objetivo_info_alim.get('ObjetivoPeso'), objetivo_info_alim.get('Atividade'))
            
            if rec is not None:
                peso = dados_pessoais.get(config.COL_PESO, 70.0)
                prot_obj, carb_obj, gord_obj, sod_obj = float(rec[config.COL_REC_PROTEINA]) * peso, float(rec[config.COL_REC_CARBOIDRATO]) * peso, float(rec[config.COL_REC_GORDURA]) * peso, float(rec[config.COL_REC_SODIO])
                
                macros = {
                    "Calorias": (total.get(config.COL_ENERGIA, 0), alvo_calorico, "kcal"),
                    "Proteína": (total.get(config.COL_PROTEINA, 0), prot_obj, "g"),
                    "Carboidrato": (total.get(config.COL_CARBOIDRATO, 0), carb_obj, "g"),
                    "Gorduras": (total.get(config.COL_LIPIDEOS, 0), gord_obj, "g"),
                    "Sódio": (total.get(config.COL_SODIO, 0), sod_obj, "mg")
                }
                cols = st.columns(len(macros))
                for i, (nome, (valor, meta, unidade)) in enumerate(macros.items()):
                    with cols[i]:
                        st.markdown(f"**{nome}**")
                        st.markdown(f"<font size='2' color='grey'>{valor:.0f} / {meta:.0f} {unidade}</font>", unsafe_allow_html=True)
                        percentual = (valor / meta) if meta > 0 else 0
                        # CORREÇÃO: Garante que o valor passado para st.progress não seja NaN
                        if pd.isna(percentual):
                            percentual = 0.0
                        st.progress(min(percentual, 1.0))
            else:
                st.warning("Não foi possível encontrar uma recomendação de macronutrientes para a combinação de sexo, objetivo e nível de atividade definidos na aba 'Objetivos'.")

        st.markdown("---")

        st.subheader("📊 Análise das Refeições")
        
        if not df_distribuicao.empty:
            metricas_opcoes = {
                "Calorias (kcal)": config.COL_ENERGIA,
                "Proteínas (g)": config.COL_PROTEINA,
                "Carboidratos (g)": config.COL_CARBOIDRATO,
                "Gorduras (g)": config.COL_LIPIDEOS
            }
            metrica_selecionada_label = st.selectbox(
                "Selecione o nutriente para visualizar a distribuição:",
                options=list(metricas_opcoes.keys())
            )
            coluna_selecionada = metricas_opcoes[metrica_selecionada_label]

            from plotly.subplots import make_subplots
            fig = make_subplots(
                rows=1, cols=2,
                specs=[[{'type':'domain'}, {'type':'domain'}]],
                subplot_titles=(f'Distribuição de {metrica_selecionada_label}', 'Distribuição de Peso (g)')
            )
            fig.add_trace(go.Pie(
                labels=df_distribuicao.index,
                values=df_distribuicao[coluna_selecionada],
                name=metrica_selecionada_label,
                hole=.4,
                hovertemplate='<b>%{label}</b><br>%{value:,.1f} (' + coluna_selecionada.split('(')[-1] + '<br>%{percent}<extra></extra>'
            ), 1, 1)
            fig.add_trace(go.Pie(
                labels=df_distribuicao.index,
                values=df_distribuicao.get('Quantidade', pd.Series(dtype='float64')),
                name='Peso (g)',
                hole=.4,
                hovertemplate='<b>%{label}</b><br>%{value:,.0f}g<br>%{percent}<extra></extra>'
            ), 1, 2)
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                textfont_size=14
            )
            fig.update_layout(
                height=400,
                margin=dict(t=50, b=20, l=20, r=20),
                plot_bgcolor='rgba(0,0,0,0)',
                legend_traceorder="reversed"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Adicione refeições para visualizar a análise gráfica.")

        st.subheader("Refeições do Dia")
        
        if not df_refeicoes.empty:
            sequencia_refeicao = config.OPCOES_REFEICOES
            if "Refeicao" in df_refeicoes.columns:
                df_refeicoes['Refeicao'] = pd.Categorical(df_refeicoes['Refeicao'], categories=sequencia_refeicao, ordered=True)
                df_refeicoes = df_refeicoes.sort_values(by="Refeicao").reset_index(drop=True)

            edited_df = st.data_editor(
                df_refeicoes,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Refeicao": st.column_config.SelectboxColumn("Refeição", options=config.OPCOES_REFEICOES, required=True),
                    "Alimento": st.column_config.TextColumn("Alimento", required=True),
                    "Quantidade": st.column_config.NumberColumn("Quantidade (g)", min_value=0.0, step=1.0)
                },
                key="editor_refeicoes_dia"
            )

            if st.button("💾 Salvar Alterações Manuais", key="salvar_refeições"):
                if 'sb_planos_alim' in st.session_state:
                    st.session_state._preserve_plan_selection_on_rerun = st.session_state.sb_planos_alim
                
                st.session_state._preserve_assistant_state = {
                    "alvo": st.session_state.get("alvo_adicao_radio"),
                    "refeicao": st.session_state.get("refeicao_assistente_select"),
                    "busca": st.session_state.get("busca_alimento_input")
                }

                utils.salvar_df(edited_df, path_refeicoes)
                st.toast("Alterações salvas!", icon="🍽️")
                _get_cached_meal_analysis.clear()
                st.rerun()
        else:
            st.info("Nenhuma refeição registrada para hoje. Use o 'Assistente de Adição' ao lado para começar.")

    with col_assistente:
        st.subheader("✨ Assistente de Adição", help = 'Refeições de acordo com a tabela TACO - Tabela Brasileira de Composição de Alimentos')
        alvo_adicao = st.radio("Adicionar para:", ("Refeições do Dia", "Plano Alimentar"), horizontal=True, key="alvo_adicao_radio")
        
        plano_alvo_nome = None
        if alvo_adicao == "Plano Alimentar":
            lista_planos_existentes = df_planos_alimentares['nome_plano'].unique().tolist() if 'nome_plano' in df_planos_alimentares.columns else []
            if not lista_planos_existentes:
                st.info("Crie um plano no gerenciador abaixo para poder adicionar alimentos a ele.")
            else:
                plano_alvo_nome = st.selectbox("Selecione o Plano Alvo:", options=lista_planos_existentes)
        
        refeicao_escolhida = st.selectbox("Adicionar à Refeição:", options=config.OPCOES_REFEICOES, key="refeicao_assistente_select")
        termo_busca = st.text_input("Buscar Alimento:", key="busca_alimento_input")
        
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
                    if 'sb_planos_alim' in st.session_state:
                        st.session_state._preserve_plan_selection_on_rerun = st.session_state.sb_planos_alim
                    
                    if alvo_adicao == "Refeições do Dia":
                        nova_refeicao = pd.DataFrame([{"Refeicao": refeicao_escolhida, "Alimento": alimento_selecionado, "Quantidade": quantidade}])
                        utils.adicionar_registro_df(nova_refeicao, path_refeicoes)
                        st.toast(f"'{alimento_selecionado}' adicionado!", icon="👍")
                        _get_cached_meal_analysis.clear()
                        st.rerun()
                    elif alvo_adicao == "Plano Alimentar" and plano_alvo_nome:
                        novo_item_plano = pd.DataFrame([{'nome_plano': plano_alvo_nome, 'Refeicao': refeicao_escolhida, 'Alimento': alimento_selecionado, 'Quantidade': quantidade}])
                        utils.adicionar_registro_df(novo_item_plano, path_planos)
                        st.rerun()
            elif termo_busca:
                st.info("Nenhum alimento encontrado.")

    def handle_create_plan(new_plan_name, current_plans_list):
        if new_plan_name and new_plan_name not in current_plans_list:
            novo_plano_df = pd.DataFrame([{'nome_plano': new_plan_name, 'Refeicao': np.nan, 'Alimento': np.nan, 'Quantidade': np.nan}])
            utils.adicionar_registro_df(novo_plano_df, path_planos)
            st.toast(f"Plano '{new_plan_name}' criado!", icon="📅")
            return True
        else:
            st.session_state.form_error = "Nome de plano inválido ou já existente."
            return False

    def callback_create_and_select_plan():
        new_plan_name = st.session_state.get("new_plan_name_input", "")
        plan_list = df_planos_alimentares['nome_plano'].unique().tolist() if 'nome_plano' in df_planos_alimentares.columns else []
        
        if handle_create_plan(new_plan_name, plan_list):
            st.session_state.sb_planos_alim = new_plan_name
            if "new_plan_name_input" in st.session_state:
                del st.session_state["new_plan_name_input"]

    with st.expander("Gerenciar Meus Planos Alimentares", expanded=True):
        planos_df = user_data.get("df_planos_alimentares", pd.DataFrame())
        lista_planos = ["-- Criar Novo Plano --"] + sorted(planos_df['nome_plano'].unique().tolist()) if 'nome_plano' in planos_df.columns else ["-- Criar Novo Plano --"]
        
        plano_selecionado = st.selectbox(
            "Selecione um plano para editar ou crie um novo:", 
            options=lista_planos, 
            key="sb_planos_alim"
        )
        
        if plano_selecionado == "-- Criar Novo Plano --":
            st.text_input("Nome do Novo Plano Alimentar (ex: Dia de Treino Intenso)", key="new_plan_name_input")
            st.button("Criar Plano Alimentar", on_click=callback_create_and_select_plan)

            if 'form_error' in st.session_state and st.session_state.form_error:
                st.error(st.session_state.form_error)
                del st.session_state.form_error
        
        elif plano_selecionado != "-- Criar Novo Plano --":
            st.markdown(f"**Editando o plano: {plano_selecionado}**")
            
            itens_plano = planos_df[planos_df['nome_plano'] == plano_selecionado].copy()
            
            itens_plano.dropna(subset=['Alimento'], inplace=True)

            if 'Alimento' in itens_plano.columns:
                itens_plano['Alimento'] = itens_plano['Alimento'].astype(object)
            if 'Refeicao' in itens_plano.columns:
                itens_plano['Refeicao'] = itens_plano['Refeicao'].astype(object)

            if not itens_plano.empty and "Refeicao" in itens_plano.columns:
                itens_plano = itens_plano.sort_values(by="Refeicao")

            itens_plano.reset_index(drop=True, inplace=True)
            
            itens_editados = st.data_editor(
                itens_plano, 
                num_rows="dynamic", 
                use_container_width=True, 
                key=f"editor_plano_{plano_selecionado}",
                column_config={
                    "nome_plano": None,
                    "Refeicao": st.column_config.SelectboxColumn("Refeição", options=config.OPCOES_REFEICOES, required=True),
                    "Alimento": st.column_config.TextColumn("Alimento", required=True),
                    "Quantidade": st.column_config.NumberColumn("Quantidade (g)", min_value=0.0, step=1.0)
                }
            )
            c1, c2, c3 = st.columns([1, 1, 1.2])
            if c1.button("💾 Salvar Alterações no Plano", key=f"save_{plano_selecionado}"):
                df_outros_planos = planos_df[planos_df['nome_plano'] != plano_selecionado]
                df_final = pd.concat([df_outros_planos, itens_editados], ignore_index=True)
                utils.salvar_df(df_final, path_planos)
                st.toast(f"Plano '{plano_selecionado}' salvo!", icon="💾")
                st.rerun()
            if c2.button("🚀 Carregar para Hoje", key=f"load_{plano_selecionado}"):
                itens_para_carregar = itens_editados.drop(columns=['nome_plano'], errors='ignore')
                utils.salvar_df(itens_para_carregar, path_refeicoes)
                st.toast(f"Plano '{plano_selecionado}' carregado para hoje.", icon="🚀")
                _get_cached_meal_analysis.clear()
                st.rerun()

            delete_key = f"confirm_delete_plano_alim_{plano_selecionado}"

            if c3.button(f"🗑️ Apagar Plano", type="secondary", key=f"delete_btn_{plano_selecionado}"):
                st.session_state[delete_key] = True

            if st.session_state.get(delete_key, False):
                st.warning(f"Tem certeza que deseja apagar o plano '{plano_selecionado}'? Esta ação não pode ser desfeita.")
                col_conf1, col_conf2, _ = st.columns([1, 1, 3])
                with col_conf1:
                    if st.button("Sim, apagar", type="primary", key=f"confirm_delete_yes_{plano_selecionado}"):
                        planos_df = planos_df[planos_df['nome_plano'] != plano_selecionado]
                        utils.salvar_df(planos_df, path_planos)
                        st.toast(f"Plano '{plano_selecionado}' apagado.", icon="🗑️")
                        if 'sb_planos_alim' in st.session_state:
                            del st.session_state.sb_planos_alim
                        st.session_state[delete_key] = False
                        st.rerun()
                with col_conf2:
                    if st.button("Cancelar", key=f"confirm_delete_no_{plano_selecionado}"):
                        st.session_state[delete_key] = False
                        st.rerun()

def render_cadastro_alimentos_sub_tab(TABELA_ALIM: pd.DataFrame):
    """
    Renderiza a sub-aba para cadastro e edição de alimentos na tabela geral.
    """
    # --- Formulário para Adição Rápida ---
    with st.expander("Adicionar Novo Alimento"):
        with st.form(key="form_novo_alimento", clear_on_submit=True):
            st.write("**Informações Gerais**")
            
            # >>>>>>>> CORREÇÃO AQUI <<<<<<<<<<
            # Extrai os grupos únicos existentes, remove valores nulos, ordena e adiciona "Outros".
            grupos_existentes = sorted(TABELA_ALIM['Grupo'].dropna().unique().tolist())
            opcoes_grupo = grupos_existentes + ["Outros"]

            c1, c2 = st.columns(2)
            alimento_nome = c1.text_input("Nome do Alimento")
            alimento_grupo = c2.selectbox("Grupo", options=opcoes_grupo, index=len(opcoes_grupo)-1) # Padrão para "Outros"

            st.write("**Macronutrientes e Fibras (valores por 100g)**")
            c3, c4, c5, c6, c7 = st.columns(5)
            energia_kcal = c3.number_input("Energia (kcal)", value=0.0, format="%.2f")
            proteina_g = c4.number_input("Proteína (g)", value=0.0, format="%.2f")
            carboidrato_g = c5.number_input("Carboidrato (g)", value=0.0, format="%.2f")
            lipideos_g = c6.number_input("Lipídeos (g)", value=0.0, format="%.2f")
            fibra_g = c7.number_input("Fibra (g)", value=0.0, format="%.2f")

            st.write("**Minerais Selecionados (valores por 100g)**")
            c8, c9, c10, c11 = st.columns(4)
            calcio_mg = c8.number_input("Cálcio (mg)", value=0.0, format="%.2f")
            magnesio_mg = c9.number_input("Magnésio (mg)", value=0.0, format="%.2f")
            ferro_mg = c10.number_input("Ferro (mg)", value=0.0, format="%.2f")
            sodio_mg = c11.number_input("Sódio (mg)", value=0.0, format="%.2f")

            submitted = st.form_submit_button("Adicionar Alimento à Tabela")

            if submitted:
                if not alimento_nome:
                    st.warning("O nome do alimento é obrigatório.")
                else:
                    new_row_data = {col: 0.0 for col in TABELA_ALIM.columns if col not in ['ID', 'Grupo', 'Alimento', config.COL_ALIMENTO_PROC]}
                    
                    new_row_data['ID'] = TABELA_ALIM['ID'].max() + 1 if not TABELA_ALIM.empty else 1
                    new_row_data['Grupo'] = alimento_grupo
                    new_row_data['Alimento'] = utils.limpar_texto_bruto(alimento_nome)
                    new_row_data[config.COL_ALIMENTO_PROC] = utils.normalizar_texto(alimento_nome)
                    new_row_data['Energia(kcal)'] = energia_kcal
                    new_row_data['Proteina(g)'] = proteina_g
                    new_row_data['Carboidrato(g)'] = carboidrato_g
                    new_row_data['Lipideos(g)'] = lipideos_g
                    new_row_data['Fibra Alimentar(g)'] = fibra_g
                    new_row_data['Calcio(mg)'] = calcio_mg
                    new_row_data['Magnesio(mg)'] = magnesio_mg
                    new_row_data['Ferro(mg)'] = ferro_mg
                    new_row_data['Sodio(mg)'] = sodio_mg
                    
                    novo_alimento_df = pd.DataFrame([new_row_data])
                    utils.adicionar_registro_df(novo_alimento_df, config.PATH_TABELA_ALIM)
                    
                    utils.carregar_tabela_alimentacao.clear()
                    st.toast(f"Alimento '{alimento_nome}' adicionado com sucesso!")
                    st.rerun()

    st.subheader("Tabela Completa")
    
    tabela_para_editar = TABELA_ALIM.copy()
    
    tabela_para_editar.reset_index(drop=True, inplace=True)

    tabela_editada = st.data_editor(
        tabela_para_editar,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_tabela_alimentos",
        column_config={
            "Alimento_proc": None,
            "ID": st.column_config.NumberColumn("ID", disabled=True),
            "Alimento": st.column_config.TextColumn("Alimento", required=True, width="large"),
            "Grupo": st.column_config.TextColumn("Grupo"),
            "Umidade(%)": st.column_config.NumberColumn("Umidade (%)", format="%.2f"),
            "Energia(kcal)": st.column_config.NumberColumn("Energia (kcal)", format="%.2f"),
            "Energia(kJ)": st.column_config.NumberColumn("Energia (kJ)", format="%.2f"),
            "Proteina(g)": st.column_config.NumberColumn("Proteína (g)", format="%.2f"),
            "Lipideos(g)": st.column_config.NumberColumn("Lipídeos (g)", format="%.2f"),
            "Colesterol(mg)": st.column_config.NumberColumn("Colesterol (mg)", format="%.2f"),
            "Carboidrato(g)": st.column_config.NumberColumn("Carboidrato (g)", format="%.2f"),
            "Fibra Alimentar(g)": st.column_config.NumberColumn("Fibra (g)", format="%.2f"),
            "Cinzas(g)": st.column_config.NumberColumn("Cinzas (g)", format="%.2f"),
            "Calcio(mg)": st.column_config.NumberColumn("Cálcio (mg)", format="%.2f"),
            "Magnesio(mg)": st.column_config.NumberColumn("Magnésio (mg)", format="%.2f"),
            "Manganes(mg)": st.column_config.NumberColumn("Manganês (mg)", format="%.2f"),
            "Fosforo(mg)": st.column_config.NumberColumn("Fósforo (mg)", format="%.2f"),
            "Ferro(mg)": st.column_config.NumberColumn("Ferro (mg)", format="%.2f"),
            "Sodio(mg)": st.column_config.NumberColumn("Sódio (mg)", format="%.2f"),
            "Potassio(mg)": st.column_config.NumberColumn("Potássio (mg)", format="%.2f"),
            "Cobre(mg)": st.column_config.NumberColumn("Cobre (mg)", format="%.2f"),
            "Zinco(mg)": st.column_config.NumberColumn("Zinco (mg)", format="%.2f"),
            "Retinol(mcg)": st.column_config.NumberColumn("Retinol (mcg)", format="%.2f"),
            "RE(mcg)": st.column_config.NumberColumn("RE (mcg)", format="%.2f"),
            "RAE(mcg)": st.column_config.NumberColumn("RAE (mcg)", format="%.2f"),
            "Tiamina(mg)": st.column_config.NumberColumn("Tiamina (mg)", format="%.2f"),
            "Riboflavina(mg)": st.column_config.NumberColumn("Riboflavina (mg)", format="%.2f"),
            "Piridoxina(mg)": st.column_config.NumberColumn("Piridoxina (mg)", format="%.2f"),
            "Niacina(mg)": st.column_config.NumberColumn("Niacina (mg)", format="%.2f"),
            "VitaminaC(mg)": st.column_config.NumberColumn("Vitamina C (mg)", format="%.2f"),
        }
    )

    if st.button("💾 Salvar Alterações na Tabela de Alimentos"):
        df_para_salvar = tabela_editada.copy()
        
        if config.COL_ALIMENTO in df_para_salvar.columns:
            df_para_salvar[config.COL_ALIMENTO] = df_para_salvar[config.COL_ALIMENTO].apply(utils.limpar_texto_bruto)
            df_para_salvar[config.COL_ALIMENTO_PROC] = df_para_salvar[config.COL_ALIMENTO].apply(utils.normalizar_texto)

        utils.salvar_df(df_para_salvar, config.PATH_TABELA_ALIM)
        
        utils.carregar_tabela_alimentacao.clear()
        
        st.toast("Tabela de alimentos atualizada com sucesso!", icon="✅")
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
        
        sub_tab_reg, sub_tab_plan = st.tabs([
            "💪 Registrar Treino", "🛠️ Planejamento Completo"
        ])

        with sub_tab_reg:
            render_registro_sub_tab(username, user_data)
        with sub_tab_plan:
            render_planejamento_sub_tab(username, user_data)

    else:
        st.error("Preencha e salve seus dados pessoais na primeira aba.")


def render_planejamento_sub_tab(username: str, user_data: Dict[str, Any]):
    """
    Renderiza a sub-aba de planejamento, com a adição do tipo de exercício.
    """
    # --- RESTAURAÇÃO MANUAL DE ESTADO PÓS-RERUN PROBLEMÁTICO ---
    if "_preserve_macro_selection_on_rerun" in st.session_state:
        st.session_state.macro_select_planning = st.session_state._preserve_macro_selection_on_rerun
        del st.session_state._preserve_macro_selection_on_rerun

    # --- FUNÇÕES DE CALLBACK PARA MANIPULAÇÃO DE ESTADO ---
    def callback_criar_plano():
        novo_nome_plano = st.session_state.get("novo_nome_plano_input", "")
        df_planos_treino = user_data.get("df_planos_treino", pd.DataFrame())
        path_planos_treino = utils.get_user_data_path(username, config.FILE_PLANOS_TREINO)

        if novo_nome_plano and ('nome_plano' not in df_planos_treino.columns or novo_nome_plano not in df_planos_treino['nome_plano'].tolist()):
            novo_id = df_planos_treino['id_plano'].max() + 1 if not df_planos_treino.empty else 1
            novo_plano_df = pd.DataFrame([{'id_plano': novo_id, 'nome_plano': novo_nome_plano}])
            df_planos_treino_atualizado = pd.concat([df_planos_treino, novo_plano_df], ignore_index=True)
            utils.salvar_df(df_planos_treino_atualizado, path_planos_treino)
            st.toast(f"Modelo '{novo_nome_plano}' criado!", icon="✅")
            st.session_state.sb_planos_unificado = novo_nome_plano
            st.session_state.novo_nome_plano_input = "" 
        else:
            st.error("Nome de modelo inválido ou já existente.")

    def callback_criar_macro():
        nome_macro = st.session_state.get("nome_macro_input", "")
        objetivo_macro = st.session_state.get("objetivo_macro_input", "")
        data_inicio = st.session_state.get("data_inicio_macro_input", date.today())
        data_fim = st.session_state.get("data_fim_macro_input", date.today())
        df_macro = user_data.get("df_macrociclos", pd.DataFrame())
        path_macro = utils.get_user_data_path(username, config.FILE_MACROCICLOS)

        if nome_macro and data_inicio < data_fim:
            max_id = df_macro['id_macrociclo'].max() if not df_macro.empty and 'id_macrociclo' in df_macro.columns else 0
            novo_macro = pd.DataFrame([{'id_macrociclo': max_id + 1, 'nome': nome_macro, 'objetivo_principal': objetivo_macro, 'data_inicio': data_inicio.strftime('%Y-%m-%d'), 'data_fim': data_fim.strftime('%Y-%m-%d')}])
            df_macro_atualizado = pd.concat([df_macro, novo_macro], ignore_index=True)
            utils.salvar_df(df_macro_atualizado, path_macro)
            st.toast("Macrociclo criado!", icon="✅")
            st.session_state.macro_select_planning = nome_macro
        else:
            st.error("Preencha o nome e garanta que a data de início seja anterior à data de fim.")

    st.subheader("Passo 1: Crie seus Treinos")

    # --- CARREGAMENTO DE DADOS ---
    df_planos_treino = user_data.get("df_planos_treino", pd.DataFrame())
    df_exercicios_todos = user_data.get("df_exercicios", pd.DataFrame())
    df_macro = user_data.get("df_macrociclos", pd.DataFrame())
    df_meso = user_data.get("df_mesociclos", pd.DataFrame())
    df_plano_sem = user_data.get("df_plano_semanal", pd.DataFrame())

    colunas_exercicios_necessarias = {
        'id_plano': pd.Series(dtype='int'), 'nome_exercicio': pd.Series(dtype='str'),
        'tipo_exercicio': pd.Series(dtype='str'), 'series_planejadas': pd.Series(dtype='int'),
        'repeticoes_planejadas': pd.Series(dtype='str'), 'ordem': pd.Series(dtype='int')
    }
    for col, dtype_series in colunas_exercicios_necessarias.items():
        if col not in df_exercicios_todos.columns:
            df_exercicios_todos[col] = dtype_series

    path_planos_treino = utils.get_user_data_path(username, config.FILE_PLANOS_TREINO)
    path_exercicios = utils.get_user_data_path(username, config.FILE_PLANOS_EXERCICIOS)
    path_macro = utils.get_user_data_path(username, config.FILE_MACROCICLOS)
    path_meso = utils.get_user_data_path(username, config.FILE_MESOCICLOS)
    path_plano_sem = utils.get_user_data_path(username, config.FILE_PLANO_SEMANAL)
    path_exercicios_db = config.ASSETS_DIR / "exercises" / "exercicios.json"
    exercisedb = utils.carregar_banco_exercicios(path_exercicios_db)

    with st.expander("Modelos de Treino", expanded=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            if 'id_plano' not in df_planos_treino.columns:
                df_planos_treino = pd.DataFrame(columns=['id_plano', 'nome_plano']).sort_values('nome_plano')
            df_planos_treino = df_planos_treino.sort_values('nome_plano')
            lista_planos = ["-- Criar Novo Plano --"] + df_planos_treino['nome_plano'].tolist()
            default_index_plano = 0
            if 'sb_planos_unificado' in st.session_state and st.session_state.sb_planos_unificado in lista_planos:
                default_index_plano = lista_planos.index(st.session_state.sb_planos_unificado)

            opcao_plano = st.selectbox(
                "Selecione para editar ou crie um novo:", 
                options=lista_planos, 
                key="sb_planos_unificado",
                index=default_index_plano
            )

            if opcao_plano == "-- Criar Novo Plano --":
                with st.form("form_novo_plano"):
                    st.text_input("Nome do Novo Modelo de Treino", key="novo_nome_plano_input")
                    st.form_submit_button("Criar Modelo", on_click=callback_criar_plano)

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
                        
                        if 'macro_select_planning' in st.session_state:
                            st.session_state._preserve_macro_selection_on_rerun = st.session_state.macro_select_planning
                        
                        del st.session_state.sb_planos_unificado
                        st.rerun()
                    if col_conf2.button("Cancelar"):
                        st.session_state[f'confirm_delete_plano_{opcao_plano}'] = False
                        st.rerun()

                st.markdown("---")
                st.subheader("Assistente de Adição")

                if exercisedb:
                    all_muscles = set()
                    all_equipment = set()
                    for ex in exercisedb:
                        if isinstance(ex, dict):
                            for muscle in ex.get("primaryMuscles", []): all_muscles.add(muscle.title())
                            equip = ex.get("equipment")
                            if equip: all_equipment.add(equip.title())
                    
                    muscle_options = ["Todos"] + sorted(list(all_muscles))
                    equipment_options = ["Todos"] + sorted(list(all_equipment))
                    
                    selected_muscle = st.selectbox("Filtrar por grupo muscular:", options=muscle_options, key="filtro_grupo_muscular")
                    selected_equipment = st.selectbox("Filtrar por equipamento:", options=equipment_options, key="filtro_equipamento")
                    
                    search_term = st.text_input("Buscar exercício por nome:").lower()

                    current_filter_state = f"{selected_muscle}-{selected_equipment}-{search_term}"
                    if 'last_filter_state' not in st.session_state or st.session_state.last_filter_state != current_filter_state:
                        st.session_state.last_filter_state = current_filter_state
                        st.session_state.exercises_to_show = 5
                    if 'exercises_to_show' not in st.session_state:
                        st.session_state.exercises_to_show = 5

                    if search_term or selected_muscle != "Todos" or selected_equipment != "Todos":
                        filtered_exercises = []
                        for ex in exercisedb:
                            if not isinstance(ex, dict): continue
                            muscle_match = (selected_muscle == "Todos" or any(m.title() == selected_muscle for m in ex.get("primaryMuscles", [])))
                            equip_match = (selected_equipment == "Todos" or (ex.get("equipment") or "").title() == selected_equipment)
                            name_match = search_term in ex.get("name", "").lower()
                            if muscle_match and equip_match and name_match:
                                filtered_exercises.append(ex)

                        if not filtered_exercises:
                            st.info("Nenhum exercício encontrado com os filtros selecionados.")
                        
                        base_image_path = config.ASSETS_DIR / "exercises"
                        exercises_to_display = filtered_exercises[:st.session_state.exercises_to_show]
                        for i, ex in enumerate(exercises_to_display):
                            ex_name = ex.get("name")
                            instruction = ex.get("instructions", [])
                            if not ex_name: continue
                            with st.container(border=True):
                                st.markdown(f"**{ex_name}**")
                                images = ex.get("images", [])
                                if len(images) == 2:
                                    image_path1 = base_image_path / Path(images[0])
                                    image_path2 = base_image_path / Path(images[1])
                                    if image_path1.exists() and image_path2.exists():
                                        anim_html = utils.get_image_animation_html(image_path1, image_path2, width=500)
                                        st.markdown(anim_html, unsafe_allow_html=True)
                                elif images:
                                    image_path = base_image_path / Path(images[0])
                                    if image_path.exists(): st.image(str(image_path), use_column_width=True)

                                st.markdown("<br/>", unsafe_allow_html=True)
                                col_1, col_2 = st.columns([1, 1])
                                with col_1:
                                    st.markdown(f"**Grupo Muscular:** {', '.join(ex.get('primaryMuscles', []))}")
                                    st.markdown(f"**Músculo Secundário:** {', '.join(ex.get('secondaryMuscles', []))}")
                                    st.markdown(f"**Equipamento:** {ex.get('equipment', 'N/A')}")
                                    st.markdown(f"**Nível:** {ex.get('level', 'N/A')}")
                                with col_2:
                                    st.markdown(f"**Músculos Trabalhados:**")
                                    primary, secondary = ex.get("primaryMuscles", []), ex.get("secondaryMuscles", [])
                                    img_col1, img_col2 = st.columns(2)
                                    with img_col1:
                                        front_primary = [m for m in primary if m.lower() in config.FRONT_MUSCLES]
                                        front_secondary = [m for m in secondary if m.lower() in config.FRONT_MUSCLES]
                                        html_front = utils.render_muscle_diagram(config.PATH_GRAFICO_MUSCULOS_FRONT, front_primary, front_secondary, width=150)
                                        st.markdown(html_front, unsafe_allow_html=True)
                                    with img_col2:
                                        back_primary = [m for m in primary if m.lower() in config.BACK_MUSCLES]
                                        back_secondary = [m for m in secondary if m.lower() in config.BACK_MUSCLES]
                                        html_back = utils.render_muscle_diagram(config.PATH_GRAFICO_MUSCULOS_BACK, back_primary, back_secondary, width=150)
                                        st.markdown(html_back, unsafe_allow_html=True)
                                st.markdown('')
                                if instruction:
                                    with st.expander("Instruções"):
                                        for inst in instruction: st.markdown(f"- {inst}")
                                
                                if st.button("Adicionar ao plano", key=f"add_local_{i}_{ex.get('id', ex_name)}", use_container_width=True):
                                    id_plano_selecionado = df_planos_treino[df_planos_treino['nome_plano'] == opcao_plano]['id_plano'].iloc[0]
                                    exercicios_atuais_plano = df_exercicios_todos[df_exercicios_todos['id_plano'] == id_plano_selecionado]
                                    nova_ordem = len(exercicios_atuais_plano)
                                    novo_exercicio = pd.DataFrame([{'id_plano': id_plano_selecionado, 'nome_exercicio': ex_name, 'tipo_exercicio': 'Musculação', 'series_planejadas': 3, 'repeticoes_planejadas': '8-12', 'ordem': nova_ordem}])
                                    df_exercicios_todos = pd.concat([df_exercicios_todos, novo_exercicio], ignore_index=True)
                                    utils.salvar_df(df_exercicios_todos, path_exercicios)
                                    st.toast(f"'{ex_name}' adicionado ao plano '{opcao_plano}'!")
                                    
                                    if 'macro_select_planning' in st.session_state:
                                        st.session_state._preserve_macro_selection_on_rerun = st.session_state.macro_select_planning
                                    
                                    st.rerun()

                        if len(filtered_exercises) > st.session_state.exercises_to_show:
                            if st.button("Exibir mais 10"):
                                st.session_state.exercises_to_show += 10
                                st.rerun()
        with c2:
            if opcao_plano != "-- Criar Novo Plano --":
                st.markdown(f"##### Exercícios do Treino: **{opcao_plano}**")
                id_plano_selecionado = df_planos_treino[df_planos_treino['nome_plano'] == opcao_plano]['id_plano'].iloc[0]
                df_exercicios_plano = df_exercicios_todos[df_exercicios_todos['id_plano'] == id_plano_selecionado].copy()
                
                if 'ordem' not in df_exercicios_plano.columns or df_exercicios_plano['ordem'].isnull().any():
                    if 'ordem' in df_exercicios_plano.columns: df_exercicios_plano = df_exercicios_plano.drop(columns=['ordem'])
                    df_exercicios_plano = df_exercicios_plano.reset_index(drop=True).reset_index().rename(columns={'index': 'ordem'})
                df_exercicios_plano = df_exercicios_plano.sort_values('ordem')
                df_exercicios_plano['repeticoes_planejadas'] = df_exercicios_plano['repeticoes_planejadas'].astype(str)
                
                exercicios_editados = st.data_editor(
                    df_exercicios_plano, num_rows="dynamic", use_container_width=True, key=f"editor_exercicios_tab", hide_index=True,
                    column_order=("ordem", "nome_exercicio", "tipo_exercicio", "series_planejadas", "repeticoes_planejadas"),
                    column_config={
                        "_index": st.column_config.Column(disabled=True), "id_plano": None,
                        "ordem": st.column_config.NumberColumn("Ordem", width="small", required=True, help="Edite os números para reordenar os exercícios."),
                        "nome_exercicio": st.column_config.TextColumn("Exercício", required=True),
                        "tipo_exercicio": st.column_config.SelectboxColumn("Tipo", options=["Musculação", "Cardio"], required=True),
                        "series_planejadas": st.column_config.NumberColumn("Séries", min_value=1, required=True),
                        "repeticoes_planejadas": st.column_config.TextColumn("Meta (Reps ou Min)", required=True)
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

    st.subheader("Passo 2: Estruture a Periodização dos Treinos")
    st.markdown("##### 1. Macrociclo")
    if 'nome' not in df_macro.columns:
        df_macro = pd.DataFrame(columns=['nome']).sort_values('nome')
    df_macro = df_macro.sort_values('nome')
    lista_macros = ["-- Criar Novo Macrociclo --"] + df_macro['nome'].tolist() if 'nome' in df_macro.columns else ["-- Criar Novo Macrociclo --"]
    macro_selecionado_nome = st.selectbox("Selecione um Macrociclo para gerenciar ou crie um novo", options=lista_macros, key="macro_select_planning")

    if macro_selecionado_nome == "-- Criar Novo Macrociclo --":
        with st.form("form_novo_macro"):
            st.write(f"Crie um novo grande ciclo de treino (ex: Preparação Verão {datetime.today().year}).")
            st.text_input("Nome do Macrociclo", key="nome_macro_input")
            st.text_area("Objetivo Principal", key="objetivo_macro_input")
            col1, col2 = st.columns(2)
            col1.date_input("Data de Início", value=date.today(), key="data_inicio_macro_input")
            col2.date_input("Data de Fim", value=date.today() + pd.DateOffset(months=3), key="data_fim_macro_input")
            st.form_submit_button("Criar Macrociclo", on_click=callback_criar_macro)
    
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
                if 'macro_select_planning' in st.session_state: del st.session_state.macro_select_planning
                st.rerun()
            if col_conf2.button("Cancelar"):
                st.session_state[f'confirm_delete_macro_{id_macro_ativo}'] = False
                st.rerun()

        st.markdown("---")
        st.markdown(f"##### 2. Mesociclos (As Fases do '{macro_selecionado_nome}')")
        mesos_do_macro = df_meso[df_meso['id_macrociclo'] == id_macro_ativo].copy() if 'id_macrociclo' in df_meso.columns else pd.DataFrame()
        colunas_meso = {
            'id_mesociclo': pd.Series(dtype='Int64'), 'id_macrociclo': pd.Series(dtype='Int64'), 'nome': pd.Series(dtype='str'),
            'ordem': pd.Series(dtype='Int64'), 'duracao_semanas': pd.Series(dtype='Int64'), 'foco_principal': pd.Series(dtype='str')
        }
        for col, dtype_series in colunas_meso.items():
            if col not in mesos_do_macro.columns: mesos_do_macro[col] = dtype_series
        mesos_do_macro['duracao_semanas'] = mesos_do_macro['duracao_semanas'].fillna(4)
        mesos_do_macro = mesos_do_macro.astype({'nome': str, 'foco_principal': str, 'ordem': 'Int64', 'duracao_semanas': 'Int64'})
        
        # >>>>>>>> CORREÇÃO AQUI <<<<<<<<<<
        # Garante que o DataFrame tenha um índice limpo antes de ser passado para o editor.
        mesos_do_macro.reset_index(drop=True, inplace=True)

        mesos_editados = st.data_editor(
            mesos_do_macro,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_meso",
            column_config={
                "id_mesociclo": None, 
                "id_macrociclo": None,
                "nome": st.column_config.TextColumn("Nome do Mesociclo", required=True),
                "ordem": st.column_config.NumberColumn("Ordem", min_value=1, required=True),
                "duracao_semanas": st.column_config.NumberColumn("Duração (Semanas)", min_value=1, required=True, default=4),
                "foco_principal": st.column_config.TextColumn("Foco Principal")
            }
        )
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
        st.markdown("##### 3. Rotina da Semana")
        mesos_do_macro = mesos_do_macro.sort_values('nome')
        lista_mesos_nomes = mesos_do_macro['nome'].dropna().tolist() if not mesos_do_macro.empty else []
        if lista_mesos_nomes:
            meso_selecionado_nome = st.selectbox("Selecione um Mesociclo para planejar as semanas", options=lista_mesos_nomes, key=f"meso_select_{id_macro_ativo}")
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
                
                plano_semanal_editado = st.data_editor(plano_semanal_atual, use_container_width=True, hide_index=True, key=f"editor_semana_{id_meso_ativo}_{semana_num}", column_config={
                    "dia_da_semana": st.column_config.TextColumn("Dia da Semana", disabled=True),
                    "plano_treino": st.column_config.SelectboxColumn("Modelo de Treino", options=planos_disponiveis, required=True)
                })
                
                col_save, col_clear = st.columns(2)
                with col_save:
                    if st.button("💾 Salvar Plano da Semana"):
                        df_plano_sem_outros = df_plano_sem.drop(plano_semanal_salvo.index) if not plano_semanal_salvo.empty else df_plano_sem
                        novo_plano_semanal = plano_semanal_editado.copy()
                        novo_plano_semanal['id_mesociclo'], novo_plano_semanal['semana_numero'] = id_meso_ativo, semana_num
                        df_final_semanal = pd.concat([df_plano_sem_outros, novo_plano_semanal], ignore_index=True)
                        utils.salvar_df(df_final_semanal, path_plano_sem)
                        st.toast(f"Plano para a Semana {semana_num} salvo!", icon="🗓️")
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

def render_registro_sub_tab(username: str, user_data: Dict[str, Any]):
    """
    Renderiza a sub-aba para registrar treinos, com um painel de controle
    customizado para corresponder fielmente ao layout do usuário.
    """
    # --- LÓGICA DE DADOS E TIMERS (INICIALIZAÇÃO) ---
    workout_today = logic.get_workout_for_day(user_data, date.today())
    df_log_exercicios = user_data.get("df_log_exercicios", pd.DataFrame())

    # --- Carrega o banco de dados de exercícios ---
    path_exercicios_db = config.ASSETS_DIR / "exercises" / "exercicios.json"
    exercisedb_data = utils.carregar_banco_exercicios(path_exercicios_db)
    
    exercisedb = []
    if isinstance(exercisedb_data, list):
        exercisedb = exercisedb_data
    elif isinstance(exercisedb_data, dict) and "exercises" in exercisedb_data:
        exercisedb = exercisedb_data["exercises"]
    
    # --- Cria mapas de consulta ---
    exercise_image_map = {}
    exercise_details_map = {}
    exercise_name_list = []
    base_image_path = config.ASSETS_DIR / "exercises"
    if exercisedb:
        for ex_data in exercisedb:
            if isinstance(ex_data, dict) and ex_data.get("name"):
                ex_name = ex_data["name"]
                exercise_name_list.append(ex_name)
                normalized_name = utils.normalizar_texto(ex_name)
                exercise_details_map[normalized_name] = ex_data
                if ex_data.get("images"):
                    image_paths = [base_image_path / Path(img_file) for img_file in ex_data["images"]]
                    exercise_image_map[normalized_name] = image_paths

    # --- GERENCIAMENTO DE ESTADO PARA REORDENAÇÃO E TIMERS ---
    todays_plan_name = workout_today['nome_plano'] if workout_today else None
    
    # Inicializa ou reseta o estado do treino se o plano do dia mudou
    if 'current_plan_name' not in st.session_state or st.session_state.current_plan_name != todays_plan_name:
        df_to_load = workout_today['exercicios'].copy() if workout_today else pd.DataFrame()
        st.session_state.todays_workout_df = df_to_load
        st.session_state.current_plan_name = todays_plan_name
        
        # Inicializa o contador de séries para cada exercício
        if not df_to_load.empty:
            st.session_state.workout_sets = {
                index: int(row.get('series_planejadas', 1))
                for index, row in df_to_load.iterrows()
            }
        else:
            st.session_state.workout_sets = {}
        
        # Reseta o estado de adição de exercício
        st.session_state.adding_exercise = False

    # CORREÇÃO: Garante que workout_sets sempre exista
    if 'workout_sets' not in st.session_state:
        st.session_state.workout_sets = {}

    # Inicializa outros estados se não existirem
    if 'timer_started' not in st.session_state: st.session_state.timer_started = False
    if 'start_time' not in st.session_state: st.session_state.start_time = None
    if 'elapsed_minutes' not in st.session_state: st.session_state.elapsed_minutes = 0.0
    if 'rest_timer_running' not in st.session_state: st.session_state.rest_timer_running = False
    if 'rest_end_time' not in st.session_state: st.session_state.rest_end_time = None
    if 'total_rest_seconds' not in st.session_state: st.session_state.total_rest_seconds = 0
    if 'current_rest_duration' not in st.session_state: st.session_state.current_rest_duration = 0
    if 'last_check_time' not in st.session_state: st.session_state.last_check_time = None
    if 'set_durations' not in st.session_state: st.session_state.set_durations = {}
    if 'checkbox_states' not in st.session_state: st.session_state.checkbox_states = {}

    with st.sidebar:
        if st.session_state.timer_started or st.session_state.rest_timer_running:
            st_autorefresh(interval=1000, key="global_timer_refresher")

    # --- PAINEL DE CONTROLE DO TREINO ---
    with st.container(border=True):
        col1, col2, col3 = st.columns([2.5, 3, 3])
        with col1:
            if st.session_state.timer_started and st.session_state.start_time:
                accumulated_seconds = st.session_state.elapsed_minutes * 60
                current_elapsed = datetime.now() - st.session_state.start_time
                total_seconds = accumulated_seconds + current_elapsed.total_seconds()
                hours, remainder = divmod(int(total_seconds), 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                total_seconds = st.session_state.elapsed_minutes * 60
                hours, remainder = divmod(int(total_seconds), 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            st.markdown("<p style='font-size: 0.9rem; color: rgba(250, 250, 250, 0.7);'>Tempo Total</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size: 2.5rem; font-weight: bold; margin-top: -10px;'>{time_str}</p>", unsafe_allow_html=True)
            btn_c1, btn_c2, btn_c3 = st.columns(3)
            if btn_c1.button("▶️ Iniciar", width='stretch', disabled=st.session_state.timer_started):
                st.session_state.timer_started = True
                st.session_state.start_time = datetime.now()
                st.session_state.last_check_time = time.time()
                st.rerun()
            if btn_c2.button("⏸️ Parar", width='stretch', disabled=not st.session_state.timer_started):
                if st.session_state.start_time:
                    elapsed_time = datetime.now() - st.session_state.start_time
                    st.session_state.elapsed_minutes += elapsed_time.total_seconds() / 60
                    st.session_state.start_time = None
                st.session_state.timer_started = False
                st.session_state.last_check_time = None
                st.rerun()
            if btn_c3.button("🔄 Zerar", width='stretch'):
                st.session_state.timer_started = False
                st.session_state.start_time = None
                st.session_state.elapsed_minutes = 0.0
                st.session_state.total_rest_seconds = 0
                st.session_state.current_rest_duration = 0
                st.session_state.last_check_time = None
                st.session_state.set_durations = {}
                st.session_state.checkbox_states = {}
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
                if st.button("Iniciar Descanso", width='stretch', disabled=st.session_state.rest_timer_running, key="start_rest_button_final_v3"):
                    st.session_state.rest_timer_running = True
                    st.session_state.rest_end_time = time.time() + default_rest_time
                    st.session_state.current_rest_duration = default_rest_time
                    st.rerun()
            with rest_display_col:
                total_rest_min, total_rest_sec = divmod(st.session_state.total_rest_seconds, 60)
                total_rest_str = f"{total_rest_min:02d}:{total_rest_sec:02d}"
                if st.session_state.rest_timer_running and st.session_state.rest_end_time:
                    remaining_time = st.session_state.rest_end_time - time.time()
                    if remaining_time > 0:
                        minutes, seconds = divmod(int(remaining_time), 60)
                        time_str = f"{minutes:02}:{seconds:02}"
                        color = "#FF4B4B" if remaining_time < 11 else "inherit"
                        st.markdown(f"""
                        <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;'>
                            <p style='font-size: 3.5rem; color: {color}; font-weight: bold;'>{time_str}</p>
                            <p style='font-size: 0.9rem; color: rgba(250, 250, 250, 0.7); margin-bottom: 10px;'>Descanso total: {total_rest_str}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.session_state.total_rest_seconds += st.session_state.current_rest_duration
                        st.session_state.current_rest_duration = 0
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
    if 'todays_workout_df' in st.session_state and not st.session_state.todays_workout_df.empty:
        exercicios_df = st.session_state.todays_workout_df.copy()
        
        for index, exercicio in exercicios_df.iterrows():
            with st.container(border=True):
                # MODIFICAÇÃO: Layout principal com duas colunas: conteúdo e controles
                main_col, controls_col = st.columns([0.9, 0.1])

                with main_col:
                 
                    with st.popover(f"##### {exercicio['nome_exercicio']}"):
                        nome_normalizado = utils.normalizar_texto(exercicio['nome_exercicio'])
                        exercise_details = exercise_details_map.get(nome_normalizado)
                        image_paths = exercise_image_map.get(nome_normalizado)

                        if image_paths and len(image_paths) == 2:
                            image_path1, image_path2 = image_paths[0], image_paths[1]
                            if image_path1.exists() and image_path2.exists():
                                anim_html = utils.get_image_animation_html(image_path1, image_path2, width=300)
                                st.markdown(anim_html, unsafe_allow_html=True)
                        elif image_paths and image_paths[0].exists():
                            st.image(str(image_paths[0]), use_column_width=True)
                        
                        if exercise_details:
                            instructions = exercise_details.get("instructions", [])
                            if instructions:
                                with st.expander("Instruções"):
                                    for inst in instructions: st.markdown(f"- {inst}")

                    tipo_exercicio = exercicio.get('tipo_exercicio', 'Musculação')
                    previous_perf_data = logic.get_previous_performance(df_log_exercicios, exercicio['nome_exercicio'])
                    
                    if tipo_exercicio == 'Cardio':
                        previous_performance_str = f"{previous_perf_data.get('minutos', 0)} min" if previous_perf_data.get('minutos') else "N/A"
                    else:
                        previous_performance_str = f"{previous_perf_data.get('kg', 0)} kg x {previous_perf_data.get('reps', 0)}" if previous_perf_data.get('kg') is not None else "N/A"

                    num_series = st.session_state.workout_sets.get(index, 1)

                    if tipo_exercicio == 'Cardio':
                        col_header = st.columns([0.4, 0.8, 2, 2, 2.4, 0.8])
                        col_header[0].write("")
                        col_header[1].write("**Série**")
                        col_header[2].write("**Anterior**")
                        col_header[3].write("**Meta**")
                        col_header[4].write("**Minutos**")
                        col_header[5].write("✔")
                        for i in range(1, num_series + 1):
                            key_base = f"cardio_{exercicio['nome_exercicio']}_{i}_{index}"
                            cols = st.columns([0.4, 0.8, 2, 2, 2.4, 0.8])
                            if cols[0].button("🗑️", key=f"remove_set_{key_base}", help="Remover série"):
                                if st.session_state.workout_sets[index] > 1:
                                    st.session_state.workout_sets[index] -= 1
                                    st.rerun()
                                else:
                                    st.toast("Não é possível remover a última série.", icon="⚠️")
                            
                            cols[1].markdown(f"**{i}**")
                            cols[2].markdown(f"`{previous_performance_str}`")
                            cols[3].markdown(f"`{exercicio['repeticoes_planejadas']}`")
                            cols[4].number_input("Min", key=f"min_{key_base}", min_value=0, step=1, label_visibility="collapsed", value=previous_perf_data.get('minutos', 0))
                            cols[5].checkbox("Feito", key=f"done_{key_base}", label_visibility="collapsed")
                    else: # Musculação
                        col_header = st.columns([0.4, 0.8, 2, 2, 1.2, 1.2, 0.8])
                        col_header[0].write("")
                        col_header[1].write("**Série**")
                        col_header[2].write("**Anterior**")
                        col_header[3].write("**Meta**")
                        col_header[4].write("**kg**")
                        col_header[5].write("**Reps**")
                        col_header[6].write("✔")
                        for i in range(1, num_series + 1):
                            key_base = f"musc_{exercicio['nome_exercicio']}_{i}_{index}"
                            cols = st.columns([0.4, 0.8, 2, 2, 1.2, 1.2, 0.8])
                            if cols[0].button("🗑️", key=f"remove_set_{key_base}", help="Remover série"):
                                if st.session_state.workout_sets[index] > 1:
                                    st.session_state.workout_sets[index] -= 1
                                    st.rerun()
                                else:
                                    st.toast("Não é possível remover a última série.", icon="⚠️")

                            cols[1].markdown(f"**{i}**")
                            cols[2].markdown(f"`{previous_performance_str}`")
                            cols[3].markdown(f"`{exercicio['repeticoes_planejadas']} reps`")
                            cols[4].number_input("kg", key=f"kg_{key_base}", min_value=0.0, step=0.5, label_visibility="collapsed", value=previous_perf_data.get('kg', 0.0))
                            cols[5].number_input("reps", key=f"reps_{key_base}", min_value=0, step=1, label_visibility="collapsed", value=previous_perf_data.get('reps', 0))
                            
                            checkbox_key = f"done_{key_base}"
                            prev_state = st.session_state.checkbox_states.get(checkbox_key, False)
                            is_checked = cols[6].checkbox("Feito", key=checkbox_key, label_visibility="collapsed")
                            
                            if is_checked and not prev_state:
                                if st.session_state.timer_started and st.session_state.last_check_time:
                                    now = time.time()
                                    duration_seconds = now - st.session_state.last_check_time
                                    st.session_state.set_durations[key_base] = duration_seconds / 60
                                    st.session_state.last_check_time = now
                            elif not is_checked and prev_state:
                                st.session_state.set_durations.pop(key_base, None)

                            st.session_state.checkbox_states[checkbox_key] = is_checked
                    
                    if st.button("Adicionar série", key=f"add_set_{index}"):
                        st.session_state.workout_sets[index] += 1
                        st.rerun()
                
                with controls_col:
                    # MODIFICAÇÃO: Botões de controle agora estão na mesma coluna
                    if st.button("🗑️", key=f"remove_ex_{index}_main", help="Remover exercício da sessão", use_container_width=True):
                        st.session_state.todays_workout_df.drop(index, inplace=True)
                        st.session_state.todays_workout_df.reset_index(drop=True, inplace=True)
                        st.session_state.workout_sets = {
                            idx: int(row.get('series_planejadas', 1))
                            for idx, row in st.session_state.todays_workout_df.iterrows()
                        }
                        st.rerun()

                    # Adiciona o espaço vertical
                    st.write("<div style='height: 60px;'></div>", unsafe_allow_html=True)

                    is_first = (index == 0)
                    is_last = (index == len(exercicios_df) - 1)
                    
                    if st.button("🔼", key=f"up_{index}", help="Mover para cima", use_container_width=True, disabled=is_first):
                        df = st.session_state.todays_workout_df
                        a, b = df.iloc[index-1].copy(), df.iloc[index].copy()
                        df.iloc[index-1], df.iloc[index] = b, a
                        st.session_state.todays_workout_df = df
                        st.rerun()

                    if st.button("🔽", key=f"down_{index}", help="Mover para baixo", use_container_width=True, disabled=is_last):
                        df = st.session_state.todays_workout_df
                        a, b = df.iloc[index+1].copy(), df.iloc[index].copy()
                        df.iloc[index+1], df.iloc[index] = b, a
                        st.session_state.todays_workout_df = df
                        st.rerun()

        if st.session_state.get('adding_exercise', False):
            with st.form("new_exercise_form"):
                st.subheader("Adicionar Novo Exercício")
                new_ex_name = st.selectbox("Selecione o exercício", options=sorted(exercise_name_list))
                c1, c2 = st.columns(2)
                new_ex_sets = c1.number_input("Número de séries", min_value=1, value=3)
                new_ex_reps = c2.text_input("Meta de Reps/Min", value="8-12 reps")
                
                submitted = st.form_submit_button("Adicionar Exercício ao Treino")
                if submitted:
                    new_exercise_row = pd.DataFrame([{
                        'nome_exercicio': new_ex_name,
                        'tipo_exercicio': 'Musculação',
                        'series_planejadas': new_ex_sets,
                        'repeticoes_planejadas': new_ex_reps,
                        'ordem': len(st.session_state.todays_workout_df)
                    }])
                    
                    st.session_state.todays_workout_df = pd.concat(
                        [st.session_state.todays_workout_df, new_exercise_row],
                        ignore_index=True
                    )
                    new_index = len(st.session_state.todays_workout_df) - 1
                    st.session_state.workout_sets[new_index] = new_ex_sets
                    
                    st.session_state.adding_exercise = False
                    st.rerun()
            if st.button("Cancelar"):
                st.session_state.adding_exercise = False
                st.rerun()
        else:
            if st.button("Adicionar exercício", use_container_width=True):
                st.session_state.adding_exercise = True
                st.rerun()

        st.subheader("Resumo da Sessão")
        c1_sum, c2_sum, c3_sum = st.columns(3)
        duracao_min_total = c1_sum.number_input("Tempo Total do Treino (min)", min_value=0, value=int(round(st.session_state.elapsed_minutes, 0)), step=1)
        intensidade_tr = c2_sum.selectbox("Intensidade Percebida", config.OPCOES_INTENSIDADE_TREINO, index=1)
        data_treino = c3_sum.date_input("Data do treino", value=date.today(), key="date_input_main_log")

        if st.button("Salvar Treino", type="primary", use_container_width=True):
            new_log_entries = []
            dados_pessoais = user_data.get("dados_pessoais", {})
            peso_usuario = dados_pessoais.get(config.COL_PESO, 70.0)

            total_calorias_musculacao = 0.0
            total_calorias_cardio = 0.0
            total_minutos_cardio = 0
            
            untimed_musc_sets = []
            
            for index, exercicio in exercicios_df.iterrows():
                tipo_exercicio = exercicio.get('tipo_exercicio', 'Musculação')
                num_series = st.session_state.workout_sets.get(index, 1)

                for i in range(1, num_series + 1):
                    key_prefix = "cardio" if tipo_exercicio == 'Cardio' else "musc"
                    key_base = f"{key_prefix}_{exercicio['nome_exercicio']}_{i}_{index}"
                    
                    if st.session_state.get(f'done_{key_base}'):
                        log_entry = {'Data': data_treino.strftime("%d/%m/%Y"), 'nome_exercicio': exercicio['nome_exercicio'], 'set': i}
                        
                        if tipo_exercicio == 'Cardio':
                            minutos = st.session_state.get(f'min_{key_base}', 0)
                            total_minutos_cardio += minutos
                            log_entry.update({'minutos_realizados': minutos, 'kg_realizado': 0, 'reps_realizadas': 0})
                            
                            gasto_exercicio = logic.calcular_gasto_treino(
                                cardio=True, intensidade=intensidade_tr, duracao=minutos, carga=0, peso=peso_usuario
                            )
                            total_calorias_cardio += gasto_exercicio
                        else: # Musculação
                            kg = st.session_state.get(f'kg_{key_base}', 0.0)
                            reps = st.session_state.get(f'reps_{key_base}', 0)
                            carga = kg * reps
                            log_entry.update({'kg_realizado': kg, 'reps_realizadas': reps, 'minutos_realizados': 0})
                            
                            if key_base in st.session_state.set_durations:
                                duracao = st.session_state.set_durations[key_base]
                                gasto_exercicio = logic.calcular_gasto_treino(
                                    cardio=False, intensidade=intensidade_tr, duracao=duracao, carga=carga, peso=peso_usuario
                                )
                                total_calorias_musculacao += gasto_exercicio
                            else:
                                untimed_musc_sets.append({'carga': carga})
                        
                        new_log_entries.append(log_entry)
            
            if untimed_musc_sets:
                duracao_musculacao_restante = duracao_min_total - total_minutos_cardio
                if duracao_musculacao_restante > 0 and len(untimed_musc_sets) > 0:
                    duracao_por_set_nao_cronometrado = duracao_musculacao_restante / len(untimed_musc_sets)
                    
                    for set_data in untimed_musc_sets:
                        gasto_exercicio = logic.calcular_gasto_treino(
                            cardio=False, intensidade=intensidade_tr, duracao=duracao_por_set_nao_cronometrado, 
                            carga=set_data['carga'], peso=peso_usuario
                        )
                        total_calorias_musculacao += gasto_exercicio

            if not new_log_entries:
                st.warning("Nenhuma série foi marcada como 'Feito'. O treino não foi salvo.")
            else:
                path_log_exercicios = utils.get_user_data_path(username, config.FILE_LOG_EXERCICIOS)
                utils.adicionar_registro_df(pd.DataFrame(new_log_entries), path_log_exercicios)

                gasto_est_total = total_calorias_musculacao + total_calorias_cardio
                
                path_treinos_simples = utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES)
                
                plano_executado_nome = st.session_state.current_plan_name or "Avulso (Modificado)"
                
                novo_treino_simples = pd.DataFrame([{
                    'Data': data_treino.strftime("%d/%m/%Y"),
                    'Plano Executado': plano_executado_nome,
                    'Tipo de Treino': "Misto" if total_calorias_cardio > 0 and total_calorias_musculacao > 0 else ("Cardio" if total_calorias_cardio > 0 else "Musculação"),
                    'Tempo (min)': duracao_min_total,
                    'Calorias Gastas': round(gasto_est_total, 2)
                }])
                
                utils.adicionar_registro_df(novo_treino_simples, path_treinos_simples)
                
                del st.session_state.todays_workout_df
                del st.session_state.current_plan_name
                del st.session_state.workout_sets
                st.session_state.adding_exercise = False
                st.session_state.timer_started = False
                st.session_state.start_time = None
                st.session_state.elapsed_minutes = 0.0
                st.session_state.rest_timer_running = False
                st.session_state.rest_end_time = None
                st.session_state.current_rest_duration = 0
                st.session_state.last_check_time = None
                st.session_state.set_durations = {}
                st.session_state.checkbox_states = {}

                st.toast("Treino salvo com sucesso!", icon="💪")
                st.rerun()

    else:
        st.info("Nenhum treino planejado para hoje.")

    exp = True if not workout_today else False
    with st.expander('Registro Avulso', expanded=exp):
        render_registro_avulso_form(username, user_data)
    
    dft_simples = user_data.get("df_log_treinos", pd.DataFrame())
    with st.expander("Histórico de Treinos Realizados"):
        if not dft_simples.empty:           
            dft_simples_sorted = dft_simples.copy()
            dft_simples_sorted[config.COL_DATA] = pd.to_datetime(dft_simples_sorted[config.COL_DATA], format="%d/%m/%Y")
            dft_simples_sorted = dft_simples_sorted.sort_values(by=config.COL_DATA, ascending=False).reset_index(drop=True)
            
            dft_editado = st.data_editor(
                dft_simples_sorted,
                num_rows="dynamic",
                width='stretch',
                key="editor_treinos_realizados",
                hide_index=True,
                column_config={
                    "Calorias Gastas": st.column_config.NumberColumn("Calorias Gastas (kcal)", format="%.0f")
                }
            )
            
            if st.button("💾 Salvar Alterações no Histórico", key="salvar_historico_treino"):
                original_dates = set(pd.to_datetime(dft_simples[config.COL_DATA], format="%d/%m/%Y").dt.strftime('%d/%m/%Y'))
                edited_dates = set(pd.to_datetime(dft_editado[config.COL_DATA]).dt.strftime('%d/%m/%Y'))

                deleted_dates = original_dates - edited_dates

                if deleted_dates:
                    path_log_exercicios = utils.get_user_data_path(username, config.FILE_LOG_EXERCICIOS)
                    df_log_exercicios_completo = utils.carregar_df(path_log_exercicios)
                    
                    if not df_log_exercicios_completo.empty and 'Data' in df_log_exercicios_completo.columns:
                        df_log_exercicios_filtrado = df_log_exercicios_completo[~df_log_exercicios_completo['Data'].isin(deleted_dates)]
                        utils.salvar_df(df_log_exercicios_filtrado, path_log_exercicios)

                dft_editado[config.COL_DATA] = pd.to_datetime(dft_editado[config.COL_DATA]).dt.strftime('%d/%m/%Y')
                utils.salvar_df(dft_editado, utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES))
                st.toast("Histórico de treinos atualizado!", icon="💾")
                st.rerun()

def render_registro_avulso_form(username: str, user_data: Dict[str, Any]):
    """Renderiza o formulário simples para registrar um treino avulso."""
    # st.subheader("Registrar Treino Avulso")
    df_planos_treino = user_data.get("df_planos_treino", pd.DataFrame())
    if 'nome_plano' not in df_planos_treino.columns:
        df_planos_treino = pd.DataFrame(columns=['nome_plano']).sort_values('nome_plano')
    df_planos_treino = df_planos_treino.sort_values('nome_plano')
    
    dados_pessoais = user_data.get("dados_pessoais", {})
    path_treinos = utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES)
    lista_planos = ["Nenhum (Avulso)"] + (df_planos_treino['nome_plano'].tolist() if 'nome_plano' in df_planos_treino.columns else [])
    plano_executado = st.selectbox("Qual plano de treino você executou?", options=lista_planos, key="plano_avulso")

    # Lógica para atualizar o toggle "Cardio?" se o plano de treino mudar
    last_plan = st.session_state.get('last_plano_avulso', None)
    if last_plan != plano_executado:
        # Se o plano mudou, define o estado do toggle baseado no nome do novo plano
        default_cardio = "cardio" in plano_executado.lower() if plano_executado != "Nenhum (Avulso)" else False
        st.session_state.cardio_reg_avulso = default_cardio
    
    # Armazena o plano atual para a próxima execução
    st.session_state.last_plano_avulso = plano_executado
    
    # O toggle agora usa o valor do session_state, que é atualizado pela lógica acima
    cardio = st.toggle("Cardio?", key="cardio_reg_avulso")

    c1, c2, c3, c4 = st.columns(4)
    intensidade_tr = c1.selectbox("Intensidade", config.OPCOES_INTENSIDADE_TREINO, index=1, key="intensidade_reg_avulso")
    duracao_min = c2.number_input("Tempo (min)", 0, 600, 60, 5, key="duracao_reg_avulso")
    # O campo de carga total agora é desabilitado corretamente quando o toggle muda
    carga_total = c3.number_input("Carga total (kg)", 0.0, step=5.0, value=5000.0, key="carga_reg_avulso", disabled=cardio)
    data_treino = c4.date_input("Data do treino", value=date.today(), key="date_input_avulso")
    
    gasto_est = logic.calcular_gasto_treino(cardio, intensidade_tr, duracao_min, carga_total, dados_pessoais.get(config.COL_PESO, 70.0))
    st.metric("Gasto calórico estimado", f"{gasto_est:.0f} kcal")

    if st.button("Salvar Treino Avulso", type="primary", width="stretch"):
        novo_treino = pd.DataFrame([{
            config.COL_DATA: data_treino.strftime("%d/%m/%Y"),
            "Plano Executado": plano_executado if plano_executado != "Nenhum (Avulso)" else "Avulso",
            "Tipo de Treino": "Cardio" if cardio else "Musculação",
            "Tempo (min)": duracao_min,
            "Calorias Gastas": round(gasto_est, 2)
        }])
        utils.adicionar_registro_df(novo_treino, path_treinos)
        st.toast("Treino avulso adicionado com sucesso!", icon="💪")
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
        with st.form(key="form_adicionar_medida_evolucao"):
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
                nova_medida = pd.DataFrame([{
                    "semana": len(dfe_final) + 1,
                    "data": data_med.strftime("%d/%m/%Y"),
                    "peso": peso_in,
                    "var": var,
                    "gordura_corporal": gord_corp,
                    "gordura_visceral": gord_visc,
                    "musculos_esqueleticos": musc_esq,
                    "cintura": cintura,
                    "peito": peito,
                    "braco": braco,
                    "coxa": coxa
                }])
                utils.adicionar_registro_df(nova_medida, path_evolucao)

                path_pessoais = utils.get_user_data_path(username, config.FILE_DADOS_PESSOAIS)
                dfp = utils.carregar_df(path_pessoais)
                if not dfp.empty:
                    if float(peso_in) > 0:
                        dfp.loc[0, config.COL_PESO] = float(peso_in)
                    if float(gord_corp) > 0:
                        dfp.loc[0, 'gordura_corporal'] = float(gord_corp)
                    if float(gord_visc) > 0:
                        dfp.loc[0, 'gordura_visceral'] = float(gord_visc)
                    if float(musc_esq) > 0:
                        dfp.loc[0, 'massa_muscular'] = float(musc_esq)
                    utils.salvar_df(dfp, path_pessoais)

                st.toast("Medida adicionada com sucesso!", icon="📏")
                _get_cached_evolution_charts.clear()
                st.rerun()

    # CORREÇÃO 1: Movido o "Histórico de medições" para o topo da aba para melhor usabilidade.
    with st.expander("Histórico de medições", expanded=False):
        if not dfe_final.empty:
            # CORREÇÃO 2: Adicionado .reset_index(drop=True) para remover a coluna de índice.
            df_display = dfe_final.sort_values("semana", ascending=False).reset_index(drop=True)
            dfe_editado = st.data_editor(
                df_display,
                num_rows="dynamic",
                width='stretch',
                hide_index=True,
                key="editor_evolucao",
                column_config={
                    "semana": st.column_config.NumberColumn("Semana", format="%d"),
                    "data": st.column_config.TextColumn("Data"),
                    "peso": st.column_config.NumberColumn("Peso (kg)", format="%.1f"),
                    "var": st.column_config.NumberColumn("Variação (kg)", format="%.1f"),
                    "gordura_corporal": st.column_config.NumberColumn("Gordura Corporal (%)", format="%.1f"),
                    "gordura_visceral": st.column_config.NumberColumn("Gordura Visceral (%)", format="%.1f"),
                    "musculos_esqueleticos": st.column_config.NumberColumn("Massa Muscular (%)", format="%.1f"),
                    "cintura": st.column_config.NumberColumn("Cintura (cm)", format="%.1f"),
                    "peito": st.column_config.NumberColumn("Peito (cm)", format="%.1f"),
                    "braco": st.column_config.NumberColumn("Braço (cm)", format="%.1f"),
                    "coxa": st.column_config.NumberColumn("Coxa (cm)", format="%.1f"),
                }
            )
            if st.button("💾 Salvar Alterações no Histórico", key="salvar_historico_evolucao"):
                df_para_salvar = dfe_editado.sort_values("semana", ascending=True)
                utils.salvar_df(df_para_salvar, path_evolucao)

                path_pessoais = utils.get_user_data_path(username, config.FILE_DADOS_PESSOAIS)
                dfp = utils.carregar_df(path_pessoais)

                if not dfp.empty and not df_para_salvar.empty:
                    ultima_medida = df_para_salvar.iloc[-1]
                    
                    if pd.notna(ultima_medida.get(config.COL_PESO)) and float(ultima_medida.get(config.COL_PESO)) > 0:
                        dfp.loc[0, config.COL_PESO] = float(ultima_medida.get(config.COL_PESO))
                    if pd.notna(ultima_medida.get('gordura_corporal')) and float(ultima_medida.get('gordura_corporal')) > 0:
                        dfp.loc[0, 'gordura_corporal'] = float(ultima_medida.get('gordura_corporal'))
                    if pd.notna(ultima_medida.get('gordura_visceral')) and float(ultima_medida.get('gordura_visceral')) > 0:
                        dfp.loc[0, 'gordura_visceral'] = float(ultima_medida.get('gordura_visceral'))
                    if pd.notna(ultima_medida.get('musculos_esqueleticos')) and float(ultima_medida.get('musculos_esqueleticos')) > 0:
                        dfp.loc[0, 'massa_muscular'] = float(ultima_medida.get('musculos_esqueleticos'))

                    utils.salvar_df(dfp, path_pessoais)

                st.toast("Histórico de evolução atualizado!", icon="✅")
                _get_cached_evolution_charts.clear()
                st.rerun()
        else:
            st.info("Adicione sua primeira medida para começar a ver o histórico.")


    dados_atuais = logic.get_latest_metrics(dados_pessoais, dfe_final)

    if not dfe_final.empty:
        st.subheader("📊 Composição Corporal e Métricas")

        metricas = logic.calcular_metricas_saude(dados_atuais, objetivo_info)

        st.info(
            f"Variação semanal estimada: **{metricas['var_semanal_kg']:+.2f} kg** "
            f"({metricas['var_semanal_percent']:+.2f}%) • Conclusão prevista: "
            f"**{metricas['data_objetivo_fmt']}** ({metricas['dias_restantes']} dias restantes)"
        )

        def classificar_imc(v):
            if v < 18.5: return "Abaixo do peso"
            if v <= 24.9: return "Peso normal"
            if v <= 29.9: return "Sobrepeso"
            return "Obesidade"

        sexo_atual = dados_atuais.get('sexo', 'M')
        idade_atual = dados_atuais.get('idade', 30)

        classificacoes = logic.classificar_composicao_corporal(
            dados_atuais.get('gordura_corporal', 0),
            dados_atuais.get('gordura_visceral', 0),
            dados_atuais.get('massa_muscular', 0),
            sexo_atual,
            idade_atual
        )

        ranges_gordura = logic.obter_faixa_gordura_ideal(sexo_atual, idade_atual)
        ranges_visceral = (0, 9)
        ranges_musculo = {"M": (34, 39), "F": (24, 29)}.get(sexo_atual)
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.info(f"IMC: **{metricas['IMC']:.1f}** — {classificar_imc(metricas['IMC'])}")
            plotting.plot_composition_range("Índice de Massa Corporal (IMC)", metricas['IMC'], (18.5, 24.9), (15, 40))
        with col2:
            st.info(f"Gordura corporal: **{dados_atuais.get('gordura_corporal', 0):.1f}%** — {classificacoes['gordura']}")
            plotting.plot_composition_range("Gordura Corporal (%)", dados_atuais.get('gordura_corporal', 0), ranges_gordura, (0, 50))
        with col3:
            st.info(f"Gordura visceral: **{dados_atuais.get('gordura_visceral', 0):.1f}** — {classificacoes['visceral']}")
            plotting.plot_composition_range("Gordura Visceral (%)", dados_atuais.get('gordura_visceral', 0), ranges_visceral, (0, 20))
        with col4:
            st.info(f"Massa muscular: **{dados_atuais.get('massa_muscular', 0):.1f}%** — {classificacoes['musculo']}")
            plotting.plot_composition_range("Massa Muscular (%)", dados_atuais.get('massa_muscular', 0), ranges_musculo, (15, 60))

        st.subheader("📈 Evolução de medidas")

        fig1, fig2 = _get_cached_evolution_charts(dfe_final, dados_pessoais, objetivo_info)

        if fig1:
            st.plotly_chart(fig1, width='stretch')
        if fig2:
            st.plotly_chart(fig2, width='stretch')

    else:
        # Se não houver histórico, a mensagem de "Adicione sua primeira medida" deve aparecer aqui.
        st.info("Adicione sua primeira medida para começar a ver a evolução.")
