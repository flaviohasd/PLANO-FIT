# ==============================================================================
# PLANO FIT APP - ARQUIVO PRINCIPAL
# ==============================================================================

import streamlit as st
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components
import config
import utils
import os
import ui
import auth
import base64
from datetime import date, datetime, timedelta

# A configuração da página deve ser a primeira chamada do Streamlit e executada apenas uma vez.
st.set_page_config(page_title=config.APP_TITLE, layout="wide")

# --- SINCRONIZAÇÃO DE FUSO HORÁRIO (MÉTODO ROBUSTO VIA URL PARAM) ---
if 'timezone_offset' not in st.session_state:
    st.session_state.timezone_offset = None

# Passo 1: Verifica se o fuso horário foi retornado como um parâmetro na URL.
if hasattr(st, 'query_params') and 'tz_offset' in st.query_params:
    try:
        # Se sim, salva na sessão, limpa o parâmetro da URL e re-executa.
        st.session_state.timezone_offset = int(st.query_params['tz_offset'])
        # A linha abaixo requer Streamlit 1.33+. Se der erro, pode ser removida.
        st.query_params.clear()
        st.rerun()
    except (ValueError, TypeError):
        # Se o parâmetro for inválido, limpa e tenta de novo.
        st.query_params.clear()
        st.rerun()

# Passo 2: Se o fuso horário ainda não está na sessão, executa o script no navegador.
if st.session_state.timezone_offset is None:
    # Exibe a mensagem de carregamento e o script que irá recarregar a página com o parâmetro.
    st.info("Sincronizando fuso horário do seu navegador...")
    
    components.html(
        f"""
        <script>
            // Evita um loop infinito, só executa se o parâmetro não existir.
            if (!window.location.search.includes('tz_offset=')) {{
                const offset = new Date().getTimezoneOffset();
                // Adiciona o parâmetro de fuso horário à URL e recarrega a página.
                window.location.href = window.location.href + '?tz_offset=' + offset;
            }}
        </script>
        """,
        height=0
    )

# Passo 3: Se o fuso horário já foi capturado, executa o aplicativo principal.
else:
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None

    if not st.session_state.logged_in:
        auto_login_user = auth.get_last_user()
        if auto_login_user:
            st.session_state.logged_in = True
            st.session_state.current_user = auto_login_user
            st.rerun()

    # --- INTERFACE ---
    if not st.session_state.logged_in:
        ui.render_login_screen()
    else:
        st.markdown(
            "<h1 style='text-align: center;'>🏋️‍♂️ PLANO FIT</h1>",
            unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align: center;'>Metas, planejamento alimentar, treinos e evolução</p>",
            unsafe_allow_html=True)

        st.sidebar.header(f"Perfil: {st.session_state.current_user}")
        if st.sidebar.button("Trocar Perfil / Sair"):
            auth.clear_last_user()
            st.session_state.logged_in = False
            st.session_state.current_user = None
            if 'timezone_offset' in st.session_state:
                del st.session_state.timezone_offset
            st.rerun()

        st.sidebar.header("⚙️ Configurações & Arquivos")
        up1 = st.sidebar.file_uploader("Tabela de alimentação (.csv ; latin1)", type=["csv"], key="alim")
        if up1:
            with open(config.PATH_TABELA_ALIM, "wb") as f: f.write(up1.read())
            utils.carregar_tabela_alimentacao.clear()
            st.toast("Tabela de alimentação atualizada!")
            
        up2 = st.sidebar.file_uploader("Recomendação diária (.csv ; latin1)", type=["csv"], key="rec")
        if up2:
            with open(config.PATH_RECOMEND, "wb") as f: f.write(up2.read())
            utils.carregar_recomendacao.clear()
            st.toast("Tabela de recomendação atualizada!")
        
        st.sidebar.write(":open_file_folder: Pasta de dados:", config.ASSETS_DIR.resolve())
        
        TABELA_ALIM = utils.carregar_tabela_alimentacao(config.PATH_TABELA_ALIM)
        RECOMEND = utils.carregar_recomendacao(config.PATH_RECOMEND)
        
        if TABELA_ALIM.empty: st.warning("Carregue a tabela de alimentação na barra lateral para ativar buscas por alimentos.")
        if RECOMEND.empty: st.info("Carregue a tabela de recomendação diária na barra lateral para metas de macros.")

        user_data = {}
        if st.session_state.current_user:
            username = st.session_state.current_user
            df_dados_pessoais = utils.carregar_df(utils.get_user_data_path(username, config.FILE_DADOS_PESSOAIS))
            dados_pessoais = df_dados_pessoais.iloc[0].to_dict() if not df_dados_pessoais.empty else {}
            
            user_data = {
                "dados_pessoais": dados_pessoais,
                "df_objetivo": utils.carregar_df(utils.get_user_data_path(username, config.FILE_OBJETIVO)),
                "df_evolucao": utils.carregar_df(utils.get_user_data_path(username, config.FILE_EVOLUCAO)),
                "df_log_treinos": utils.carregar_df(utils.get_user_data_path(username, config.FILE_LOG_TREINOS_SIMPLES)),
                "df_log_exercicios": utils.carregar_df(utils.get_user_data_path(username, config.FILE_LOG_EXERCICIOS)),
                "df_refeicoes": utils.carregar_df(utils.get_user_data_path(username, config.FILE_REFEICOES)),
                "df_planos_alimentares": utils.carregar_df(utils.get_user_data_path(username, config.FILE_PLANOS_ALIMENTARES)),
                "df_planos_treino": utils.carregar_df(utils.get_user_data_path(username, config.FILE_PLANOS_TREINO)),
                "df_exercicios": utils.carregar_df(utils.get_user_data_path(username, config.FILE_PLANOS_EXERCICIOS)),
                "df_macrociclos": utils.carregar_df(utils.get_user_data_path(username, config.FILE_MACROCICLOS)),
                "df_mesociclos": utils.carregar_df(utils.get_user_data_path(username, config.FILE_MESOCICLOS)),
                "df_plano_semanal": utils.carregar_df(utils.get_user_data_path(username, config.FILE_PLANO_SEMANAL))
            }

        tabs = ["Visão Geral", "Dados Pessoais", "Objetivos", "Alimentação", "Treino", "Evolução"]
        
        active_tab = option_menu(
            menu_title=None,
            options=tabs,
            icons=["speedometer2", "person-fill", "flag-fill", "apple", "fire", "graph-up"],
            menu_icon="cast",
            default_index=0,
            orientation="horizontal",
            key="active_tab",
            styles={
                "container": {"padding": "0!important", "background-color": "#262730"},
                "icon": {"color": "white", "font-size": "18px"}, 
                "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#3A3B4A"},
                "nav-link-selected": {"background-color": "#0690bb"},
            }
        )

        if active_tab == "Visão Geral":
            ui.render_visao_geral_tab(user_data, RECOMEND)
        elif active_tab == "Dados Pessoais":
            ui.render_dados_pessoais_tab(user_data)
        elif active_tab == "Objetivos":
            ui.render_objetivos_tab(user_data)
        elif active_tab == "Alimentação":
            ui.render_alimentacao_tab(user_data, TABELA_ALIM, RECOMEND)
        elif active_tab == "Treino":
            ui.render_treino_tab(user_data)
        elif active_tab == "Evolução":
            ui.render_evolucao_tab(user_data)

        st.markdown("---")
        st.markdown("© PLANO FIT app — Criado por **Flávio Dias** | [GitHub](https://github.com/flaviohasd) • [LinkedIn](https://linkedin.com/in/flaviohasd) • [E-mail](mailto:flaviohasd@hotmail.com)")
        st.caption("Versão 1.0")