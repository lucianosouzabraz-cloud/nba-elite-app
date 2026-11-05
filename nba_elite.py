import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, playergamelog

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="NBA Elite Analytics", layout="wide")
st.title("🏀 NBA - Análise Estatística por Jogador")

# Estilo CSS para centralizar e compactar a tabela HTML no formato do print
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
# FUNÇÕES DE CACHE E BUSCA DE DADOS
# ==========================================
@st.cache_data(ttl=86400)
def obter_todos_times():
    """Retorna a lista de times da NBA organizada por nome."""
    nba_teams = teams.get_teams()
    df_teams = pd.DataFrame(nba_teams)
    return df_teams.sort_values(by="full_name")

@st.cache_data(ttl=3600)
def obter_elenco_time(team_id):
    """Retorna os jogadores do time selecionado."""
    roster = commonteamroster.CommonTeamRoster(team_id=team_id).get_data_frames()[0]
    return roster[['PLAYER', 'PLAYER_ID']].sort_values(by="PLAYER")

@st.cache_data(ttl=1800)
def obter_logs_jogador(player_id, season="2026-27"):
    """Busca o histórico de jogos do jogador na temporada especificada."""
    gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season).get_data_frames()[0]
    return gamelog

# ==========================================
# SIDEBAR - SELEÇÃO DE FILTROS
# ==========================================
st.sidebar.header("🔍 Seleção de Filtros")

# 1. Seleção do Time
df_times = obter_todos_times()
time_selecionado = st.sidebar.selectbox("Escolha o Time:", df_times['full_name'].values)
team_id = df_times[df_times['full_name'] == time_selecionado]['id'].values[0]

# 2. Seleção do Jogador (Filtrado pelo time)
df_elenco = obter_elenco_time(team_id)
jogador_selecionado = st.sidebar.selectbox("Escolha o Jogador:", df_elenco['PLAYER'].values)
player_id = df_elenco[df_elenco['PLAYER'] == jogador_selecionado]['PLAYER_ID'].values[0]

# 3. Seleção da Temporada
temporada = st.sidebar.selectbox(
    "Temporada:", 
    ["2026-27", "2025-26", "2024-25", "2023-24"], 
    index=0
)

# ==========================================
# QUADRO PRINCIPAL - PROCESSAMENTO E TABELA
# ==========================================
st.subheader(f"📊 Estatísticas: {jogador_selecionado} ({time_selecionado}) - Temporada {temporada}")

try:
    with st.spinner("Buscando estatísticas atualizadas da NBA..."):
        df_raw = obter_logs_jogador(player_id, season=temporada)
    
    if not df_raw.empty:
        df_display = pd.DataFrame()
        
        # Jogo (Ex: 05/11 @ Kings ou x Heat)
        df_display['Jogo'] = pd.to_datetime(df_raw['GAME_DATE']).dt.strftime('%d/%m') + " " + df_raw['MATCHUP']
        
        # Minutos e Pontos
        df_display['MIN'] = df_raw['MIN']
        df_display['PTS'] = df_raw['PTS']
        
        # Arremessos no formato "Convertidos-Tentados" (ex: 11-23)
        df_display['AQ'] = df_raw['FGM'].astype(str) + "-" + df_raw['FGA'].astype(str)
        df_display['3PT'] = df_raw['FG3M'].astype(str) + "-" + df_raw['FG3A'].astype(str)
        df_display['LL'] = df_raw['FTM'].astype(str) + "-" + df_raw['FTA'].astype(str)
        
        # Rebotes, Assistências, Roubos, Bloqueios e Turnovers
        df_display['REB'] = df_raw['REB']
        df_display['AST'] = df_raw['AST']
        df_display['RBD'] = df_raw['STL']  # Roubos de Bola
        df_display['BLQ'] = df_raw['BLK']  # Bloqueios/Tocos
        df_display['BP'] = df_raw['TOV']   # Turnovers/Erros
        
        # Cards de Médias no Topo
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Média PTS", round(df_raw['PTS'].mean(), 1))
        col2.metric("Média REB", round(df_raw['REB'].mean(), 1))
        col3.metric("Média AST", round(df_raw['AST'].mean(), 1))
        col4.metric("Média 3PT Convertidos", round(df_raw['FG3M'].mean(), 1))
        col5.metric("Média Minutos", round(df_raw['MIN'].mean(), 1))
        
        st.divider()
        
        # Renderização da Tabela HTML (Centralizado e Compacto)
        html_table = df_display.to_html(classes='nba-table', index=False, escape=False)
        st.markdown(f'<div class="tabela-container">{html_table}</div>', unsafe_allow_html=True)
        
    else:
        st.warning(f"O jogador {jogador_selecionado} ainda não possui partidas registradas na temporada {temporada}.")

except Exception as e:
    st.error(f"Erro ao carregar dados da NBA: {e}")
