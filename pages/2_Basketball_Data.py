import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import (
    leaguedashteamstats,
    leaguedashplayerstats,
    commonteamroster,
    commonplayerinfo,
)
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

st.set_page_config(page_title="NBAStat | Basketball Data", page_icon="📊", layout="wide")

# --- NBA Team Primary Colors & Logo Helper ---
TEAM_COLORS = {
    "ATL": "#E03A3E", "BOS": "#007A33", "BKN": "#000000", "CHA": "#1D1160",
    "CHI": "#CE1141", "CLE": "#860038", "DAL": "#00538C", "DEN": "#0E2240",
    "DET": "#C8102E", "GSW": "#1D428A", "HOU": "#CE1141", "IND": "#002D62",
    "LAC": "#C8102E", "LAL": "#552583", "MEM": "#5D76A9", "MIA": "#98002E",
    "MIL": "#00471B", "MIN": "#0C2340", "NOP": "#0C2340", "NYK": "#006BB6",
    "OKC": "#007AC1", "ORL": "#0077C0", "PHI": "#006BB6", "PHX": "#1D1160",
    "POR": "#E03A3E", "SAC": "#5A2D81", "SAS": "#C4CED4", "TOR": "#CE1141",
    "UTA": "#002B5C", "WAS": "#002B5C"
}

def get_team_logo_url(team_id: int) -> str:
    return f"https://cdn.nba.com/logos/nba/{team_id}/primary/L/logo.svg"

def get_player_headshot_url(player_id: int) -> str:
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

# --- Cached NBA API Loaders ---
@st.cache_data(ttl=3600)
def load_league_team_stats(season: str = "2026-27") -> pd.DataFrame:
    df = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        per_mode_detailed="PerGame"
    ).get_data_frames()[0]
    adv_df = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        measure_type_detailed_defense="Advanced"
    ).get_data_frames()[0][["TEAM_ID", "OFF_RATING", "DEF_RATING", "NET_RATING", "TS_PCT", "PACE", "PIE"]]
    merged = pd.merge(df, adv_df, on="TEAM_ID", how="left")
    return merged

@st.cache_data(ttl=3600)
def load_league_player_stats(season: str = "2026-27") -> pd.DataFrame:
    base_df = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        per_mode_detailed="PerGame"
    ).get_data_frames()[0]
    adv_df = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        measure_type_detailed_defense="Advanced"
    ).get_data_frames()[0][["PLAYER_ID", "TS_PCT", "USG_PCT", "OFF_RATING", "DEF_RATING", "NET_RATING", "PIE"]]
    merged = pd.merge(base_df, adv_df, on="PLAYER_ID", how="left")
    return merged

@st.cache_data(ttl=3600)
def get_team_roster(team_id: int, season: str = "2026-27") -> pd.DataFrame:
    return commonteamroster.CommonTeamRoster(team_id=team_id, season=season).get_data_frames()[0]

def compute_2k_overall(row: pd.Series) -> int:
    """Computes a fun NBA 2K-style overall rating (70-99) from box score & efficiency stats."""
    pts = float(row.get("PTS", 0))
    reb = float(row.get("REB", 0))
    ast = float(row.get("AST", 0))
    stl = float(row.get("STL", 0))
    blk = float(row.get("BLK", 0))
    ts = float(row.get("TS_PCT", 0.55)) * 100
    raw = 68 + (pts * 0.52) + (reb * 0.45) + (ast * 0.65) + ((stl + blk) * 1.4) + ((ts - 54) * 0.35)
    return int(max(70, min(99, round(raw))))

def render_2k_player_card(player_row: pd.Series, team_id: int, team_abbr: str):
    """Renders an NBA 2K MyTEAM-style interactive HTML card with player headshot, team logo, and full stats."""
    pid = int(player_row["PLAYER_ID"])
    name = player_row["PLAYER_NAME"]
    ovr = compute_2k_overall(player_row)
    color = TEAM_COLORS.get(team_abbr, "#1D428A")
    headshot = get_player_headshot_url(pid)
    logo = get_team_logo_url(team_id)

    pts = f"{player_row.get('PTS', 0):.1f}"
    reb = f"{player_row.get('REB', 0):.1f}"
    ast = f"{player_row.get('AST', 0):.1f}"
    stl = f"{player_row.get('STL', 0):.1f}"
    blk = f"{player_row.get('BLK', 0):.1f}"
    tov = f"{player_row.get('TOV', 0):.1f}"
    fg_pct = f"{player_row.get('FG_PCT', 0)*100:.1f}%"
    fg3_pct = f"{player_row.get('FG3_PCT', 0)*100:.1f}%"
    ft_pct = f"{player_row.get('FT_PCT', 0)*100:.1f}%"
    ts_pct = f"{player_row.get('TS_PCT', 0)*100:.1f}%"
    usg_pct = f"{player_row.get('USG_PCT', 0)*100:.1f}%"
    plus_minus = f"{player_row.get('PLUS_MINUS', 0):+.1f}"

    card_html = f"""
    <div style="
        background: linear-gradient(145deg, #111625 0%, {color} 100%);
        border: 2px solid #f5c542;
        border-radius: 18px;
        padding: 18px;
        color: white;
        box-shadow: 0 10px 25px rgba(0,0,0,0.45);
        font-family: 'Segoe UI', sans-serif;
        margin-bottom: 14px;
    ">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="font-size:34px; font-weight:900; color:#f5c542; line-height:1;">{ovr}</span>
                <span style="font-size:12px; font-weight:700; letter-spacing:1px; color:#ddd; display:block;">OVR • {team_abbr}</span>
            </div>
            <img src="{logo}" width="54" height="54" style="object-fit:contain;" />
        </div>
        <div style="text-align:center; margin: 6px 0;">
            <img src="{headshot}" width="175" style="border-radius: 10px; object-fit:cover;" onerror="this.style.display='none'" />
            <h3 style="margin: 6px 0 2px 0; font-size:20px; font-weight:800; color:#ffffff;">{name}</h3>
            <span style="font-size:12px; color:#e0e0e0;">GP: {int(player_row.get('GP', 0))} | MIN: {player_row.get('MIN', 0):.1f} | +/-: {plus_minus}</span>
        </div>
        <div style="
            display:grid; grid-template-columns: repeat(4, 1fr); gap:8px;
            background: rgba(0,0,0,0.45); border-radius:12px; padding:10px; text-align:center; margin-top:10px;
        ">
            <div><div style="font-size:11px; color:#bbb;">PPG</div><div style="font-size:16px; font-weight:800;">{pts}</div></div>
            <div><div style="font-size:11px; color:#bbb;">RPG</div><div style="font-size:16px; font-weight:800;">{reb}</div></div>
            <div><div style="font-size:11px; color:#bbb;">APG</div><div style="font-size:16px; font-weight:800;">{ast}</div></div>
            <div><div style="font-size:11px; color:#bbb;">TS%</div><div style="font-size:16px; font-weight:800; color:#f5c542;">{ts_pct}</div></div>
            <div><div style="font-size:11px; color:#bbb;">FG%</div><div style="font-size:14px; font-weight:700;">{fg_pct}</div></div>
            <div><div style="font-size:11px; color:#bbb;">3P%</div><div style="font-size:14px; font-weight:700;">{fg3_pct}</div></div>
            <div><div style="font-size:11px; color:#bbb;">STL / BLK</div><div style="font-size:14px; font-weight:700;">{stl} / {blk}</div></div>
            <div><div style="font-size:11px; color:#bbb;">USG% / TOV</div><div style="font-size:14px; font-weight:700;">{usg_pct} / {tov}</div></div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def render_2k_team_card(team_row: pd.Series):
    """Renders an NBA 2K-style Team Analytics Card with Team Logo and Offensive/Defensive Ratings."""
    tid = int(team_row["TEAM_ID"])
    tname = team_row["TEAM_NAME"]
    abbr = team_row.get("TEAM_ABBREVIATION", "NBA")
    color = TEAM_COLORS.get(abbr, "#1D428A")
    logo = get_team_logo_url(tid)

    wins = int(team_row.get("W", 0))
    losses = int(team_row.get("L", 0))
    wpct = f"{team_row.get('W_PCT', 0)*100:.1f}%"
    pts = f"{team_row.get('PTS', 0):.1f}"
    ortg = f"{team_row.get('OFF_RATING', 0):.1f}"
    drtg = f"{team_row.get('DEF_RATING', 0):.1f}"
    nrtg = f"{team_row.get('NET_RATING', 0):+.1f}"
    ts = f"{team_row.get('TS_PCT', 0)*100:.1f}%"
    ast = f"{team_row.get('AST', 0):.1f}"
    reb = f"{team_row.get('REB', 0):.1f}"
    pace = f"{team_row.get('PACE', 0):.1f}"

    html = f"""
    <div style="
        background: linear-gradient(135deg, #10141f 0%, {color} 100%);
        border: 2px solid #f5c542;
        border-radius: 16px;
        padding: 16px;
        color: white;
        box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        margin-bottom: 12px;
    ">
        <div style="display:flex; align-items:center; gap:14px;">
            <img src="{logo}" width="64" height="64" style="object-fit:contain;" />
            <div>
                <h3 style="margin:0; font-size:19px; font-weight:800;">{tname}</h3>
                <span style="font-size:13px; color:#f5c542; font-weight:700;">Record: {wins}-{losses} ({wpct}) | Net Rating: {nrtg}</span>
            </div>
        </div>
        <div style="
            display:grid; grid-template-columns: repeat(4, 1fr); gap:8px;
            background: rgba(0,0,0,0.45); border-radius:10px; padding:10px; text-align:center; margin-top:12px;
        ">
            <div><div style="font-size:11px; color:#bbb;">PPG</div><div style="font-size:15px; font-weight:800;">{pts}</div></div>
            <div><div style="font-size:11px; color:#bbb;">OFF RTG</div><div style="font-size:15px; font-weight:800;">{ortg}</div></div>
            <div><div style="font-size:11px; color:#bbb;">DEF RTG</div><div style="font-size:15px; font-weight:800;">{drtg}</div></div>
            <div><div style="font-size:11px; color:#bbb;">TS%</div><div style="font-size:15px; font-weight:800; color:#f5c542;">{ts}</div></div>
            <div><div style="font-size:11px; color:#bbb;">RPG</div><div style="font-size:14px; font-weight:700;">{reb}</div></div>
            <div><div style="font-size:11px; color:#bbb;">APG</div><div style="font-size:14px; font-weight:700;">{ast}</div></div>
            <div><div style="font-size:11px; color:#bbb;">PACE</div><div style="font-size:14px; font-weight:700;">{pace}</div></div>
            <div><div style="font-size:11px; color:#bbb;">FG% / 3P%</div><div style="font-size:14px; font-weight:700;">{team_row.get('FG_PCT',0)*100:.1f}% / {team_row.get('FG3_PCT',0)*100:.1f}%</div></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def mapMaking(team, season):
    teamInfo = teams.find_teams_by_full_name(team)
    teamID = teamInfo[0]["id"]
    teamLoc = f"{teamInfo[0]['city']}, {teamInfo[0]['state']}"
    geolocator = Nominatim(user_agent="cs1301_nbaLocations")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    teamCoord = geocode(teamLoc)

    roster_df = get_team_roster(teamID, season)
    playerLats, playerLongs, validPlayers = [], [], []

    for _, r in roster_df.iterrows():
        playerName = r["PLAYER"]
        playerID = r["PLAYER_ID"]
        playerInfo = commonplayerinfo.CommonPlayerInfo(player_id=playerID).get_data_frames()[0]
        lastLoc = str(playerInfo["LAST_AFFILIATION"].values[0]).replace("/", ", ")
        playerCoord = geocode(lastLoc)
        if playerCoord is None:
            country = playerInfo["COUNTRY"].values[0]
            if country:
                playerCoord = geocode(country)
        if playerCoord is not None:
            validPlayers.append(playerName)
            playerLats.append(playerCoord.latitude)
            playerLongs.append(playerCoord.longitude)

    allNames = [team] + validPlayers
    allLats = [teamCoord.latitude] + playerLats
    allLongs = [teamCoord.longitude] + playerLongs
    allTypes = ["Team"] + ["Player"] * len(playerLats)

    worldMap = px.scatter_map(
        lat=allLats, lon=allLongs, text=allNames, color=allTypes,
        color_discrete_sequence=["red", "blue"],
        title=f"{team} Player Hometowns / Prior Affiliations",
        map_style="carto-darkmatter"
    )
    lineLats, lineLongs = [], []
    for i in range(len(playerLats)):
        lineLats.extend([teamCoord.latitude, playerLats[i], None])
        lineLongs.extend([teamCoord.longitude, playerLongs[i], None])
    lines = px.line_map(lat=lineLats, lon=lineLongs)
    worldMap.add_trace(lines.data[0])
    st.plotly_chart(worldMap, use_container_width=True)

def data():
    st.title("🏀 NBA Analytics: Beyond the Box Score")
    st.subheader("Interactive 2K-Style Player & Team Visual Analytics")

    season = st.sidebar.selectbox(
        "Select NBA Season:",
        options=["2026-27", "2025-26", "2024-25", "2023-24", "2022-23"],
        index=0
    )

    try:
        with st.spinner(f"Loading {season} NBA League Stats..."):
            team_df = load_league_team_stats(season)
            player_df = load_league_player_stats(season)
    except Exception as e:
        st.error(f"Could not fetch live NBA API data right now: {e}")
        return

    teamsAPI = teams.get_teams()
    team_name_to_obj = {t["full_name"]: t for t in teamsAPI}
    teamOptions = sorted(list(team_name_to_obj.keys()))

    tab1, tab2, tab3 = st.tabs([
        "🏆 Compare Teams (2K Graph & Logos)",
        "🃏 Compare Players (2K Cards & Radar)",
        "🌍 Where Are Players From?"
    ])

    # ================= TAB 1: TEAM ANALYTICS =================
    with tab1:
        st.subheader("Team Analytics & Efficiency Comparison")
        col_ctrl1, col_ctrl2 = st.columns([1, 2])
        with col_ctrl1:
            number = int(st.radio("How many teams to compare?", ["2", "3", "4"], horizontal=True))
        with col_ctrl2:
            stat_options = {
                "Points Per Game (PTS)": "PTS",
                "Offensive Rating (OFF_RATING)": "OFF_RATING",
                "Defensive Rating (DEF_RATING)": "DEF_RATING",
                "Net Rating (NET_RATING)": "NET_RATING",
                "True Shooting % (TS_PCT)": "TS_PCT",
                "Win Percentage (W_PCT)": "W_PCT",
                "Field Goal % (FG_PCT)": "FG_PCT",
                "3-Point % (FG3_PCT)": "FG3_PCT",
                "Assists Per Game (AST)": "AST",
                "Rebounds Per Game (REB)": "REB",
                "Steals Per Game (STL)": "STL",
                "Blocks Per Game (BLK)": "BLK",
                "Turnovers Per Game (TOV)": "TOV",
                "Pace (PACE)": "PACE"
            }
            selected_stat_labels = st.multiselect(
                "Select statistical categories to graph:",
                options=list(stat_options.keys()),
                default=["Points Per Game (PTS)", "Offensive Rating (OFF_RATING)", "Defensive Rating (DEF_RATING)"]
            )

        default_teams = ["Atlanta Hawks", "Oklahoma City Thunder", "Minnesota Timberwolves", "Boston Celtics"]
        teamSelections = []
        cols = st.columns(number)
        for i in range(number):
            with cols[i]:
                default_idx = teamOptions.index(default_teams[i]) if default_teams[i] in teamOptions else i
                choice = st.selectbox(f"Select Team {i+1}:", options=teamOptions, index=default_idx, key=f"team_cmp_{i}")
                teamSelections.append(choice)

        selected_rows = team_df[team_df["TEAM_NAME"].isin(teamSelections)].copy()

        # Render 2K Team Cards with Logos
        card_cols = st.columns(len(teamSelections))
        for idx, t_name in enumerate(teamSelections):
            t_match = selected_rows[selected_rows["TEAM_NAME"] == t_name]
            if not t_match.empty:
                with card_cols[idx]:
                    render_2k_team_card(t_match.iloc[0])

        # Interactive 2K-style Plotly Bar Chart with Embedded Team Logos
        if selected_stat_labels and not selected_rows.empty:
            fig = go.Figure()
            for label in selected_stat_labels:
                col_code = stat_options[label]
                y_vals = []
                for t_name in teamSelections:
                    r = selected_rows[selected_rows["TEAM_NAME"] == t_name]
                    val = float(r[col_code].values[0]) if not r.empty else 0.0
                    if "PCT" in col_code:
                        val = round(val * 100, 1)
                    y_vals.append(round(val, 1))

                fig.add_trace(go.Bar(
                    name=label,
                    x=teamSelections,
                    y=y_vals,
                    text=y_vals,
                    textposition="outside"
                ))

            # Embed Team Logos directly above the bars in the interactive Plotly graph
            max_y = max([max(trace.y) for trace in fig.data]) if fig.data else 100
            for idx, t_name in enumerate(teamSelections):
                t_obj = team_name_to_obj[t_name]
                fig.add_layout_image(
                    dict(
                        source=get_team_logo_url(t_obj["id"]),
                        xref="x",
                        yref="y",
                        x=t_name,
                        y=max_y * 1.15,
                        sizex=0.45,
                        sizey=max_y * 0.22,
                        xanchor="center",
                        yanchor="middle"
                    )
                )

            fig.update_layout(
                title=f"2K Team Comparison Graph ({season})",
                barmode="group",
                template="plotly_dark",
                yaxis=dict(range=[0, max_y * 1.32]),
                height=500,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

            # League-Wide Offensive vs Defensive Rating Scatter with Team Logos
            with st.expander("📈 Explore League-Wide Offensive vs. Defensive Rating (All 30 Teams)"):
                scatter_fig = px.scatter(
                    team_df,
                    x="OFF_RATING",
                    y="DEF_RATING",
                    text="TEAM_ABBREVIATION",
                    size="W",
                    color="NET_RATING",
                    color_continuous_scale="RdYlGn",
                    hover_data=["TEAM_NAME", "W", "L", "PTS", "TS_PCT"],
                    title=f"{season} NBA Team Efficiency Landscape (Top-Right = High Offense, Lower Y = Better Defense)"
                )
                scatter_fig.update_yaxes(autorange="reversed")
                scatter_fig.update_layout(template="plotly_dark", height=520)
                st.plotly_chart(scatter_fig, use_container_width=True)

    # ================= TAB 2: PLAYER COMPARISON =================
    with tab2:
        st.subheader("2K Head-to-Head Player Comparison")
        p_col1, p_col2 = st.columns(2)

        with p_col1:
            t1_idx = teamOptions.index("Oklahoma City Thunder") if "Oklahoma City Thunder" in teamOptions else 0
            team1 = st.selectbox("Select Player 1's Team:", options=teamOptions, index=t1_idx, key="p_team1")
            t1_obj = team_name_to_obj[team1]
            t1_players_df = player_df[player_df["TEAM_ID"] == t1_obj["id"]].sort_values("PTS", ascending=False)
            p1_names = t1_players_df["PLAYER_NAME"].tolist()
            player1 = st.selectbox("Select Player 1:", options=p1_names, key="p_name1")
            p1_row = t1_players_df[t1_players_df["PLAYER_NAME"] == player1].iloc[0]
            render_2k_player_card(p1_row, t1_obj["id"], t1_obj["abbreviation"])

        with p_col2:
            t2_idx = teamOptions.index("Los Angeles Lakers") if "Los Angeles Lakers" in teamOptions else 1
            team2 = st.selectbox("Select Player 2's Team:", options=teamOptions, index=t2_idx, key="p_team2")
            t2_obj = team_name_to_obj[team2]
            t2_players_df = player_df[player_df["TEAM_ID"] == t2_obj["id"]].sort_values("PTS", ascending=False)
            p2_names = t2_players_df["PLAYER_NAME"].tolist()
            player2 = st.selectbox("Select Player 2:", options=p2_names, key="p_name2")
            p2_row = t2_players_df[t2_players_df["PLAYER_NAME"] == player2].iloc[0]
            render_2k_player_card(p2_row, t2_obj["id"], t2_obj["abbreviation"])

        # Interactive 2K Attribute Radar Chart + Bar Chart with Player Headshots & Team Logos
        st.markdown("### 🎮 Interactive 2K Attribute Radar & Stat Breakdown")
        radar_categories = ["Scoring (PTS)", "Playmaking (AST)", "Rebounding (REB)", "Defense (STL+BLK)", "Efficiency (TS%)", "Impact (+/-)"]

        def normalize_radar(r):
            return [
                min(100, round((r["PTS"] / 35.0) * 100, 1)),
                min(100, round((r["AST"] / 11.0) * 100, 1)),
                min(100, round((r["REB"] / 14.0) * 100, 1)),
                min(100, round(((r["STL"] + r["BLK"]) / 4.0) * 100, 1)),
                min(100, round((r["TS_PCT"] / 0.70) * 100, 1)),
                min(100, max(10, round(((r["PLUS_MINUS"] + 10) / 22.0) * 100, 1)))
            ]

        g_col1, g_col2 = st.columns(2)
        with g_col1:
            radar_fig = go.Figure()
            radar_fig.add_trace(go.Scatterpolar(
                r=normalize_radar(p1_row),
                theta=radar_categories,
                fill="toself",
                name=f"{player1} ({t1_obj['abbreviation']})",
                line_color=TEAM_COLORS.get(t1_obj["abbreviation"], "#007AC1")
            ))
            radar_fig.add_trace(go.Scatterpolar(
                r=normalize_radar(p2_row),
                theta=radar_categories,
                fill="toself",
                name=f"{player2} ({t2_obj['abbreviation']})",
                line_color="#FDB927"
            ))
            radar_fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                title="2K Archetype Radar (Normalized 0-100 Ratings)",
                template="plotly_dark",
                height=440
            )
            st.plotly_chart(radar_fig, use_container_width=True)

        with g_col2:
            bar_metrics = ["PTS", "REB", "AST", "STL", "BLK", "TOV"]
            bar_fig = go.Figure()
            bar_fig.add_trace(go.Bar(
                name=player1,
                x=bar_metrics,
                y=[round(float(p1_row[m]), 1) for m in bar_metrics],
                text=[round(float(p1_row[m]), 1) for m in bar_metrics],
                textposition="outside",
                marker_color=TEAM_COLORS.get(t1_obj["abbreviation"], "#007AC1")
            ))
            bar_fig.add_trace(go.Bar(
                name=player2,
                x=bar_metrics,
                y=[round(float(p2_row[m]), 1) for m in bar_metrics],
                text=[round(float(p2_row[m]), 1) for m in bar_metrics],
                textposition="outside",
                marker_color="#FDB927"
            ))
            bar_fig.update_layout(
                title="Per-Game Box Score Head-to-Head",
                barmode="group",
                template="plotly_dark",
                height=440
            )
            st.plotly_chart(bar_fig, use_container_width=True)

        # Complete Statistical Comparison Table (All Stats)
        st.markdown("### 📋 Full Statistical Comparison Table")
        full_cols = [
            "PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "MIN", "PTS", "REB", "AST",
            "STL", "BLK", "TOV", "FG_PCT", "FG3_PCT", "FT_PCT", "TS_PCT", "USG_PCT",
            "OFF_RATING", "DEF_RATING", "NET_RATING", "PLUS_MINUS"
        ]
        comp_df = pd.DataFrame([p1_row[full_cols], p2_row[full_cols]]).copy()
        for pct_col in ["FG_PCT", "FG3_PCT", "FT_PCT", "TS_PCT", "USG_PCT"]:
            comp_df[pct_col] = (comp_df[pct_col] * 100).round(1).astype(str) + "%"
        st.dataframe(comp_df, hide_index=True, use_container_width=True)

    # ================= TAB 3: PLAYER HOMETOWN MAP =================
    with tab3:
        st.subheader("Where are players from?")
        with st.form("mapForm"):
            team = st.selectbox("Choose team:", options=teamOptions)
            submitted = st.form_submit_button("Submit Choice")
        if submitted:
            with st.spinner("Searching the world for players..."):
                mapMaking(team, season)
            st.success("Map complete!")

data()
