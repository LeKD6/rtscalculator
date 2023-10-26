import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import requests

def fetch_data(year, season_type):
    player_stats_url = f"https://www.basketball-reference.com/{season_type}/NBA_{year}_per_game.html"
    response = requests.get(player_stats_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find(name='table', id='per_game_stats')
    df = pd.read_html(str(table))[0]
    df = df.dropna(subset=['Player', 'Tm', 'MP'])  # Only drop rows where these columns are NaN
    df.fillna({'PTS': 0, 'FGA': 0, 'FTA': 0, '3PA': 0, '3P' : 0, '3P%' : 0, 'AST': 0, 'TOV': 0}, inplace=True)  # Fill NaN with 0 for these columns
    for col in ['PTS', 'FGA', 'FTA', 'MP', '3PA', 'AST', 'TOV']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['3P%'] = pd.to_numeric(df['3P%'], errors='coerce') * 100
    df['3PA'] = pd.to_numeric(df['3PA'], errors='coerce')
    df['3P'] = pd.to_numeric(df['3P'], errors='coerce')

    # Calculate league-wide statistics
    TSA_league = df['FGA'].sum() + 0.44 * df['FTA'].sum()
    TS_league = df['PTS'].sum() / (2 * TSA_league) * 100
    league_avg_3P = df['3P'].sum() / df['3PA'].sum() * 100
    
    # Calculate player metrics
    df['TSA'] = df['FGA'] + 0.44 * df['FTA']
    df['TS%'] = df['PTS'] / (2 * df['TSA']) * 100
    df['rTS%'] = df['TS%'] - TS_league
    df['r3P%'] = (df['3P%'] - league_avg_3P) 
    df['AST:TOV'] = df['AST'] / df['TOV'].replace(0, 1)  # replace 0 with 1 to avoid division by zero
    
    # Calculate rA:T based on positions
    df['rAST:TOV'] = df.groupby('Pos')['AST:TOV'].rank(pct=True) * 100    

    return df

def format_dataframe(df):
    for col in df.select_dtypes(include=[float]).columns:
        df[col] = df[col].apply(lambda x: '{:.2f}'.format(x))
    return df
# Mapping for the season type
season_type_mapping = {
    "Regular Season": "leagues",
    "Playoffs": "playoffs"
}

# Streamlit App
st.title("NBA Advanced Stats Calculator")

# Add glossary to the sidebar
st.sidebar.title("Glossary")
st.sidebar.markdown("""
- **PTS**: Points
- **MP**: Minutes Played
- **TS%**: True Shooting Percentage - A measure of efficiency taking into account free throws as well as 3s being worth more points than 2s.
- **rTS%**: Relative True Shooting Percentage - How many percentage points above or below the league average TS% a player falls.
- **3P%**: Three-Point Percentage
- **r3P%**: Relative Three-Point Percentage - How many percentage points above or below the league average 3P% a player falls.
- **AST/TOV**: The ratio of assist per game to turnovers per game a player has. A number over 1 indicates more assists than turnovers.
- **rAST/TOV**: Relative Assist-to-Turnover Ratio - The percentile ranking a player is at their position for their AST/TOV ratio. Adjusted for position to account for some positions naturally being less passing inclined than others. 99 = 99th percentile, aka one of the best. 50 is average.
""")


year = st.selectbox("Select Year:", list(range(1980, 2025)))
season_display = st.selectbox("Select Season Type:", ["Regular Season", "Playoffs"])

if year and season_display:
    season = season_type_mapping[season_display]
    df_player_stats = fetch_data(year, season)
    
    # Format the DataFrame
    formatted_df = format_dataframe(df_player_stats)

    unique_teams = df_player_stats['Tm'].dropna().unique().tolist()
    unique_players = df_player_stats['Player'].dropna().unique().tolist()

    st.header("To Compare Players")
    player1 = st.selectbox("Select Player 1:", ['Select'] + unique_players)
    player2 = st.selectbox("Select Player 2:", ['Select'] + unique_players)

    if player1 != 'Select' and player2 != 'Select':
        comparison_df = pd.concat([df_player_stats[df_player_stats['Player'] == player1], 
                                   df_player_stats[df_player_stats['Player'] == player2]])
        comparison_df = comparison_df.round({'PTS': 1, 'TS%': 1, 'rTS%': 1, '3P%': 1, 'r3P%': 1, 'AST:TOV': 1, 'rA:T': 1})
        st.table(comparison_df[['Player', 'Tm', 'PTS', 'TS%', 'rTS%', '3P%', 'r3P%', 'AST:TOV', 'rAST:TOV']])

    st.header("For Individual or Teams Use Either of the Below Filters")
    team = st.selectbox("Select Team:", ['Select'] + unique_teams)
    player = st.selectbox("Select Player:", ['Select'] + unique_players)
    mp = st.slider("Select Minimum MP:", min_value=0, max_value=48)

    query = []
    if team != 'Select':
        query.append(f"Tm == '{team}'")
    if player != 'Select':
        query.append(f'Player == "{player}"')
    if mp > 0:
        query.append(f"MP >= {mp}")
        
    query = " & ".join(query)
    filtered_df = df_player_stats.query(query) if query else df_player_stats
    filtered_df = filtered_df.round({'PTS': 1, 'TS%': 1, 'rTS%': 1, '3P%': 1, 'r3P%': 1, 'AST:TOV': 1, 'rAST:TOV': 1})
    st.table(filtered_df[['Player', 'Tm', 'PTS', 'TS%', 'rTS%', '3P%', 'r3P%', 'AST:TOV', 'rAST:TOV']])
