# PLANO FIT 🏋️‍♂️🍽️

**Seu Assistente Pessoal Completo de Fitness e Nutrição**

PLANO FIT é uma aplicação web, construída com Streamlit, projetada para ser a ferramenta definitiva no gerenciamento da sua jornada de saúde e bem-estar. Centralize seu planejamento de treinos, monitore sua alimentação, acompanhe sua evolução corporal e atinja seus objetivos de forma inteligente e baseada em dados.

  <p align="center">
  <img src="https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExMWZwcXZqdDlnM2M1eWt0ZnZ5cThsaDA4NnhvZWZlN3BvMXdoend6bSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/5g6ijNORnMoqoJ2o1X/giphy.gif" alt="-Finja que há uma imagem motivadora aqui" width="500" />
  </p>

## ✨ Funcionalidades Principais

O PLANO FIT foi desenvolvido com uma arquitetura modular e robusta, oferecendo um conjunto completo de ferramentas:

* **📊 Dashboard de Visão Geral:**
    * Acompanhe o progresso em direção à sua meta de peso (perda, manutenção ou ganho).
    * Visualize suas metas diárias de calorias, macronutrientes e hidratação.
    * Monitore sua consistência com um *streak* de treinos e métricas de adesão semanal.
    * Visualize a periodização do seu treino (Macrociclos e Mesociclos) em um gráfico de Gantt interativo.
    * Consulte seu plano de treino para a semana atual.
    * Analise sua frequência de treinos com um *heatmap* de atividade anual.
     
      <details closed>
        <summary>Exemplo</summary>
        IMAGEM
      </details>
      
* **🍽️ Planejamento Nutricional:**
    * Registre suas refeições diárias de forma simples e rápida.
    * Busque alimentos em uma base de dados nutricionais ([TACO](https://www.cfn.org.br/wp-content/uploads/2017/03/taco_4_edicao_ampliada_e_revisada.pdf)) para adicionar às suas refeições.
    * Crie, salve e edite múltiplos **Planos Alimentares** (ex: "Dia de Treino Intenso", "Final de Semana").
    * Carregue um plano alimentar completo para o dia atual com um único clique.
    * Acompanhe em tempo real seus totais de calorias e macronutrientes, comparando com suas metas.
     
      <details closed>
        <summary>Exemplo</summary>
        IMAGEM
      </details>
      
* **🏋️‍♀️ Periodização de Treino Avançada:**
    * **Macrociclos:** Defina objetivos de longo prazo (ex: "Preparação Verão 2025").
    * **Mesociclos:** Divida seu macrociclo em fases com focos específicos (ex: "Fase de Adaptação", "Fase de Hipertrofia").
    * **Plano Semanal:** Atribua modelos de treino específicos para cada dia da semana, dentro de cada mesociclo.
     
      <details closed>
        <summary>Exemplo</summary>
        IMAGEM
      </details>
      
* **💪 Registro de Treino Detalhado:**
    * Crie **Modelos de Treino** reutilizáveis (ex: "Treino A - Peito e Tríceps", "Cardio HIIT").
    * Navegue por um vasto banco de dados com mais de 900 exercícios, com animações, instruções e diagramas musculares detalhados.
    * Registre seus treinos diários de forma guiada, com base no seu planejamento.
    * Utilize um painel de controle com **cronômetro de treino e timer de descanso** integrados.
    * Consulte o desempenho anterior para cada exercício (`kg x reps` ou `minutos`) diretamente na tela de registro para incentivar a progressão.
     
      <details closed>
        <summary>Exemplo</summary>
        IMAGEM
      </details>
      
* **📈 Acompanhamento de Evolução:**
    * Registre seu peso, medidas corporais e percentuais de gordura e músculo.
    * Visualize seu progresso através de gráficos interativos que mostram a evolução do seu peso e composição corporal ao longo do tempo.
    * Receba classificações sobre seu IMC e percentuais de gordura, ajudando a contextualizar seus resultados.
     
      <details closed>
        <summary>Exemplo</summary>
        IMAGEM
      </details>
      
* **👤 Gerenciamento de Perfis:**
    * Sistema de múltiplos perfis com proteção por senha (opcional).
    * Funcionalidade "Permanecer conectado" para um acesso rápido e fácil.
     
      <details closed>
        <summary>Exemplo</summary>
        IMAGEM
      </details>
      
## 🚀 Vantagens e Diferenciais

* **Centralização Total:** Esqueça as planilhas e múltiplos apps. O PLANO FIT integra planejamento, registro e análise em um único lugar.
* **Orientado a Dados:** Todas as metas e progressos são calculados e exibidos visualmente, permitindo que você tome decisões mais inteligentes sobre seu treino e dieta.
* **Altamente Personalizável:** A estrutura de periodização (Macro/Meso/Semanal) permite criar um planejamento de treino verdadeiramente seu e adaptado aos seus objetivos.
* **Interface Intuitiva:** Construído com Streamlit, o app oferece uma experiência de usuário limpa, rápida e interativa.
* **Estrutura de Código Robusta:** O projeto é dividido de forma clara entre lógica de negócio (`logic.py`), interface (`ui.py`), autenticação (`auth.py`), configurações (`config.py`) e utilitários (`utils.py`), facilitando a manutenção e a adição de novas funcionalidades.

## 📂 Estrutura do Projeto

A organização do código foi pensada para ser modular e escalável.

    plano-fit/
    ├── app.bat                 # Atalho para rxecutar o app (streamlit run)
    ├── src/
    │   ├── app.py              # Ponto de entrada principal da aplicação Streamlit
    │   ├── ui.py               # Módulo da Interface do Usuário (renderiza todas as telas e abas)
    │   ├── logic.py            # Módulo da Lógica de Negócio (todos os cálculos e análises)
    │   ├── auth.py             # Módulo de Autenticação e gerenciamento de usuários
    │   ├── utils.py            # Funções utilitárias (manipulação de arquivos, normalização de texto)
    │   ├── plotting.py         # Funções para a criação de gráficos com Plotly
    │   └── config.py           # Arquivo de configurações e constantes
    │
    ├── assets/
    │   ├── exercises/
    │   |   ├── exercicios.json                  # Arquivo JSON dos exercícios
    │   |   ├── 3_4_Sit-Up/
    │   |   │   ├── 0.jpg
    │   |   │   └── 1.jpg
    │   |   └── ... (outras pastas de exercícios)
    |   |
    │   └── muscle_diagram/
    │   |   ├── main/
    │   |   ├── secondary/
    │   |   ├── muscular_system_front.svg
    │   │   └── muscular_system_back.svg
    |   |
    │   └── utils
    │        ├── tabela_alimentacao.csv         # Tabela TACO
    |        └── recomendacao_diaria.csv        # Recomendações nutricionais diárias
    |
    ├── data/
    │   ├── exercises.json
    │   ├── users.csv
    │   ├── session_info.csv
    │   └── {username}/
    │       ├── dados_pessoais.csv
    │       ├── objetivo_salvo.csv
    │       ├── evolucao.csv
    │       └── ... (outros arquivos de dados específicos do usuário)
    │
    ├── requirements.txt        # Dependências do projeto
    └── README.md               # Este arquivo

## 🛠️ Como Executar Localmente

Para executar o PLANO FIT em sua máquina local, siga os passos abaixo:

1.  [**Clone o repositório:**](https://github.com/flaviohasd/plano-fit.git)
    ```bash
    git clone https://github.com/flaviohasd/plano-fit.git
    cd plano-fit
    ```


2.  **Crie e ative um ambiente virtual (recomendado):**
    ```bash
    python -m venv venv
    
    # Windows
    venv\Scripts\activate
    
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt

4.  **Execute a aplicação:**
    O ponto de entrada principal está dentro da pasta `src`.
    ```bash
    streamlit run src/app.py
    ```

5.  Abra seu navegador e acesse o endereço `http://localhost:8501`.

## 💻 Tecnologias Utilizadas

* **Linguagem:** Python 3.9+
* **Framework Web:** Streamlit
* **Manipulação de Dados:** Pandas
* **Visualização de Dados:** Plotly
* **Utilitários:** Streamlit Autorefresh

## 🙏 Agradecimentos e Créditos

Este projeto foi possível graças ao trabalho incrível de desenvolvedores e comunidades de código aberto. Um agradecimento especial a:

* **[yuhonas/free-exercise-db](https://github.com/yuhonas/free-exercise-db):** Pela abrangente base de dados de exercícios e pelas imagens/animações utilizadas na aplicação.
* **[wger-project/wger](https://github.com/wger-project/wger):** Pelos arquivos SVG dos diagramas de músculos, que permitem a visualização detalhada dos grupos musculares trabalhados.

## 👤 Autor

**Flávio Dias**

* [GitHub](https://github.com/flaviohasd)
* [LinkedIn](https://linkedin.com/in/flaviohasd)
* [E-mail](mailto:flaviohasd@hotmail.com)

## ⚠️ Aviso Importante (Disclaimer)

As informações e cálculos apresentados neste aplicativo, incluindo metas calóricas, macronutrientes, peso ideal e consumo de água, são **estimativas** baseadas em fórmulas e recomendações gerais.

O desenvolvedor deste projeto é um entusiasta de tecnologia e fitness, com formação em Engenharia Mecânica, e **não é um nutricionista, educador físico ou profissional da área da saúde.** O PLANO FIT foi originalmente criado como uma ferramenta para auxiliar na jornada de fitness **pessoal** do autor e é compartilhado com a comunidade no espírito do código aberto.

Portanto, o conteúdo aqui apresentado não deve, em hipótese alguma, substituir a orientação de um profissional qualificado. Antes de iniciar qualquer plano de dieta ou treino, **consulte sempre um médico, nutricionista e/ou educador físico.** Utilize esta ferramenta como um auxílio para sua organização, mas sempre com o acompanhamento e a validação de profissionais da saúde.
