import streamlit as st
import pandas as pd
import requests

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E ESTILO CSS
# ==========================================
st.set_page_config(page_title="NBA Elite Analytics", layout="wide")
st.title("🏀 NBA - Análise Estatística por Jogador")

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

# Mapeamento oficial das siglas dos times na ESPN
TEAMS_ESPN = {
    "Atlanta Hawks": "atl", "Boston Celtics": "bos", "Brooklyn Nets": "bkn",
    "Charlotte Hornets": "cha", "Chicago Bulls": "chi", "Cleveland Cavaliers": "cle",
    "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Detroit Pistons": "det",
    "Golden State Warriors": "gsw", "Houston Rockets": "hou", "Indiana Pacers": "ind",
    "LA Clippers": "lac", "Los Angeles Lakers": "lal", "Memphis Grizzlies": "mem",
    "Miami Heat": "mia", "Milwaukee Bucks": "mil", "Minnesota Timberwolves": "min",
    "New Orleans Pelicans": "nop", "New York Knicks": "nyk", "Oklahoma City Thunder": "okc",
    "Orlando Magic": "orl", "Philadelphia 76ers": "phi", "Phoenix Suns": "phx",
    "Portland Trail Blazers": "por", "Sacramento Kings": "sac", "San Antonio Spurs": "sas",
    "Toronto Raptors": "tor", "Utah Jazz": "uta", "Washington Wizards": "was"
}

# Dicionário para formatar os nomes dos adversários exatamente como no print original
TEAM_NAMES_MAP = {
    'SAC': 'Kings', 'MIA': 'Heat', 'TOR': 'Raptors', 'GS': 'Warriors', 'GSW': 'Warriors',
    'LAC': 'Clippers', 'POR': 'Trail Blazers', 'UTAH': 'Jazz', 'UTA': 'Jazz', 'DEN': 'Nuggets',
    'ATL': 'Hawks', 'BOS': 'Celtics', 'BKN': 'Nets', 'CHA': 'Hornets', 'CHI': 'Bulls',
    'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DET': 'Pistons', 'HOU': 'Rockets', 'IND': 'Pacers',
    'LAL': 'Lakers', 'MEM': 'Grizzlies', 'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans',
    'NYK': 'Knicks', 'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHX': 'Suns',
    'SAS': 'Spurs', 'WAS': 'Wizards'
}

# ==========================================
# FUNÇÕES DE BUSCA DE DADOS (ESPN API)
# ==========================================
@st.cache_data(ttl=3600)
def obter_elenco_time(team_abbr):
    """Busca o elenco do time selecionado."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_abbr}/roster"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            jogadores = []
            for athlete in data.get('athletes', []):
                jogadores.append({
                    'PLAYER': athlete.get('fullName'),
                    'ESPN_ID': athlete.get('id')
                })
            df = pd.DataFrame(jogadores)
            if not df.empty:
                return df.sort_values(by="PLAYER")
    except Exception:
        pass
    return pd.DataFrame(columns=['PLAYER', 'ESPN_ID'])

@st.cache_data(ttl=1800)
def obter_gamelog_correto(espn_id):
    """Busca os estatísticas jogo a jogo e ajusta a ordem exata das colunas."""
    url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{espn_id}/gamelog"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            events_dict = data.get('events', {})
            season_types = data.get('seasonTypes', [])
            
            logs = []
            for stype in season_types:
                for category in stype.get('categories', []):
                    for event in category.get('events', []):
                        event_id = str(event.get('eventId'))
                        event_info = events_dict.get(event_id, {})
                        
                        # Extrai a sigla do adversário e converte para o nome legível
                        raw_opponent = event_info.get('opponent', {}).get('abbreviation', '')
                        nome_adversario = TEAM_NAMES_MAP.get(raw_opponent, raw_opponent)
                        
                        # Define Mando de Campo: '@' para jogo fora, 'x' para jogo em casa
                        home_away_flag = event_info.get('homeAway', '')
                        simbolo_mando = '@' if home_away_flag == 'away' else 'x'
                        
                        # Formata a Data (Ex: 05/11)
                        game_date_str = event_info.get('gameDate', '')
                        if game_date_str:
                            data_fmt = pd.to_datetime(game_date_str).strftime('%d/%m')
                        else:
                            data_fmt = ""
                        
                        stats = event.get('stats', [])
                        if stats and len(stats) >= 13:
                            logs.append({
                                'Jogo': f"{data_fmt} {simbolo_mando} {nome_adversario}".strip(),
                                'MIN': stats[0],
                                'PTS': stats[13] if len(stats) > 13 else stats[1],
                                'AQ': stats[1],    # Field Goals (FG)
                                '3PT': stats[3],   # 3-Point (3PT)
                                'LL': stats[5],    # Free Throws (FT)
                                'REB': stats[7],   # Total Rebounds (REB)
                                'AST': stats[8],   # Assists (AST)
                                'RBD': stats[10],  # Steals (Roubos de Bola) - Corrigido
                                'BLQ': stats[9],   # Blocks (Bloqueios/Tocos) - Corrigido
                                'BP': stats[11]    # Turnovers (Bolas Perdidas) - Corrigido
                            })
            return pd.DataFrame(logs)
    except Exception:
        pass
    return pd.DataFrame()

# ==========================================
# SIDEBAR - SELEÇÃO DE FILTROS
# ==========================================
st.sidebar.header("🔍 Seleção de Filtros")

# 1. Seleção do Time
time_selecionado = st.sidebar.selectbox("Escolha o Time:", list(TEAMS_ESPN.keys()))
team_abbr = TEAMS_ESPN[time_selecionado]

# 2. Seleção do Jogador
df_elenco = obter_elenco_time(team_abbr)

if not df_elenco.empty:
    jogador_selecionado = st.sidebar.selectbox("Escolha o Jogador:", df_elenco['PLAYER'].values)
    espn_id = df_elenco[df_elenco['PLAYER'] == jogador_selecionado]['ESPN_ID'].values[0]
else:
    st.sidebar.warning("Carregando elenco...")
    st.stop()

# 3. Seleção da Temporada
temporada = st.sidebar.selectbox("Temporada:", ["2026-27", "2025-26", "2024-25"], index=0)

# ==========================================
# QUADRO PRINCIPAL
# ==========================================
st.subheader(f"📊 Estatísticas: {jogador_selecionado} ({time_selecionado}) - Temporada {temporada}")

try:
    with st.spinner("Buscando estatísticas atualizadas da NBA..."):
        df_display = obter_gamelog_correto(espn_id)
    
    if not df_display.empty:
        # Converter estatísticas para inteiros para calcular as médias no topo
        pts_num = pd.to_numeric(df_display['PTS'], errors='coerce').fillna(0)
        reb_num = pd.to_numeric(df_display['REB'], errors='coerce').fillna(0)
        ast_num = pd.to_numeric(df_display['AST'], errors='coerce').fillna(0)
        min_num = pd.to_numeric(df_display['MIN'], errors='coerce').fillna(0)
        
        # Cards de Médias no Topo
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Média PTS", round(pts_num.mean(), 1))
        col2.metric("Média REB", round(reb_num.mean(), 1))
        col3.metric("Média AST", round(ast_num.mean(), 1))
        col4.metric("Total de Jogos", len(df_display))
        col5.metric("Média Minutos", round(min_num.mean(), 1))
        
        st.divider()
        
        # Renderização da Tabela HTML Centralizada
        html_table = df_display.to_html(classes='nba-table', index=False, escape=False)
        st.markdown(f'<div class="tabela-container">{html_table}</div>', unsafe_allow_html=True)
    else:
        st.warning(f"Nenhuma partida encontrada para {jogador_selecionado} na temporada selecionada.")

except Exception as e:
    st.error(f"Erro ao processar estatísticas: {e}")
