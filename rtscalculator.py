import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import requests
from st_aggrid import AgGrid

@st.cache(ttl=86400)
def fetch_data_per_75(year, season_type):
    if season_type == "leagues":
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}_per_poss.html"
    elif season_type == "playoffs":
        url = f"https://www.basketball-reference.com/playoffs/NBA_{year}_per_poss.html"
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'lxml')
    table = soup.find(name='table')
    df = pd.read_html(str(table), flavor='lxml')[0]
    
    df = df.dropna(subset=['Player', 'Tm', 'MP'])

    # Convert numerical columns to float
    for col in ['PTS', 'FGA', 'FTA', 'MP', '3PA', 'AST', 'TOV', 'TRB', 'FT%', 'G']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Apply per 75 possessions scaling
    for col in ['PTS', 'FGA', 'AST', 'TRB', '3PA', 'FTA', 'TOV']:
        df[col] = (df[col] * 0.75).round(3)

    # Retain other columns as is
    df['MP'] = (df['MP']).round(3)
    df['FT%'] = (df['FT%']).round(3)
    df['G'] = (df['G']).round(3)

    # Fill NaN values after performing conversions
    df.fillna({'PTS': 0, 'FGA': 0, 'FTA': 0, '3PA': 0, '3P': 0, '3P%': 0, 'AST': 0, 'TOV': 0, 'TRB': 0, 'FT%': 0, 'G': 0}, inplace=True)

    return df
    
@st.cache_data(ttl=86400)
def fetch_data(year, season_type):
    player_stats_url = f"https://www.basketball-reference.com/{season_type}/NBA_{year}_totals.html"
    response = requests.get(player_stats_url)
    soup = BeautifulSoup(response.content, 'lxml')
    table = soup.find(name='table')
    df = pd.read_html(str(table), flavor='lxml')[0]

    df = df.dropna(subset=['Player', 'Tm', 'MP'])  # Only drop rows where these columns are NaN

    for col in ['PTS', 'FGA', 'FTA', 'MP', '3PA', 'AST', 'TOV', 'TRB', 'FT%', 'G']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Override existing columns with per game numbers and round to 3 decimal places
    for col in ['FGA', 'PTS', 'AST', 'TRB', 'TOV', '3PA', 'FTA']:
        df[col] = (df[col] / df['G']).round(3)

    # Fill NaN values after performing conversions
    df.fillna({'PTS': 0, 'FGA': 0, 'FTA': 0, '3PA': 0, '3P': 0, '3P%': 0, 'AST': 0, 'TOV': 0, 'TRB': 0, 'FT%': 0, 'G': 0}, inplace=True)

    return df

@st.cache_data(ttl=86400)
def fetch_league_averages(input_year, season_type):
    url = f"https://www.basketball-reference.com/playoffs/NBA_{input_year}.html" if season_type == "playoffs" else f"https://www.basketball-reference.com/leagues/NBA_{input_year}.html"
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'lxml')

    # Advanced stats table for TS%
    table_advanced = soup.find('table', {'id': 'advanced_stats'})
    df_advanced = pd.read_html(str(table_advanced), flavor='lxml')[0]
    df_advanced = df_advanced[df_advanced.iloc[:, 0] == 'League Average']
    ts_col = [col for col in df_advanced.columns if 'TS%' in col][0]
    TS_percent = float(df_advanced[ts_col].values[0])

    # Per game stats table for 3P% and FT%
    table_per_game = soup.find('table', {'id': 'team-stats-per_game'})
    df_per_game = pd.read_html(str(table_per_game), flavor='lxml')[0]
    df_per_game = df_per_game[df_per_game['Team'] == 'League Average']
    tpp_col = [col for col in df_per_game.columns if '3P%' in col][0]
    ftp_col = [col for col in df_per_game.columns if 'FT%' in col][0]
    TPP = float(df_per_game[tpp_col].values[0])
    FTP = float(df_per_game[ftp_col].values[0])

    return TS_percent, TPP, FTP

@st.cache(ttl=86400)
def fetch_data_multi_years(start_year, end_year, season_type, stats_type):
    all_dfs = []
    for year in range(start_year, end_year + 1):
        if stats_type == "Per 75 Possessions":
            df = fetch_data_per_75(year, season_type)
        else:
            df = fetch_data(year, season_type)
        
        df['Year'] = year  # Tagging each entry with the year
        TS_league, TPP, FTP = fetch_league_averages(year, season_type)

        # Convert columns to numeric types
        df['3P%'] = pd.to_numeric(df['3P%'], errors='coerce') * 100
        df['3PA'] = pd.to_numeric(df['3PA'], errors='coerce')
        df['3P'] = pd.to_numeric(df['3P'], errors='coerce')
        df['FT%'] = pd.to_numeric(df['FT%'], errors='coerce') * 100
        df['FTA'] = pd.to_numeric(df['FTA'], errors='coerce')
        df['FT'] = pd.to_numeric(df['FT'], errors='coerce')

        # Calculate league-wide statistics for this specific year
        df['TS_league'] = TS_league
        league_avg_3P = TPP * 100  # Assigning value to league_avg_3P here
        df['league_avg_3P'] = league_avg_3P
        league_avg_FT = FTP * 100  # Assigning value to league_avg_FT here
        df['league_avg_FT'] = league_avg_FT

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
    weighted_avg_df = weighted_avg_df.round({'FGA':1, 'AST':1, 'TRB':1, '3PA':1, 'FTA':1, 'FT%':1, 'PTS': 1, 'TS%': 1, 'rTS%': 1, '3P%': 1, 'r3P%': 1, 'rFT%': 1, 'AST:TOV': 1, 'rAST:TOV': 1})

# Append these new rows to your existing DataFrame
    combined_df = pd.concat([combined_df, weighted_avg_df], ignore_index=True)

    return combined_df

@st.cache_data
def format_dataframe(df):

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
# Assuming your year range is from 1980 to 2025
year_range = list(range(1980, 2025))
default_start_year = 2024  # Set default start year
default_end_year = 2024    # Set default end year

# Set default values for select boxes
start_year = st.selectbox("Select Start Year:", year_range, index=year_range.index(default_start_year))
end_year = st.selectbox("Select End Year:", year_range, index=year_range.index(default_end_year))
season_display = st.selectbox("Select Season Type:", ["Regular Season", "Playoffs"])

stats_type = st.selectbox("Select Stats Type:", ["Per Game", "Per 75 Possessions"])

if start_year and end_year and season_display:
    season = "leagues" if season_display == "Regular Season" else "playoffs"
    df_player_stats = fetch_data_multi_years(start_year, end_year, season, stats_type)

    formatted_df = format_dataframe(df_player_stats)

    unique_teams = df_player_stats['Tm'].dropna().unique().tolist()
    unique_players = df_player_stats['Player'].dropna().unique().tolist()


    team = st.selectbox("Select Team:", ['Select'] + unique_teams)
    player = st.selectbox("Select Player:", ['Select'] + unique_players)
    mp = st.slider("Select Minimum MP:", min_value=0, max_value=48)
    formatted_df.loc[:, 'MP'] = pd.to_numeric(formatted_df['MP'], errors='coerce')
  
    
    query = []
    if team != 'Select':
        query.append(f"Tm == '{team}'")
    if player != 'Select':
        query.append(f'Player == "{player}"')
    if mp > 0:
        query.append(f"MP >= {mp}")  
    query = " & ".join(query)
    filtered_df = df_player_stats.query(query) if query else df_player_stats
    filtered_df.loc[:, 'MP'] = pd.to_numeric(filtered_df['MP'], errors='coerce')
    filtered_df = filtered_df.round({'FGA': 1, 'FTA': 1, 'PTS': 1, '3PA': 1, 'TRB': 1, 'AST': 1, 'TS%': 1, 'rTS%': 1, '3P%': 1, 'r3P%': 1, 'rFT%': 1, 'AST:TOV': 1, 'rAST:TOV': 1})

    gridOptions = {
        'defaultColDef': {
            'resizable': True,
            'width': 75,
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
            {'field': 'rTS%', 'width': 100},
            {'field': '3PA'},
            {'field': '3P%'},
            {'field': 'r3P%', 'width': 100},
            {'field': 'FTA'},
            {'field': 'FT%'},
            {'field': 'rFT%', 'width': 100},
            {'field': 'AST:TOV', 'width': 100},
            {'field': 'rAST:TOV', 'width': 110}
        ],
        'pagination': True,
        'paginationAutoPageSize': False,
        'paginationPageSize': 30
    }
    AgGrid(
        filtered_df[[
            'Player', 'Year', 'Tm', 'G', 'FGA', 'PTS', 
            'AST', 'TRB', 'TS%', 'rTS%', '3PA', '3P%', 
            'r3P%', 'FTA', 'FT%', 'rFT%', 'AST:TOV', 'rAST:TOV'
        ]], 
        gridOptions=gridOptions
    )

     
