# ==============================================================================
# PLANO FIT APP - ARQUIVO PRINCIPAL
# ==============================================================================
import streamlit as st
import config
import utils
import ui
import auth

# --- GERENCIAMENTO DE SESSÃO E LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# Tenta login automático se o usuário marcou "Permanecer conectado"
if not st.session_state.logged_in:
    auto_login_user = auth.get_last_user()
    if auto_login_user:
        st.session_state.logged_in = True
        st.session_state.current_user = auto_login_user

# --- INTERFACE ---
if not st.session_state.logged_in:
    # A configuração da página deve ser a primeira chamada do Streamlit
    st.set_page_config(page_title=config.APP_TITLE, layout="centered")
    ui.render_login_screen()
else:
    # --- Configuração da Página Principal ---
    st.set_page_config(page_title=config.APP_TITLE, layout="wide")
    st.title("🏋️‍♂️ PLANO FIT")
    st.caption("Metas, planejamento alimentar, treinos e evolução")

    # --- Sidebar ---
    st.sidebar.header(f"Perfil: {st.session_state.current_user}")
    if st.sidebar.button("Trocar Perfil / Sair"):
        auth.clear_last_user()
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()

    st.sidebar.header("⚙️ Configurações & Arquivos")
    up1 = st.sidebar.file_uploader("Tabela de alimentação (.csv ; latin1)", type=["csv"], key="alim")
    if up1:
        with open(config.PATH_TABELA_ALIM, "wb") as f: f.write(up1.read())
        st.cache_data.clear()
    up2 = st.sidebar.file_uploader("Recomendação diária (.csv ; latin1)", type=["csv"], key="rec")
    if up2:
        with open(config.PATH_RECOMEND, "wb") as f: f.write(up2.read())
        st.cache_data.clear()
    
    st.sidebar.write(":open_file_folder: Pasta de dados:", config.DATA_DIR.resolve())
    TABELA_ALIM = utils.carregar_tabela_alimentacao(config.PATH_TABELA_ALIM)
    RECOMEND = utils.carregar_recomendacao(config.PATH_RECOMEND)
    if TABELA_ALIM.empty: st.warning("Carregue a tabela de alimentação na barra lateral para ativar buscas por alimentos.")
    if RECOMEND.empty: st.info("Carregue a tabela de recomendação diária na barra lateral para metas de macros.")

    # --- Carregamento de Dados Específicos do Usuário ---
    dados_pessoais = {}
    if st.session_state.current_user:
        df_dados_atuais = utils.carregar_df(utils.get_user_data_path(st.session_state.current_user, config.FILE_DADOS_PESSOAIS))
        dados_pessoais = df_dados_atuais.iloc[0].to_dict() if not df_dados_atuais.empty else {}

    # --- Renderização das Abas ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["✨ Visão Geral", "👤 Dados pessoais", "🎯 Objetivos & metas", "🍽️ Alimentação", "🏋️‍♀️ Treino", "📈 Evolução"])

    with tab1:
        ui.render_visao_geral_tab(dados_pessoais, RECOMEND)
    with tab2:
        ui.render_dados_pessoais_tab(dados_pessoais)
    with tab3:
        ui.render_objetivos_tab(dados_pessoais)
    with tab4:
        ui.render_alimentacao_tab(dados_pessoais, TABELA_ALIM, RECOMEND)
    with tab5:
        ui.render_treino_tab(dados_pessoais)
    with tab6:
        ui.render_evolucao_tab(dados_pessoais)

    # --- Rodapé ---
    st.markdown("---")
    st.markdown("© PLANO FIT app — Criado por **Flávio Dias** | [GitHub](https://github.com/flaviohasd) • [LinkedIn](https://linkedin.com/in/flaviohasd) • [E-mail](mailto:flaviohasd@hotmail.com)")
    st.caption("Versão 5.0 (Modular com Login) | Todos os direitos reservados")