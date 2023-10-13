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
    df.fillna({'PTS': 0, 'FGA': 0, 'FTA': 0}, inplace=True)  # Fill NaN with 0 for these columns
    for col in ['PTS', 'FGA', 'FTA', 'MP']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    TSA_league = df['FGA'].sum() + 0.44 * df['FTA'].sum()
    TS_league = df['PTS'].sum() / (2 * TSA_league) * 100
    df['TSA'] = df['FGA'] + 0.44 * df['FTA']
    df['TS%'] = df['PTS'] / (2 * df['TSA']) * 100
    df['rTS%'] = df['TS%'] - TS_league
   
    
    return df

# Mapping for the season type
season_type_mapping = {
    "Regular Season": "leagues",
    "Playoffs": "playoffs"
}

# Streamlit App
st.title("NBA rTS% Calculator")

year = st.selectbox("Select Year:", list(range(1980, 2024)))
season_display = st.selectbox("Select Season Type:", ["Regular Season", "Playoffs"])

if year and season_display:
    season = season_type_mapping[season_display]
    df_player_stats = fetch_data(year, season)
    unique_teams = df_player_stats['Tm'].dropna().unique().tolist()
    unique_players = df_player_stats['Player'].dropna().unique().tolist()

    st.header("To Compare Players")
    player1 = st.selectbox("Select Player 1:", ['Select'] + unique_players)
    player2 = st.selectbox("Select Player 2:", ['Select'] + unique_players)

    if player1 != 'Select' and player2 != 'Select':
        player1_stats = df_player_stats[df_player_stats['Player'] == player1]
        player2_stats = df_player_stats[df_player_stats['Player'] == player2]
        comparison_df = pd.concat([player1_stats, player2_stats])
        comparison_df = comparison_df.round({'PTS': 1, 'TS%': 1, 'rTS%': 1})  # Rounding to 1 decimal place
        st.table(comparison_df[['Player', 'Tm', 'PTS', 'TS%', 'rTS%']])  # Displaying only desired columns

    st.header("For Individual or Teams Use Either of the Below Filters")
    team = st.selectbox("Select Team:", ['Select'] + unique_teams)
    player = st.selectbox("Select Player:", ['Select'] + unique_players)
    mp = st.slider("Select Minimum MP:", min_value=0, max_value=48)

    query = []
    if team != 'Select':
        query.append(f"Tm == '{team}'")
    if player != 'Select':
        query.append(f"Player == '{player}'")
    if mp > 0:
        query.append(f"MP >= {mp}")

    query = " & ".join(query)
    filtered_df = df_player_stats.query(query) if query else df_player_stats
    filtered_df = filtered_df.round({'PTS': 1, 'TS%': 1, 'rTS%': 1})  # Rounding to 1 decimal place
    st.table(filtered_df[['Player', 'Tm', 'PTS', 'TS%', 'rTS%']])  # Displaying only desired columns
