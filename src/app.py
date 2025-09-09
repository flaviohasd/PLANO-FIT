# ==============================================================================
# PLANO FIT APP - ARQUIVO PRINCIPAL
# ==============================================================================
import streamlit as st
import config
import utils
import ui
import auth

# --- GERENCIAMENTO DE SESSÃO E LOGIN ---
# Inicializa as variáveis de estado da sessão se ainda não existirem.
# Isso garante que a aplicação saiba se um usuário está logado ou não.
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# Tenta fazer o login automático se o usuário marcou "Permanecer conectado" na última sessão.
# Isso melhora a experiência do usuário, evitando logins repetidos.
if not st.session_state.logged_in:
    auto_login_user = auth.get_last_user()
    if auto_login_user:
        st.session_state.logged_in = True
        st.session_state.current_user = auto_login_user

# --- INTERFACE ---
# Decide qual tela mostrar: Login ou a Aplicação Principal.
if not st.session_state.logged_in:
    # A configuração da página deve ser a primeira chamada do Streamlit.
    # Layout "centered" é ideal para telas de login.
    st.set_page_config(page_title=config.APP_TITLE, layout="centered")
    ui.render_login_screen()
else:
    # --- Configuração da Página Principal ---
    # Layout "wide" aproveita melhor o espaço da tela para dashboards.
    st.set_page_config(page_title=config.APP_TITLE, layout="wide")
    st.title("🏋️‍♂️ PLANO FIT")
    st.caption("Metas, planejamento alimentar, treinos e evolução")

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
        st.cache_data.clear()
        st.toast("Tabela de alimentação atualizada!")
        
    up2 = st.sidebar.file_uploader("Recomendação diária (.csv ; latin1)", type=["csv"], key="rec")
    if up2:
        with open(config.PATH_RECOMEND, "wb") as f: f.write(up2.read())
        st.cache_data.clear()
        st.toast("Tabela de recomendação atualizada!")
    
    st.sidebar.write(":open_file_folder: Pasta de dados:", config.DATA_DIR.resolve())
    
    # --- Carregamento de Dados Globais ---
    # Carrega as tabelas que são usadas em várias partes do app.
    # O uso de @st.cache_data nessas funções em `utils.py` evita recarregamentos desnecessários.
    TABELA_ALIM = utils.carregar_tabela_alimentacao(config.PATH_TABELA_ALIM)
    RECOMEND = utils.carregar_recomendacao(config.PATH_RECOMEND)
    
    # Avisos para o usuário caso os arquivos de dados principais não estejam carregados.
    if TABELA_ALIM.empty: st.warning("Carregue a tabela de alimentação na barra lateral para ativar buscas por alimentos.")
    if RECOMEND.empty: st.info("Carregue a tabela de recomendação diária na barra lateral para metas de macros.")

    # --- [OTIMIZAÇÃO] Carregamento Centralizado de Dados do Usuário ---
    # Carrega todos os dataframes específicos do usuário aqui, uma única vez.
    # Isso evita múltiplas leituras de disco nas funções de renderização das abas.
    user_data = {}
    if st.session_state.current_user:
        username = st.session_state.current_user
        
        # Carrega os dados pessoais e transforma em um dicionário para fácil acesso.
        df_dados_pessoais = utils.carregar_df(utils.get_user_data_path(username, config.FILE_DADOS_PESSOAIS))
        dados_pessoais = df_dados_pessoais.iloc[0].to_dict() if not df_dados_pessoais.empty else {}
        
        # Agrupa todos os outros dataframes em um dicionário para passar para as funções de UI.
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

    # --- Renderização das Abas ---
    # Cria as abas da interface principal.
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["✨ Visão Geral", "👤 Dados pessoais", "🎯 Objetivos", "🍽️ Alimentação", "🏋️‍♀️ Treino", "📈 Evolução"])

    # Renderiza o conteúdo de cada aba, passando os dados já carregados.
    with tab1:
        ui.render_visao_geral_tab(user_data, RECOMEND)
    with tab2:
        ui.render_dados_pessoais_tab(user_data)
    with tab3:
        ui.render_objetivos_tab(user_data)
    with tab4:
        ui.render_alimentacao_tab(user_data, TABELA_ALIM, RECOMEND)
    with tab5:
        ui.render_treino_tab(user_data)
    with tab6:
        ui.render_evolucao_tab(user_data)

    # --- Rodapé ---
    st.markdown("---")
    st.markdown("© PLANO FIT app — Criado por **Flávio Dias** | [GitHub](https://github.com/flaviohasd) • [LinkedIn](https://linkedin.com/in/flaviohasd) • [E-mail](mailto:flaviohasd@hotmail.com)")
    st.caption("Versão 1.0 | Todos os direitos reservados")