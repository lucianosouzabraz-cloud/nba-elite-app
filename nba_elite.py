import streamlit as st
import pandas as pd
import requests

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E CSS
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

# Mapeamento oficial das siglas de times da NBA na ESPN API
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
# FUNÇÕES DE BUSCA (API ABERTA DA ESPN)
# ==========================================
@st.cache_data(ttl=3600)
def obter_elenco_time(team_abbr):
    """Busca estritamente os jogadores do time selecionado sem bloqueios de IP."""
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
def obter_logs_jogador(espn_id):
    """Busca o histórico de partidas jogo a jogo via ESPN."""
    url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{espn_id}/gamelog"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            season_types = data.get('seasonTypes', [])
            logs = []
            for stype in season_types:
                for category in stype.get('categories', []):
                    for event in category.get('events', []):
                        stats = event.get('stats', [])
                        if stats and len(stats) >= 13:
                            logs.append({
                                'GAME_DATE': event.get('gameDate', ''),
                                'MATCHUP': event.get('opponent', {}).get('abbreviation', ''),
                                'HOME_AWAY': '@' if event.get('homeAway') == 'away' else 'x',
                                'MIN': stats[0],
                                'PTS': int(stats[13]) if len(stats) > 13 and str(stats[13]).isdigit() else 0,
                                'AQ': stats[1],   # Field Goals (FG)
                                '3PT': stats[3],  # 3-Point Field Goals (3PT)
                                'LL': stats[5],   # Free Throws (FT)
                                'REB': int(stats[8]) if str(stats[8]).isdigit() else 0,
                                'AST': int(stats[9]) if str(stats[9]).isdigit() else 0,
                                'BLQ': int(stats[10]) if str(stats[10]).isdigit() else 0,
                                'RBD': int(stats[11]) if str(stats[11]).isdigit() else 0, # Steals (Roubos)
                                'BP': int(stats[12]) if str(stats[12]).isdigit() else 0    # Turnovers
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

# 2. Seleção do Jogador (FILTRADO STRICTAMENTE PELO TIME)
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
        df_raw = obter_logs_jogador(espn_id)
    
    if not df_raw.empty:
        df_display = pd.DataFrame()
        
        # Formatação idêntica do Jogo (Ex: 05/11 @ SAC ou x MIA)
        df_display['Jogo'] = pd.to_datetime(df_raw['GAME_DATE']).dt.strftime('%d/%m') + " " + df_raw['HOME_AWAY'] + " " + df_raw['MATCHUP']
        
        # Colunas na mesma ordem do seu print
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
        
        # Cards de Médias no Topo
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
        st.warning(f"Nenhuma partida encontrada para {jogador_selecionado} na temporada selecionada.")

except Exception as e:
    st.error(f"Erro ao processar estatísticas: {e}")
