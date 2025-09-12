# ==============================================================================
# PLANO FIT APP - FUNÇÕES UTILITÁRIAS
# ==============================================================================
# Este arquivo contém funções de propósito geral que são usadas em várias
# partes da aplicação, como manipulação de arquivos, limpeza de texto e
# carregamento de dados. Manter essas funções aqui ajuda a manter o resto
# do código mais limpo e focado em suas tarefas específicas.
# ==============================================================================

import re
import unicodedata
from pathlib import Path
import json
import pandas as pd
import streamlit as st
import config
import base64

def get_user_data_path(username: str, filename: str) -> Path:
    """
    Constrói o caminho completo para um arquivo de dados específico do usuário.
    Cria o diretório do usuário se ele não existir.
    """
    if not username:
        st.error("Erro: Nome de usuário não encontrado na sessão.")
        return None
    user_dir = config.DATA_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / filename

def limpar_texto_bruto(txt: str) -> str:
    """
    Realiza uma limpeza básica em um texto.
    """
    if pd.isna(txt): return ""
    txt = str(txt).replace("\n", " ").replace("\r", " ").replace("\t", " ")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def limpar_valor_numerico(valor) -> float:
    """
    Converte um valor para um float limpo.
    """
    if pd.isna(valor): return 0.0
    valor_limpo = str(valor).replace("*", "").strip()
    if not valor_limpo: return 0.0
    try:
        return float(valor_limpo.replace(",", "."))
    except ValueError:
        return 0.0

def normalizar_texto(txt: str) -> str:
    """
    Normaliza um texto para busca: minúsculas, sem acentos e caracteres especiais.
    """
    if pd.isna(txt): return ""
    txt = str(txt).lower().strip()
    txt = "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")
    txt = re.sub(r"[^a-z0-9\s/]", "", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt

def carregar_df(path: Path) -> pd.DataFrame:
    """
    Carrega um arquivo CSV de forma segura.
    """
    if path is None or not path.exists(): return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding='utf-8')
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo {path.name}: {e}")
        return pd.DataFrame()

def salvar_df(df: pd.DataFrame, path: Path):
    """
    Salva um DataFrame em um arquivo CSV.
    """
    if path is None:
        st.error("Erro interno: O caminho para salvar o arquivo é inválido (None).")
        return
    try:
        # Garante que o diretório pai exista antes de tentar salvar
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, encoding='utf-8')
    except Exception as e:
        st.error(f"""
        **Erro ao Salvar o Arquivo!**

        - **Arquivo:** `{path.name}`
        - **Local:** `{path.parent.resolve()}`
        - **Erro:** `{e}`

        **Verifique as permissões de escrita na pasta.**
        """)

def adicionar_registro_df(df_novo: pd.DataFrame, path: Path):
    """
    Adiciona um novo registro a um arquivo CSV existente.
    """
    if path is None:
        st.error("Erro interno: O caminho para adicionar registro é inválido (None).")
        return
    try:
        # Garante que o diretório pai exista antes de qualquer operação
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > 0:
            df_existente = pd.read_csv(path)
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
            df_final.to_csv(path, index=False)
        else:
            df_novo.to_csv(path, index=False)
    except Exception as e:
        st.error(f"Erro ao adicionar registro em {path.name}: {e}")

@st.cache_data(show_spinner="Carregando tabela de alimentos...")
def carregar_tabela_alimentacao(path: Path) -> pd.DataFrame:
    """
    Carrega e pré-processa a tabela de alimentos.
    """
    if not path.exists(): return pd.DataFrame()
    df = pd.read_csv(path, encoding="latin1", sep=";", on_bad_lines="skip")
    if config.COL_ALIMENTO in df.columns:
        df[config.COL_ALIMENTO] = df[config.COL_ALIMENTO].apply(limpar_texto_bruto)
        df[config.COL_ALIMENTO_PROC] = df[config.COL_ALIMENTO].apply(normalizar_texto)
    colunas_macros = [config.COL_PROTEINA, config.COL_CARBOIDRATO, config.COL_LIPIDEOS, config.COL_SODIO, config.COL_ENERGIA]
    for col in colunas_macros:
        if col in df.columns: df[col] = df[col].apply(limpar_valor_numerico)
    return df

@st.cache_data(show_spinner="Carregando recomendações...")
def carregar_recomendacao(path: Path) -> pd.DataFrame:
    """
    Carrega a tabela de recomendações diárias.
    """
    if not path.exists(): return pd.DataFrame()
    # CORREÇÃO: Trocado sep=";" por delim_whitespace=True para corretamente
    # ler arquivos cujas colunas são separadas por espaços ou tabs.
    return pd.read_csv(path, encoding="latin1", sep=";", on_bad_lines="skip")

@st.cache_data(show_spinner="Carregando banco de dados de exercícios...")
def carregar_banco_exercicios(path: Path) -> list:
    """
    Carrega o banco de dados de exercícios de um arquivo JSON local.
    """
    if not path.exists():
        st.error("Arquivo 'exercises.json' não encontrado na pasta 'data'.")
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Lógica para extrair a lista de exercícios, quer esteja numa chave ou não
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "exercises" in data and isinstance(data["exercises"], list):
            return data["exercises"]
            
        return []
    except json.JSONDecodeError:
        st.error("Erro ao decodificar 'exercises.json'. Verifique se o formato é um JSON válido.")
        return []
    except Exception as e:
        st.error(f"Erro inesperado ao carregar 'exercises.json': {e}")
        return []
    
def get_image_animation_html(path1: Path, path2: Path, width: int) -> str:
    """
    Gera uma string HTML para exibir um efeito de GIF animado,
    alternando entre duas imagens usando animação CSS, sem JavaScript.

    Args:
        path1 (Path): Caminho para a primeira imagem.
        path2 (Path): Caminho para a segunda imagem.
        width (int): A largura máxima da imagem a ser exibida.

    Returns:
        str: Uma string HTML contendo a imagem animada com CSS.
    """
    if not path1.exists() or not path2.exists():
        return "<p>Ficheiros de imagem não encontrados.</p>"

    def encode_image(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    img1_b64 = encode_image(path1)
    img2_b64 = encode_image(path2)

    # Cria um ID único para os elementos para evitar conflitos de estilo
    unique_id = f"anim_{hash(path1)}"

    html = f"""
    <style>
        .container_{unique_id} {{
            position: relative;
            width: 100%;
            max-width: {width}px;
        }}
        .container_{unique_id} .img_base {{
            width: 100%;
            height: auto;
            border-radius: 8px;
            display: block;
        }}
        .container_{unique_id} .img_top {{
            position: absolute;
            top: 0;
            left: 0;
            opacity: 0;
            animation: fade_{unique_id} 1s infinite;
        }}
        @keyframes fade_{unique_id} {{
            0% {{ opacity: 0; }}
            49% {{ opacity: 0; }}
            50% {{ opacity: 1; }}
            99% {{ opacity: 1; }}
            100% {{ opacity: 0; }}
        }}
    </style>
    <div class="container_{unique_id}">
        <img class="img_base" src="data:image/jpeg;base64,{img1_b64}">
        <img class="img_base img_top" src="data:image/jpeg;base64,{img2_b64}">
    </div>
    """
    return html

def render_muscle_diagram(base_svg_path: Path, primary_muscles: list, secondary_muscles: list, width: int = 150) -> str:
    """
    Gera um HTML que sobrepõe SVGs de músculos sobre uma imagem base do corpo.
    Usa CSS para posicionar as imagens umas sobre as outras.
    """
    def encode_svg_to_base64(svg_path: Path) -> str or None:
        """Lê um arquivo SVG e o codifica em Base64 para embutir em HTML."""
        if not svg_path.exists():
            return None
        with open(svg_path, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
            return f"data:image/svg+xml;base64,{encoded_string}"

    base_encoded = encode_svg_to_base64(base_svg_path)
    if not base_encoded:
        return f"<p>Imagem base não encontrada: {base_svg_path.name}</p>"

    # O container 'div' usa 'position: relative' para que as imagens internas
    # com 'position: absolute' se posicionem em relação a ele.
    html_layers = [f'<div style="position: relative; width: 100%; max-width: {width}px; height: auto;">']
    # A imagem base é a primeira camada.
    html_layers.append(f'<img src="{base_encoded}" style="width: 100%; height: auto; display: block;">')

    # Adiciona as camadas de músculos primários
    for muscle in primary_muscles:
        muscle_filename = config.MUSCLE_SVG_MAP.get(muscle.lower())
        if muscle_filename:
            muscle_path = config.PATH_GRAFICO_MUSCULOS_MAIN / muscle_filename
            muscle_encoded = encode_svg_to_base64(muscle_path)
            if muscle_encoded:
                # Cada músculo é uma imagem posicionada exatamente sobre a base.
                html_layers.append(f'<img src="{muscle_encoded}" style="position: absolute; top: 0; left: 0; width: 100%; height: auto;">')

    # Adiciona as camadas de músculos secundários com uma opacidade menor
    for muscle in secondary_muscles:
        muscle_filename = config.MUSCLE_SVG_MAP.get(muscle.lower())
        if muscle_filename:
            muscle_path = config.PATH_GRAFICO_MUSCULOS_SECONDARY / muscle_filename
            muscle_encoded = encode_svg_to_base64(muscle_path)
            if muscle_encoded:
                # O estilo 'opacity: 0.7' diferencia os músculos secundários.
                html_layers.append(f'<img src="{muscle_encoded}" style="position: absolute; top: 0; left: 0; width: 100%; height: auto; opacity: 0.7;">')

    html_layers.append('</div>')
    return "".join(html_layers)
