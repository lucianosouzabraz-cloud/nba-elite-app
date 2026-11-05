import streamlit as st
import pandas as pd
import time
from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import playergamelog, commonteamroster

# ==========================================
# CONFIGURAÇÃO DE HEADERS ANTI-BLOQUEIO
# ==========================================
CUSTOM_HEADERS = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com'
}

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="NBA Elite Analytics", layout="wide")
st.title("🏀 NBA - Análise Estatística por Jogador")

# Estilo CSS para alinhar e compactar a tabela HTML igual ao modelo desejado
st.markdown("""
    <style>
    .tabela-container {
        display: flex;
        justify-content: flex-start;
        margin-top: 10px;
    }
    .nba-table {
        border-collapse: collapse;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 14px;
        color: #333;
        background-color: #ffffff;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .nba-table th {
        background-color: #f8f9fa;
        color: #6c757d;
        font-weight: 600;
        padding: 10px 16px;
        text-align: center !important;
        border-bottom: 2px solid #dee2e6;
        white-space: nowrap;
    }
    .nba-table td {
        padding: 10px 16px;
        text-align: center !important;
        border-bottom: 1px solid #edf2f7;
        white-space: nowrap;
    }
    .nba-table tr:hover {
        background-color: #f1f5f9;
    }
    .nba-table td:first-child, .nba-table th:first-child {
        text-align: left !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# FUNÇÕES DE BUSCA SEBURAS (COM RETRY)
# ==========================================
@st.cache_data(ttl=86400)
def obter_todos_times():
    """Retorna os 30 times oficiais da NBA."""
    nba_teams = teams.get_teams()
    df_teams = pd.DataFrame(nba_teams)
    return df_teams.sort_values(by="full_name")

@st.cache_data(ttl=86400)
def obter_todos_jogadores_ativos():
    """Busca estaticamente todos os jogadores ativos da NBA sem fazer requisição externa instável."""
    active_players = players.get_active_players()
    df = pd.DataFrame(active_players)
    df = df.rename(columns={'full_name': 'PLAYER', 'id': 'PLAYER_ID'})
    return df.sort_values(by="PLAYER")

@st.cache_data(ttl=1800)
def obter_logs_jogador_com_retry(player_id, season="2026-27"):
    """Busca os logs do jogador com 3 tentativas para evitar timeouts temporários."""
    for tentativa in range(3):
        try:
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season,
                headers=CUSTOM_HEADERS,
                timeout=30
            ).get_data_frames()[0]
            return gamelog
        except Exception:
            time.sleep(1.5)
    return pd.DataFrame()

# ==========================================
# SIDEBAR - SELEÇÃO DE FILTROS
# ==========================================
st.sidebar.header("🔍 Seleção de Filtros")

# 1. Seleção do Time
df_times = obter_todos_times()
time_selecionado = st.sidebar.selectbox("Escolha o Time:", df_times['full_name'].values)

# 2. Seleção do Jogador (Busca ativa garantida sem travamento)
df_jogadores = obter_todos_jogadores_ativos()
jogador_selecionado = st.sidebar.selectbox("Escolha o Jogador:", df_jogadores['PLAYER'].values)
player_id = df_jogadores[df_jogadores['PLAYER'] == jogador_selecionado]['PLAYER_ID'].values[0]

# 3. Seleção da Temporada
temporada = st.sidebar.selectbox(
    "Temporada:", 
    ["2026-27", "2025-26", "2024-25", "2023-24"], 
    index=0
)

# ==========================================
# QUADRO PRINCIPAL - PROCESSAMENTO E TABELA
# ==========================================
st.subheader(f"📊 Estatísticas: {jogador_selecionado} - Temporada {temporada}")

try:
    with st.spinner("Buscando estatísticas atualizadas da NBA..."):
        df_raw = obter_logs_jogador_com_retry(player_id, season=temporada)
    
    if not df_raw.empty:
        df_display = pd.DataFrame()
        
        # Jogo (Ex: 05/11 @ SAC ou vs MIA)
        df_display['Jogo'] = pd.to_datetime(df_raw['GAME_DATE']).dt.strftime('%d/%m') + " " + df_raw['MATCHUP']
        
        # Minutos e Pontos
        df_display['MIN'] = df_raw['MIN']
        df_display['PTS'] = df_raw['PTS']
        
        # Arremessos (ex: 11-23)
        df_display['AQ'] = df_raw['FGM'].astype(str) + "-" + df_raw['FGA'].astype(str)
        df_display['3PT'] = df_raw['FG3M'].astype(str) + "-" + df_raw['FG3A'].astype(str)
        df_display['LL'] = df_raw['FTM'].astype(str) + "-" + df_raw['FTA'].astype(str)
        
        # Rebotes, Assistências, Roubos, Bloqueios e Turnovers
        df_display['REB'] = df_raw['REB']
        df_display['AST'] = df_raw['AST']
        df_display['RBD'] = df_raw['STL']  # Roubos de Bola (Steals)
        df_display['BLQ'] = df_raw['BLK']  # Bloqueios/Tocos (Blocks)
        df_display['BP'] = df_raw['TOV']   # Bolas Perdidas/Turnovers
        
        # Cards de Médias no Topo
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Média PTS", round(df_raw['PTS'].mean(), 1))
        col2.metric("Média REB", round(df_raw['REB'].mean(), 1))
        col3.metric("Média AST", round(df_raw['AST'].mean(), 1))
        col4.metric("Média 3PT Convertidos", round(df_raw['FG3M'].mean(), 1))
        col5.metric("Média Minutos", round(df_raw['MIN'].mean(), 1))
        
        st.divider()
        
        # Renderização da Tabela via HTML Customizado (Centralizado e Compacto)
        html_table = df_display.to_html(classes='nba-table', index=False, escape=False)
        st.markdown(f'<div class="tabela-container">{html_table}</div>', unsafe_allow_html=True)
        
    else:
        st.warning(f"Não foi possível carregar os dados ou o jogador {jogador_selecionado} ainda não jogou na temporada {temporada}.")

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
