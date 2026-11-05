import streamlit as st
import pandas as pd
import requests
import unicodedata
import time
from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import playergamelog

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

TEAM_ABBR_MAP = {
    1610612737: 'atl', 1610612738: 'bos', 1610612751: 'bkn', 1610612766: 'cha',
    1610612741: 'chi', 1610612739: 'cle', 1610612742: 'dal', 1610612743: 'den',
    1610612765: 'det', 1610612744: 'gsw', 1610612745: 'hou', 1610612754: 'ind',
    1610612746: 'lac', 1610612747: 'lal', 1610612763: 'mem', 1610612748: 'mia',
    1610612749: 'mil', 1610612750: 'min', 1610612740: 'nop', 1610612752: 'nyk',
    1610612760: 'okc', 1610612753: 'orl', 1610612755: 'phi', 1610612756: 'phx',
    1610612757: 'por', 1610612758: 'sac', 1610612759: 'sas', 1610612761: 'tor',
    1610612762: 'uta', 1610612764: 'was'
}

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

def normalizar_texto(texto):
    """Remove acentos e caracteres especiais para comparação de nomes."""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

@st.cache_data(ttl=86400)
def obter_todos_times():
    return pd.DataFrame(teams.get_teams()).sort_values(by="full_name")

@st.cache_data(ttl=3600)
def obter_elenco_espn(team_id):
    abbr = TEAM_ABBR_MAP.get(team_id)
    if not abbr:
        return pd.DataFrame()
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{abbr}/roster"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        jogadores = [{'PLAYER': athlete.get('fullName')} for athlete in data.get('athletes', [])]
        return pd.DataFrame(jogadores).sort_values(by="PLAYER")
    return pd.DataFrame()

@st.cache_data(ttl=86400)
def Mapeamento_Ids_Jogadores():
    """Cria um dicionário com busca por nome normalizado sem acentos."""
    todos_jogadores = players.get_active_players()
    mapa = {}
    for p in todos_jogadores:
        nome_normal = normalizar_texto(p['full_name'])
        mapa[nome_normal] = p['id']
    return mapa

@st.cache_data(ttl=1800)
def obter_logs_jogador(player_id, season="2026-27"):
    for t in range(3):
        try:
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season,
                headers=CUSTOM_HEADERS,
                timeout=30
            ).get_data_frames()[0]
            if not gamelog.empty:
                return gamelog
        except Exception:
            time.sleep(1)
    return pd.DataFrame()

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.header("🔍 Seleção de Filtros")

df_times = obter_todos_times()
time_selecionado = st.sidebar.selectbox("Escolha o Time:", df_times['full_name'].values)
team_id = df_times[df_times['full_name'] == time_selecionado]['id'].values[0]

df_elenco = obter_elenco_espn(team_id)
mapa_jogadores = Mapeamento_Ids_Jogadores()

if not df_elenco.empty:
    jogador_selecionado = st.sidebar.selectbox("Escolha o Jogador:", df_elenco['PLAYER'].values)
    nome_norm = normalizar_texto(jogador_selecionado)
    player_id = mapa_jogadores.get(nome_norm)
else:
    st.sidebar.error("Erro ao carregar o elenco.")
    st.stop()

temporada = st.sidebar.selectbox("Temporada:", ["2026-27", "2025-26", "2024-25", "2023-24"], index=0)

# ==========================================
# QUADRO PRINCIPAL
# ==========================================
st.subheader(f"📊 Estatísticas: {jogador_selecionado} ({time_selecionado}) - Temporada {temporada}")

if player_id:
    try:
        with st.spinner("Buscando estatísticas atualizadas da NBA..."):
            df_raw = obter_logs_jogador(player_id, season=temporada)
        
        if not df_raw.empty:
            df_display = pd.DataFrame()
            df_display['Jogo'] = pd.to_datetime(df_raw['GAME_DATE']).dt.strftime('%d/%m') + " " + df_raw['MATCHUP']
            df_display['MIN'] = df_raw['MIN']
            df_display['PTS'] = df_raw['PTS']
            df_display['AQ'] = df_raw['FGM'].astype(str) + "-" + df_raw['FGA'].astype(str)
            df_display['3PT'] = df_raw['FG3M'].astype(str) + "-" + df_raw['FG3A'].astype(str)
            df_display['LL'] = df_raw['FTM'].astype(str) + "-" + df_raw['FTA'].astype(str)
            df_display['REB'] = df_raw['REB']
            df_display['AST'] = df_raw['AST']
            df_display['RBD'] = df_raw['STL']
            df_display['BLQ'] = df_raw['BLK']
            df_display['BP'] = df_raw['TOV']
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Média PTS", round(df_raw['PTS'].mean(), 1))
            col2.metric("Média REB", round(df_raw['REB'].mean(), 1))
            col3.metric("Média AST", round(df_raw['AST'].mean(), 1))
            col4.metric("Média 3PT Convertidos", round(df_raw['FG3M'].mean(), 1))
            col5.metric("Média Minutos", round(df_raw['MIN'].mean(), 1))
            
            st.divider()
            html_table = df_display.to_html(classes='nba-table', index=False, escape=False)
            st.markdown(f'<div class="tabela-container">{html_table}</div>', unsafe_allow_html=True)
        else:
            st.warning(f"O jogador {jogador_selecionado} não possui partidas registradas nesta temporada.")
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
else:
    st.warning("ID do jogador não encontrado na base de dados da NBA.")
