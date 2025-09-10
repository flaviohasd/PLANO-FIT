# ==============================================================================
# PLANO FIT APP - ARQUIVO PRINCIPAL
# ==============================================================================

import streamlit as st
from streamlit_option_menu import option_menu # Importa a nova biblioteca
import config
import utils
import os
import ui
import auth
import base64

# A configuração da página deve ser a primeira chamada do Streamlit e executada apenas uma vez.
st.set_page_config(page_title=config.APP_TITLE, layout="wide")

# --- GERENCIAMENTO DE SESSÃO E LOGIN ---
# Inicializa as variáveis de estado da sessão se ainda não existirem.
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# Tenta fazer o login automático se o usuário marcou "Permanecer conectado" na última sessão.
if not st.session_state.logged_in:
    auto_login_user = auth.get_last_user()
    if auto_login_user:
        st.session_state.logged_in = True
        st.session_state.current_user = auto_login_user
        st.rerun()

# --- INTERFACE ---


# Background

def set_background(image_path):
    '''
    A function to unpack an image from a file and set as a background.
    The file should be in the specified path relative to the script.
    '''
    main_bg_ext = "png" # Assumindo que a extensão é sempre PNG. Se puder variar, você precisaria extrair do image_path.
    current_dir = os.path.dirname(__file__) # Obtém o diretório do script atual (app/src)
    full_image_path = os.path.join(current_dir, image_path) # Constrói o caminho completo

    try:
        with open(full_image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        st.error(f"Erro: Imagem não encontrada no caminho: {full_image_path}. Verifique se o caminho está correto.")
        return

    # Aplica o CSS com a imagem codificada
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url(data:image/{main_bg_ext};base64,{encoded_string});
            background-size: cover;
            background-position: center; /* Opcional: Centraliza a imagem no plano de fundo */
            background-repeat: no-repeat; /* Opcional: Evita que a imagem se repita */
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
# set_background(os.path.join("..", "assets", "images", "background.png"))

# Decide qual tela mostrar: Login ou a Aplicação Principal.
if not st.session_state.logged_in:
    ui.render_login_screen()
else:
    # --- Configuração da Página Principal ---
    # Centralizando o título
    st.markdown(
        "<h1 style='text-align: center;'>🏋️‍♂️ PLANO FIT</h1>",
        unsafe_allow_html=True)

    # Centralizando o caption
    st.markdown(
        "<p style='text-align: center;'>Metas, planejamento alimentar, treinos e evolução</p>",
        unsafe_allow_html=True)

    # --- Sidebar (Barra Lateral) ---
    st.sidebar.header(f"Perfil: {st.session_state.current_user}")
    if st.sidebar.button("Trocar Perfil / Sair"):
        auth.clear_last_user()  # Limpa a sessão "permanecer conectado"
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()  # Reinicia o script para voltar à tela de login

    st.sidebar.header("⚙️ Configurações & Arquivos")
    # File uploaders para os arquivos de dados globais.
    up1 = st.sidebar.file_uploader("Tabela de alimentação (.csv ; latin1)", type=["csv"], key="alim")
    if up1:
        # Salva o arquivo enviado e limpa o cache para forçar o reload dos dados.
        with open(config.PATH_TABELA_ALIM, "wb") as f: f.write(up1.read())
        utils.carregar_tabela_alimentacao.clear()
        st.toast("Tabela de alimentação atualizada!")
        
    up2 = st.sidebar.file_uploader("Recomendação diária (.csv ; latin1)", type=["csv"], key="rec")
    if up2:
        with open(config.PATH_RECOMEND, "wb") as f: f.write(up2.read())
        utils.carregar_recomendacao.clear()
        st.toast("Tabela de recomendação atualizada!")
    
    st.sidebar.write(":open_file_folder: Pasta de dados:", config.DATA_DIR.resolve())
    
    # --- Carregamento de Dados Globais ---
    TABELA_ALIM = utils.carregar_tabela_alimentacao(config.PATH_TABELA_ALIM)
    RECOMEND = utils.carregar_recomendacao(config.PATH_RECOMEND)
    
    if TABELA_ALIM.empty: st.warning("Carregue a tabela de alimentação na barra lateral para ativar buscas por alimentos.")
    if RECOMEND.empty: st.info("Carregue a tabela de recomendação diária na barra lateral para metas de macros.")

    # --- Carregamento Centralizado de Dados do Usuário ---
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

    # --- Renderização das Abas (usando streamlit-option-menu) ---
    
    # Define as opções das abas
    active_tab = option_menu(
        menu_title=None,
        options=["Visão Geral", "Dados Pessoais", "Objetivos", "Alimentação", "Treino", "Evolução"],
        icons=["speedometer2", "person-fill", "flag-fill", "apple", "fire", "graph-up"], # Ícones corrigidos
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

    # Renderiza o conteúdo da aba selecionada
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

    # --- Rodapé ---
    st.markdown("---")
    st.markdown("© PLANO FIT app — Criado por **Flávio Dias** | [GitHub](https://github.com/flaviohasd) • [LinkedIn](https://linkedin.com/in/flaviohasd) • [E-mail](mailto:flaviohasd@hotmail.com)")
    st.caption("Versão 1.0")