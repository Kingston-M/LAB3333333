import os
import streamlit as st
import pandas as pd
from pydantic_ai import Agent
from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguedashteamstats, leaguedashplayerstats

st.set_page_config(page_title="NBAStat | Basketball Agent", page_icon="🤖", layout="wide")

st.title("🤖 Basketball Data Agent (Dataset-Backed AI)")
st.caption("Powered by Pydantic AI + Live NBA Dataset Tools. Ask real analytical questions grounded in actual NBA stats!")

if "GOOGLE_API_KEY" in st.secrets and st.secrets["GOOGLE_API_KEY"]:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

season_choice = st.sidebar.selectbox(
    "Dataset Season for Agent:",
    options=["2026-27", "2025-26", "2024-25", "2023-24", "2022-23"],
    index=0
)

# --- Cached Dataset Loaders for Agent Tools ---
@st.cache_data(ttl=3600)
def fetch_player_dataset(season: str) -> pd.DataFrame:
    base = leaguedashplayerstats.LeagueDashPlayerStats(season=season, per_mode_detailed="PerGame").get_data_frames()[0]
    adv = leaguedashplayerstats.LeagueDashPlayerStats(season=season, measure_type_detailed_defense="Advanced").get_data_frames()[0][
        ["PLAYER_ID", "TS_PCT", "USG_PCT", "OFF_RATING", "DEF_RATING", "NET_RATING"]
    ]
    return pd.merge(base, adv, on="PLAYER_ID", how="left")

@st.cache_data(ttl=3600)
def fetch_team_dataset(season: str) -> pd.DataFrame:
    base = leaguedashteamstats.LeagueDashTeamStats(season=season, per_mode_detailed="PerGame").get_data_frames()[0]
    adv = leaguedashteamstats.LeagueDashTeamStats(season=season, measure_type_detailed_defense="Advanced").get_data_frames()[0][
        ["TEAM_ID", "OFF_RATING", "DEF_RATING", "NET_RATING", "TS_PCT", "PACE"]
    ]
    return pd.merge(base, adv, on="TEAM_ID", how="left")

# --- Tool 1 (Data-processing function written by team): Get Player Stats ---
def get_player_stats(player_name: str, season: str = "2026-27") -> dict:
    """Look up a specific NBA player's per-game box score and advanced efficiency stats for a given season."""
    df = fetch_player_dataset(season)
    matches = df[df["PLAYER_NAME"].str.contains(player_name, case=False, na=False)]
    if matches.empty:
        return {"error": f"No player found matching '{player_name}' in {season}."}
    row = matches.iloc[0]
    return {
        "player": row["PLAYER_NAME"],
        "team": row["TEAM_ABBREVIATION"],
        "season": season,
        "games_played": int(row["GP"]),
        "ppg": round(float(row["PTS"]), 1),
        "rpg": round(float(row["REB"]), 1),
        "apg": round(float(row["AST"]), 1),
        "spg": round(float(row["STL"]), 1),
        "bpg": round(float(row["BLK"]), 1),
        "tov": round(float(row["TOV"]), 1),
        "pf_total": int(round(float(row["PF"]) * int(row["GP"]))),
        "fg_pct": round(float(row["FG_PCT"]) * 100, 1),
        "fg3_pct": round(float(row["FG3_PCT"]) * 100, 1),
        "ts_pct": round(float(row["TS_PCT"]) * 100, 1),
        "usg_pct": round(float(row["USG_PCT"]) * 100, 1),
        "plus_minus": round(float(row["PLUS_MINUS"]), 1),
    }

# --- Tool 2 (Data-processing function written by team): Team Roster Stat Leader ---
def get_team_stat_leader(team_abbreviation: str, stat_column: str = "PTS", season: str = "2026-27") -> dict:
    """Find the leader on a specific NBA team (e.g., ATL, OKC, MIN, LAL) for a stat column such as PTS, REB, AST, STL, BLK, PF, or TS_PCT."""
    df = fetch_player_dataset(season)
    team_df = df[df["TEAM_ABBREVIATION"].str.upper() == team_abbreviation.upper()].copy()
    if team_df.empty:
        return {"error": f"No players found for team abbreviation '{team_abbreviation}' in {season}."}
    col = stat_column.upper()
    if col not in team_df.columns:
        col = "PTS"
    team_df["TOTAL_PF"] = team_df["PF"] * team_df["GP"]
    sort_col = "TOTAL_PF" if col == "PF" else col
    leader = team_df.sort_values(sort_col, ascending=False).iloc[0]
    val = round(float(leader[sort_col]) * 100, 1) if "PCT" in col else round(float(leader[sort_col]), 1)
    return {
        "team": team_abbreviation.upper(),
        "season": season,
        "stat": col,
        "leader_name": leader["PLAYER_NAME"],
        "value": val,
        "ppg": round(float(leader["PTS"]), 1),
        "rpg": round(float(leader["REB"]), 1),
        "apg": round(float(leader["AST"]), 1),
        "ts_pct": round(float(leader["TS_PCT"]) * 100, 1),
    }

# --- Tool 3 (AI-assisted Dream Project tool): Compare Two NBA Teams ---
def compare_nba_teams(team1_name: str, team2_name: str, season: str = "2026-27") -> dict:
    """Compare two NBA teams across record, PPG, Offensive Rating, Defensive Rating, Net Rating, and True Shooting %."""
    # AI-assisted helper to merge team box score & advanced efficiency metrics
    df = fetch_team_dataset(season)
    t1 = df[df["TEAM_NAME"].str.contains(team1_name, case=False, na=False)]
    t2 = df[df["TEAM_NAME"].str.contains(team2_name, case=False, na=False)]
    if t1.empty or t2.empty:
        return {"error": f"Could not find one or both teams: '{team1_name}', '{team2_name}'."}
    r1, r2 = t1.iloc[0], t2.iloc[0]
    return {
        "season": season,
        "team_1": {
            "name": r1["TEAM_NAME"],
            "record": f"{int(r1['W'])}-{int(r1['L'])}",
            "ppg": round(float(r1["PTS"]), 1),
            "off_rating": round(float(r1["OFF_RATING"]), 1),
            "def_rating": round(float(r1["DEF_RATING"]), 1),
            "net_rating": round(float(r1["NET_RATING"]), 1),
            "ts_pct": round(float(r1["TS_PCT"]) * 100, 1),
        },
        "team_2": {
            "name": r2["TEAM_NAME"],
            "record": f"{int(r2['W'])}-{int(r2['L'])}",
            "ppg": round(float(r2["PTS"]), 1),
            "off_rating": round(float(r2["OFF_RATING"]), 1),
            "def_rating": round(float(r2["DEF_RATING"]), 1),
            "net_rating": round(float(r2["NET_RATING"]), 1),
            "ts_pct": round(float(r2["TS_PCT"]) * 100, 1),
        }
    }

# --- Tool 4 (AI-assisted Dream Project tool): Compare Two Players Beyond the Box Score ---
def compare_two_players(player1_name: str, player2_name: str, season: str = "2026-27") -> dict:
    """Compare two NBA players side-by-side on scoring volume, playmaking, rebounding, and True Shooting efficiency."""
    # AI-assisted tool combining per-game box score and TS% efficiency
    p1 = get_player_stats(player1_name, season)
    p2 = get_player_stats(player2_name, season)
    return {"season": season, "player_1": p1, "player_2": p2}

@st.cache_resource
def get_nba_data_agent():
    return Agent(
        "google-gla:gemini-2.5-flash",
        tools=[get_player_stats, get_team_stat_leader, compare_nba_teams, compare_two_players],
        instructions=(
            "You are the 'NBAStat: Beyond the Box Score' AI Data Analyst. You MUST answer user questions using "
            "the provided NBA dataset tools rather than guessing from memory. Always pass the user's requested season "
            "(or the active sidebar season) into the tool calls. Highlight efficiency metrics like True Shooting % (TS%) "
            "and Net Rating alongside traditional box score stats."
        ),
    )

# Sample Prompts Helper
st.markdown("**Try asking:**")
sample_cols = st.columns(3)
sample_questions = [
    f"Which Hawks player (ATL) recorded the most personal fouls (PF) in {season_choice}?",
    f"How does the Timberwolves' efficiency compare to the Thunder in {season_choice}?",
    f"Compare Shai Gilgeous-Alexander and Luka Doncic beyond the box score in {season_choice}."
]
for idx, q in enumerate(sample_questions):
    if sample_cols[idx].button(q, use_container_width=True):
        st.session_state["pending_agent_prompt"] = q

if "agent_messages" not in st.session_state:
    st.session_state.agent_messages = []
if "agent_history" not in st.session_state:
    st.session_state.agent_history = []

for msg in st.session_state.agent_messages:
    with st.chat_message(msg["role"]):
        if "tool_logs" in msg and msg["tool_logs"]:
            with st.expander("🛠️ Tools Called & Dataset Results"):
                for log in msg["tool_logs"]:
                    st.write(f"**Tool:** `{log['tool']}` | **Args:** `{log['args']}`")
                    st.json(log["result"])
        st.markdown(msg["content"])

user_input = st.chat_input(f"Ask a data question about the {season_choice} NBA season...")
if "pending_agent_prompt" in st.session_state:
    user_input = st.session_state.pop("pending_agent_prompt")

if user_input:
    st.session_state.agent_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            if not os.environ.get("GOOGLE_API_KEY"):
                st.warning("⚠️ Please add your `GOOGLE_API_KEY` to `.streamlit/secrets.toml` to run the NBA Data Agent.")
            else:
                agent = get_nba_data_agent()
                contextual_prompt = f"[Active Season: {season_choice}] {user_input}"
                with st.spinner("Querying NBA dataset tools..."):
                    result = agent.run_sync(contextual_prompt, message_history=st.session_state.agent_history)

                # Extract tool calls and outputs from new messages to display transparency
                tool_logs = []
                tool_calls_map = {}
                for m in result.new_messages():
                    for part in getattr(m, "parts", []):
                        part_kind = getattr(part, "part_kind", "")
                        if part_kind == "tool-call":
                            tool_calls_map[part.tool_call_id] = {
                                "tool": part.tool_name,
                                "args": part.args,
                                "result": None
                            }
                        elif part_kind == "tool-return":
                            if part.tool_call_id in tool_calls_map:
                                tool_calls_map[part.tool_call_id]["result"] = part.content
                tool_logs = list(tool_calls_map.values())

                if tool_logs:
                    with st.expander("🛠️ Tools Called & Dataset Results", expanded=True):
                        for log in tool_logs:
                            st.write(f"**Tool:** `{log['tool']}` | **Args:** `{log['args']}`")
                            st.json(log["result"])

                st.markdown(result.output)
                st.session_state.agent_messages.append({
                    "role": "assistant",
                    "content": result.output,
                    "tool_logs": tool_logs
                })
                st.session_state.agent_history = result.all_messages()
        except Exception as e:
            st.error(f"Agent Error: {e}")
