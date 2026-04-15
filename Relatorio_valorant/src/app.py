import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

# Em caso de estar rodando localmente descomente as linhas abaixo

# from dotenv import load_dotenv
# import os

# load_dotenv()

# USER = os.getenv("user")
# PASSWORD = os.getenv("password")
# HOST = os.getenv("host")
# PORT = os.getenv("port")
# DBNAME = os.getenv("dbname")

# connection_url = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

# Configuração da Página
st.set_page_config(page_title="Valorant Pro Stats", layout="wide")

# Conexão com o Banco (A mesma que usamos no ETL)
@st.cache_resource # Isso evita que o app reconecte ao banco a cada clique
def get_connection():
    connection_url_deploy = st.secrets["postgres"]["url"]
    return create_engine(connection_url_deploy, connect_args={'client_encoding': 'utf8'})

engine = get_connection()

# 1. Carregamento de Dados
@st.cache_data
def load_data():
    query = "SELECT * FROM valorant_regional_status"
    df = pd.read_sql(query, engine)
    
    # Separando a coluna de Clutch 'CL' (ganhos/jogados)
    if 'CL' in df.columns:
        # Pega a string, remove espaços e divide no caractere '/'
        clutch_split = df['CL'].astype(str).str.strip().str.split('/', expand=True)
        if clutch_split.shape[1] >= 2:
            df['clutch_ganhos'] = pd.to_numeric(clutch_split[0], errors='coerce').fillna(0)
            df['clutch_jogados'] = pd.to_numeric(clutch_split[1], errors='coerce').fillna(0)
            # Calcula os clutchs perdidos para gerar o gráfico sobreposto
            df['clutch_perdidos'] = (df['clutch_jogados'] - df['clutch_ganhos']).clip(lower=0)
            
    return df

df = load_data()

# --- SIDEBAR (FILTROS) ---
st.sidebar.header("Filtros")

# 1. Filtro de Ano
years = df['year'].unique().tolist()
selected_year = st.sidebar.selectbox("Selecione o Ano", sorted(years, reverse=True))

# 2. Filtro de Competição
tournaments = df[df['year'] == selected_year]['tournament_id'].unique().tolist()
selected_tournament = st.sidebar.selectbox("Selecione a Competição", sorted(tournaments))

# 3. Filtro de Região
regions = df[(df['year'] == selected_year) & (df['tournament_id'] == selected_tournament)]['region'].unique().tolist()
selected_region = st.sidebar.selectbox("Selecione a Região", sorted(regions))

# 4. Filtro de Equipe
teams_available = df[
    (df['year'] == selected_year) & 
    (df['tournament_id'] == selected_tournament) & 
    (df['region'] == selected_region)
]['Team'].unique().tolist()
selected_team = st.sidebar.selectbox("Selecione a Equipe", sorted(teams_available))

# Filtragem Final do DF
df_filtered = df[
    (df['year'] == selected_year) & 
    (df['tournament_id'] == selected_tournament) & 
    (df['region'] == selected_region) & 
    (df['Team'] == selected_team)
]

# --- TELA PRINCIPAL ---
st.title(f"📊 Stats: {selected_team} ({selected_region.upper()})")

# 2. CARDS DE KPI
col1, col2, col3 = st.columns(3)

with col1:
    avg_rating = df_filtered['R2.0'].mean()
    st.metric("Média Rating", f"{avg_rating:.2f}")

with col2:
    diff_fk_fd = df_filtered['FK'].sum() - df_filtered['FD'].sum()
    st.metric("Diferença de First Kill e First Death", f"{diff_fk_fd:.0f}")

with col3:
    total_clutchs = df_filtered['clutch_jogados'].sum()
    st.metric("Total clutch", int(total_clutchs))


# 3. GRÁFICOS (Plotly)
st.divider()
c1, c2 = st.columns(2)

with c1:
    # st.subheader("Performance por Jogador (Clutchs)")
    st.subheader("Performance em Clutchs")

    if 'clutch_ganhos' in df_filtered.columns and 'clutch_perdidos' in df_filtered.columns:
        df_clutch_plot = df_filtered[['Player', 'clutch_ganhos', 'clutch_perdidos']].rename(
            columns={'clutch_ganhos': 'Ganhos', 'clutch_perdidos': 'Perdidos'}
        )
        
        fig_clutch = px.bar(
            df_clutch_plot,
            x='Player',
            y=['Ganhos', 'Perdidos'],
            template="plotly_dark",
            barmode='stack',
            labels={'value': 'Quantidade', 'variable': 'Resultado do Clutch', 'Player': 'Jogador'},
            color_discrete_map={'Ganhos': '#198754', 'Perdidos': '#dc3545'} # Cores mais agradáveis (Verde e Vermelho)
        )
        fig_clutch.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_clutch, use_container_width=True)
    else:
        st.warning("Dados não encontrados para plotar os Clutchs (Coluna 'CL').")

with c2:
    st.subheader("Relação Rating vs ACS")
    fig_kd = px.scatter(df_filtered, x='R2.0', y='ACS', text='Player', size='ACS', template="plotly_dark")
    st.plotly_chart(fig_kd, use_container_width=True)

# 5. TABELA DE DADOS
st.divider()
st.subheader(f"🏆 Top 10 Jogadores - {selected_region.upper()}")

# Filtramos os dados considerando apenas Ano, Torneio e Região
# Ignoramos o 'selected_team' para ver quem são os melhores da região toda
df_top10 = df[
    (df['year'] == selected_year) & 
    (df['tournament_id'] == selected_tournament) & 
    (df['region'] == selected_region)
]

# Ordenamos pelo Rating (R2.0) de forma decrescente e pegamos os 10 primeiros
top_10_final = df_top10.sort_values(by='R2.0', ascending=False).head(10)

# Selecionamos as colunas solicitadas
top_10_display = top_10_final[['Player', 'Team', 'R2.0', 'ACS']]

# Resetamos o index para começar de 1 a 10 (Ranking)
top_10_display.index = range(1, 11)

# Exibição com destaque
st.dataframe(
    top_10_display, 
    use_container_width=True,
    hide_index=True,
    column_config={
        "R2.0": st.column_config.NumberColumn("Rating", format="%.2f"),
        "ACS": st.column_config.NumberColumn("ACS", format="%.1f")
    }

)