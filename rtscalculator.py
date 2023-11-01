import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import requests
from st_aggrid import AgGrid


def fetch_data(year, season_type):
    player_stats_url = f"https://www.basketball-reference.com/{season_type}/NBA_{year}_per_game.html"
    response = requests.get(player_stats_url)
    soup = BeautifulSoup(response.content, 'lxml')  # or 'html5lib'
    table = soup.find(name='table', id='per_game_stats')
    df = pd.read_html(str(table), flavor='lxml')[0]
    df = df.dropna(subset=['Player', 'Tm', 'MP'])  # Only drop rows where these columns are NaN
    df.fillna({'PTS': 0, 'FGA': 0, 'FTA': 0, '3PA': 0, '3P' : 0, '3P%' : 0, 'AST': 0, 'TOV': 0, 'TRB' : 0, 'FT%': 0, 'G' : 0}, inplace=True)  # Fill NaN with 0 for these columns
    for col in ['PTS', 'FGA', 'FTA', 'MP', '3PA', 'AST', 'TOV', 'TRB', 'FT%', 'G']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

def fetch_data_multi_years(start_year, end_year, season_type):
    all_dfs = []
    for year in range(start_year, end_year + 1):
        df = fetch_data(year, season_type)
        df['Year'] = year  # Tagging each entry with the year

        # Convert columns to numeric types
        df['3P%'] = pd.to_numeric(df['3P%'], errors='coerce') * 100
        df['3PA'] = pd.to_numeric(df['3PA'], errors='coerce')
        df['3P'] = pd.to_numeric(df['3P'], errors='coerce')
        df['FT%'] = pd.to_numeric(df['FT%'], errors='coerce') * 100
        df['FTA'] = pd.to_numeric(df['FTA'], errors='coerce')
        df['FT'] = pd.to_numeric(df['FT'], errors='coerce')

        # Calculate league-wide statistics for this specific year
        TSA_league = df['FGA'].sum() + 0.44 * df['FTA'].sum()
        TS_league = df['PTS'].sum() / (2 * TSA_league) * 100
        league_avg_3P = df['3P'].sum() / df['3PA'].sum() * 100
        league_avg_FT = df['FT'].sum() / df['FTA'].sum() * 100

        # Calculate player metrics for this specific year
        df['TSA'] = df['FGA'] + 0.44 * df['FTA']
        df['TS%'] = df['PTS'] / (2 * df['TSA']) * 100
        df['rTS%'] = df['TS%'] - TS_league
        df['r3P%'] = (df['3P%'] - league_avg_3P)
        df['AST:TOV'] = df['AST'] / df['TOV'].replace(0, 1)
        df['rAST:TOV'] = df.groupby('Pos')['AST:TOV'].rank(pct=True) * 100
        df['rFT%'] = df['FT%'] - league_avg_FT

        all_dfs.append(df)

    # Concatenate all the year-specific DataFrames
    combined_df = pd.concat(all_dfs, ignore_index=True)
    # Calculate the total number of games played across all years for a specific player
    total_games = combined_df.groupby('Player')['G'].sum()

# Calculate the weighted average for each column of interest
    weighted_avg_rows = []
    for player, df_player in combined_df.groupby('Player'):
        weighted_avg_row = {}
        for col in ['PTS', 'TS%', 'rTS%', '3P%', 'r3P%', 'AST:TOV', 'rAST:TOV', 'FGA', '3PA', 'FTA', 'FT%', 'rFT%', 'AST', 'TRB']:
            weighted_avg_row[col] = (df_player[col] * df_player['G']).sum() / total_games[player]
        
    # Adding identifiers for the average row
        weighted_avg_row['Player'] = player
        weighted_avg_row['Tm'] = 'Average'
        weighted_avg_row['Year'] = 'Average'
        weighted_avg_rows.append(weighted_avg_row)

# Create a new DataFrame containing these rows
    weighted_avg_df = pd.DataFrame(weighted_avg_rows)

# Append these new rows to your existing DataFrame
    combined_df = pd.concat([combined_df, weighted_avg_df], ignore_index=True)

    return combined_df


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
- **MP**: Minutes Played
- **G**: Games Played
- **FGA**: Field Goals attempted per game
- **PTS**: Points per game
- **AST**: Assists per game
- **TRB**: Rebounds per game
- **TS%**: True Shooting Percentage - A measure of efficiency taking into account free throws as well as 3s being worth more points than 2s.
- **rTS%**: Relative True Shooting Percentage - How many percentage points above or below the league average TS% a player falls.
- **3PA**: Three-Point shots attempted per game
- **3P%**: Three-Point Percentage
- **r3P%**: Relative Three-Point Percentage - How many percentage points above or below the league average 3P% a player falls.
- **FTA**: Free Throws attempted per game
- **FT%**: Free Throw Percentage
- **rFT%**: Relative Free Throw Percentage - How many percentage points above or below the league average FT% a player falls.
- **AST/TOV**: The ratio of assist per game to turnovers per game a player has. A number over 1 indicates more assists than turnovers.
- **rAST/TOV**: Relative Assist-to-Turnover Ratio - The percentile ranking a player is at their position for their AST/TOV ratio. Adjusted for position to account for some positions naturally being less passing inclined than others. 99 = 99th percentile, aka one of the best. 50 is average.
""")

# Allow users to select a range of years
start_year = st.selectbox("Select Start Year:", list(range(1980, 2025)))
end_year = st.selectbox("Select End Year:", list(range(start_year, 2025)))
season_display = st.selectbox("Select Season Type:", ["Regular Season", "Playoffs"])

if start_year and end_year and season_display:
    st.write(f"Selected Years: {start_year} to {end_year}")  # Display the selected years
    season = season_type_mapping[season_display]
    df_player_stats = fetch_data_multi_years(start_year, end_year, season)

    
    # Format the DataFrame
    formatted_df = format_dataframe(df_player_stats)

    unique_teams = df_player_stats['Tm'].dropna().unique().tolist()
    unique_players = df_player_stats['Player'].dropna().unique().tolist()


    team = st.selectbox("Select Team:", ['Select'] + unique_teams)
    player = st.selectbox("Select Player:", ['Select'] + unique_players)
    mp = st.slider("Select Minimum MP:", min_value=0, max_value=48)
    formatted_df['MP'] = pd.to_numeric(formatted_df['MP'], errors='coerce')  
    
    query = []
    if team != 'Select':
        query.append(f"Tm == '{team}'")
    if player != 'Select':
        query.append(f'Player == "{player}"')
    if mp > 0:
        query.append(f"MP >= {mp}")  
    query = " & ".join(query)
    filtered_df = df_player_stats.query(query) if query else df_player_stats
    filtered_df['MP'] = pd.to_numeric(filtered_df['MP'], errors='coerce')  
    filtered_df = filtered_df.round({'PTS': 1, 'TS%': 1, 'rTS%': 1, '3P%': 1, 'r3P%': 1, 'rFT%': 1, 'AST:TOV': 1, 'rAST:TOV': 1})

    gridOptions = {
        'defaultColDef': {
            'resizable': True,
            'width': 100,
            'sortable': True
        },
        'columnDefs': [
            {'field': 'Player', 'pinned': 'left', 'width': 150},
            {'field': 'Year'},
            {'field': 'Tm'},
            {'field': 'G'},
            {'field': 'FGA'},
            {'field': 'PTS'},
            {'field': 'AST'},
            {'field': 'TRB'},
            {'field': 'TS%'},
            {'field': 'rTS%'},
            {'field': '3PA'},
            {'field': '3P%'},
            {'field': 'r3P%'},
            {'field': 'FTA'},
            {'field': 'FT%'},
            {'field': 'rFT%'},
            {'field': 'AST:TOV'},
            {'field': 'rAST:TOV', 'width': 110}
        ],
    }

    AgGrid(
        filtered_df[[
            'Player', 'Year', 'Tm', 'G', 'FGA', 'PTS', 
            'AST', 'TRB', 'TS%', 'rTS%', '3PA', '3P%', 
            'r3P%', 'FTA', 'FT%', 'rFT%', 'AST:TOV', 'rAST:TOV'
        ]], 
        gridOptions=gridOptions
    )
    
