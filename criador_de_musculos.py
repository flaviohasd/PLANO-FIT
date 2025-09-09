'''

ESSE ARQUIVO É EXCLUSIVAMENTE PARA A CRIAÇÃO DE ARQUIVOS .SVG, VISANDO A INCLUSÃO DE OUTROS MÚSCULOS QUE NÃO POSSUIAM IMAGEM.
ESSA FERRAMENTA AINDA ESTÁ EM CONSTRUÇÃO.

(PENDÊNCIA): Deixar a imagem do mapa muscular como background da tela de desenho.

'''
import streamlit as st
from streamlit_drawable_canvas import st_canvas
import re
from pathlib import Path
from PIL import Image
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Criador de Músculos SVG")

# --- CONSTRUÇÃO DE CAMINHOS ---
try:
    SCRIPT_DIR = Path(__file__).resolve().parent
    APP_ROOT_DIR = SCRIPT_DIR.parent.parent
    ASSETS_DIR = APP_ROOT_DIR / "app" / "assets"
except NameError:
    ASSETS_DIR = Path("assets")

PATH_DIAGRAMA_FRENTE_PNG = ASSETS_DIR / "muscle_diagram" / 'muscular_system_front.png'
PATH_DIAGRAMA_COSTAS_PNG = ASSETS_DIR / "muscle_diagram" / "muscular_system_back.png"
PATH_DIAGRAMA_FRENTE_SVG = ASSETS_DIR / "muscle_diagram" / 'muscular_system_front.svg'
PATH_DIAGRAMA_COSTAS_SVG = ASSETS_DIR / "muscle_diagram" / "muscular_system_back.svg"


# --- FUNÇÕES AUXILIARES ---
def get_svg_viewbox(svg_path: Path) -> str:
    viewbox = '0 0 600 800'
    if not svg_path.exists():
        return viewbox
    try:
        content = svg_path.read_text(encoding="utf-8")
        viewbox_match = re.search(r'viewBox="([^"]*)"', content, re.IGNORECASE)
        if viewbox_match:
            viewbox = viewbox_match.group(1)
    except Exception as e:
        st.error(f"Erro ao ler viewBox do SVG: {e}")
    return viewbox


def generate_svg_from_paths(paths_data: list, viewbox: str, color: str, width: int, height: int) -> str:
    if not paths_data:
        return ""
    path_strings = []
    for path_info in paths_data:
        if path_info.get("type") == "path":
            points = path_info.get("path", [])
            if not points:
                continue
            path_d = " ".join(
                [f"{'M' if i == 0 else 'L'} {int(p[0])} {int(p[1])}" for i, p in enumerate(points)]
            )
            if len(points) > 2:
                path_d += " Z"
            path_strings.append(f'<path d="{path_d}" fill="{color}" stroke="none" />')
    return f'''<svg width="{width}" height="{height}" viewBox="{viewbox}" xmlns="http://www.w3.org/2000/svg">
    {''.join(path_strings)}
</svg>'''.strip()


def image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


# --- INTERFACE ---
st.title("✏️ Criador de Músculos SVG")
st.markdown("""
Use esta ferramenta para criar os arquivos `.svg` para os músculos em falta.
1. Selecione a **Vista** (Frente ou Costas).
2. Desenhe o músculo usando **Polígono**.
3. Escolha a **Cor** e o **Nome do Arquivo**.
4. Clique em **Gerar e Baixar**.
""")

with st.sidebar:
    st.header("Configurações")
    vista = st.radio("1. Selecione a Vista:", ("Frente", "Costas"))
    nome_arquivo = st.text_input("2. Nome do Arquivo", "novo_musculo")
    cor_preenchimento = st.color_picker("3. Cor do Músculo", "#FF0000")

caminho_bg_png = PATH_DIAGRAMA_FRENTE_PNG if vista == "Frente" else PATH_DIAGRAMA_COSTAS_PNG
caminho_ref_svg = PATH_DIAGRAMA_FRENTE_SVG if vista == "Frente" else PATH_DIAGRAMA_COSTAS_SVG

if not caminho_bg_png.exists() or not caminho_ref_svg.exists():
    st.error("Arquivos de base não encontrados.")
    st.stop()

bg_image = Image.open(caminho_bg_png).convert("RGBA")
largura_canvas, altura_canvas = bg_image.size
viewbox_str = get_svg_viewbox(caminho_ref_svg)

# converte imagem para base64 para embutir via HTML
img_b64 = image_to_base64(caminho_bg_png)
img_datauri = f"data:image/png;base64,{img_b64}"

st.subheader(f"Vista selecionada: {vista}")

# container HTML com imagem + canvas sobreposto
st.markdown(
    f"""
    <div style="position: relative; width:{largura_canvas}px; height:{altura_canvas}px;">
        <img src="{img_datauri}" style="width:100%; height:100%; position:absolute; top:0; left:0; z-index:0;"/>
    </div>
    """,
    unsafe_allow_html=True
)

canvas_result = st_canvas(
    fill_color=f"{cor_preenchimento}80",
    stroke_width=2,
    stroke_color=cor_preenchimento,
    background_color="rgba(0,0,0,0)",  # transparente
    update_streamlit=True,
    height=altura_canvas,
    width=largura_canvas,
    drawing_mode="polygon",
    key=f"canvas_{vista}",
)

with st.sidebar:
    if st.button("4. Gerar e Baixar SVG"):
        if canvas_result.json_data and canvas_result.json_data.get("objects"):
            svg_string = generate_svg_from_paths(
                paths_data=canvas_result.json_data["objects"],
                viewbox=viewbox_str,
                color=cor_preenchimento,
                width=largura_canvas,
                height=altura_canvas
            )
            st.download_button(
                "Clique aqui para baixar!",
                data=svg_string,
                file_name=f"{nome_arquivo}.svg",
                mime="image/svg+xml"
            )
        else:
            st.error("Nenhum músculo foi desenhado.")

