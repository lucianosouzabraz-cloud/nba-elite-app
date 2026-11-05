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

# ==========================================
# FUNÇÕES DE BUSCA DE DADOS
# ==========================================
@st.cache_data(ttl=3600)
def obter_elenco_time(team_abbr):
    """Retorna os jogadores do time selecionado."""
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
def obter_gamelog_preciso(espn_id):
    """Busca os estatísticas jogo a jogo com mapeamento estruturado exato."""
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
                    # Identifica a ordem exata dos rótulos de estatísticas
                    labels = category.get('names', [])
                    for event in category.get('events', []):
                        event_id = event.get('eventId')
                        event_info = events_dict.get(str(event_id), {})
                        
                        # Data do jogo e adversário
                        game_date = event_info.get('gameDate', '')
                        opponent = event_info.get('opponent', {}).get('abbreviation', '')
                        home_away = '@' if event_info.get('homeAway') == 'away' else 'x'
                        
                        stats_values = event.get('stats', [])
                        if stats_values and labels:
                            # Cria dicionário {NOME_STAT: VALOR}
                            stat_map = dict(zip(labels, stats_values))
                            
                            logs.append({
                                'GAME_DATE': game_date,
                                'MATCHUP': f"{home_away} {opponent}",
                                'MIN': stat_map.get('MIN', '0'),
                                'PTS': int(stat_map.get('PTS', 0)) if str(stat_map.get('PTS', 0)).isdigit() else 0,
                                'AQ': stat_map.get('FG', '0-0'),
                                '3PT': stat_map.get('3PT', '0-0'),
                                'LL': stat_map.get('FT', '0-0'),
                                'REB': int(stat_map.get('REB', 0)) if str(stat_map.get('REB', 0)).isdigit() else 0,
                                'AST': int(stat_map.get('AST', 0)) if str(stat_map.get('AST', 0)).isdigit() else 0,
                                'RBD': int(stat_map.get('STL', 0)) if str(stat_map.get('STL', 0)).isdigit() else 0,
                                'BLQ': int(stat_map.get('BLK', 0)) if str(stat_map.get('BLK', 0)).isdigit() else 0,
                                'BP': int(stat_map.get('TO', 0)) if str(stat_map.get('TO', 0)).isdigit() else 0
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
        df_raw = obter_gamelog_preciso(espn_id)
    
    if not df_raw.empty:
        df_display = pd.DataFrame()
        
        # Coluna Jogo (Ex: 05/11 @ Kings ou 03/11 x Heat)
        df_display['Jogo'] = pd.to_datetime(df_raw['GAME_DATE']).dt.strftime('%d/%m') + " " + df_raw['MATCHUP']
        
        # Estatísticas exatas organizadas
        df_display['MIN'] = df_raw['MIN']
        df_display['PTS'] = df_raw['PTS']
        df_display['AQ'] = df_raw['AQ']
        df_display['3PT'] = df_raw['3PT']
        df_display['LL'] = df_raw['LL']
        df_display['REB'] = df_raw['REB']
        df_display['AST'] = df_raw['AST']
        df_display['RBD'] = df_raw['RBD']
        df_display['BLQ'] = df_raw['BLQ']
        df_display['BP'] = df_raw['BP']
        
        # Cards de Médias
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Média PTS", round(df_raw['PTS'].mean(), 1))
        col2.metric("Média REB", round(df_raw['REB'].mean(), 1))
        col3.metric("Média AST", round(df_raw['AST'].mean(), 1))
        col4.metric("Total de Jogos", len(df_raw))
        col5.metric("Média Minutos", round(pd.to_numeric(df_raw['MIN'], errors='coerce').mean(), 1))
        
        st.divider()
        
        # Tabela HTML Compacta e Centralizada
        html_table = df_display.to_html(classes='nba-table', index=False, escape=False)
        st.markdown(f'<div class="tabela-container">{html_table}</div>', unsafe_allow_html=True)
    else:
        st.warning(f"Nenhuma partida registrada para {jogador_selecionado} nesta temporada.")

except Exception as e:
    st.error(f"Erro ao processar estatísticas: {e}")
