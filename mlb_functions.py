import json

import numpy as np
import pandas as pd
import requests
import statsapi
from bs4 import BeautifulSoup as bs


def get_replacements(all_df):
    # Function to get the replacement level players theoretically left over

    roster = ["C", "2B", "SS", "3B", "1B", "OF", "OF", "OF", "2B|SS", "1B|3B", "C|1B|2B|3B|SS|OF|DH", "C|1B|2B|3B|SS|OF|DH",
              "C|1B|2B|3B|SS|OF|DH"]

    # remove all the starters
    for r in roster:
        first12 = all_df[all_df['Positions'].str.contains(r)].index[0:12]  # Get the first 12 in the list

        # print(first12)

        all_df = all_df.drop(all_df.index[first12])  # remove the first 12
        all_df = all_df.reset_index(drop=True)

    return all_df


def get_yahoo_positions():
    # Function to create a table of player positions based on Yahoo fantasy baseball

    pos_df = pd.read_csv("draft-tools/fp_hit.csv")  # Read in Fantasypros data (for positions)
    pos_df["PlayerName"] = pos_df["Player"]
    pos_df = pos_df[["PlayerName", "Positions", "Rank", "ADP"]]
    pos_df['Positions'] = pos_df['Positions'].str.replace('LF', 'OF')
    pos_df['Positions'] = pos_df['Positions'].str.replace('CF', 'OF')
    pos_df['Positions'] = pos_df['Positions'].str.replace('RF', 'OF')

    pos_df = pos_df[['PlayerName', 'Positions']]

    return pos_df


def get_games_left():
    # Function to get a pandas dataframe of each team's remaining number of games

    # MLB Stats API Call for current Standings
    standings = statsapi.standings_data(leagueId="103,104", division="all", include_wildcard=True, season=None,
                                        standingsTypes=None, date=None)

    # For loop to gather games played and games left for each MLB team
    tm_games = []
    for div in standings:
        # print(type(standings[div]))
        for team in standings[div]["teams"]:
            tm_name = team.get("name")
            tm_id = team.get("team_id")
            tm_g = int(team.get("w")) + int(team.get("l"))
            tm_gl = 162 - tm_g

            tm_games.append([tm_name, tm_id, tm_g, tm_gl])

    # Convert 2d list to a pandas df
    tm_games_df = pd.DataFrame(tm_games, columns=['name', 'team_id', 'G', 'GL'])

    return tm_games_df


def get_thebat_ros_proj():
    # Function to get THE BAT rest of season projections for all batters

    # Ge the source code from Fangraphs website
    r = requests.get("https://www.fangraphs.com/projections?pos=all&stats=bat&type=rthebat", verify=False)

    # Convert it via beautiful soup, get the dictionary of player stats contained under the __NEXT_DATA__ field
    soup = bs(r.content, "html.parser")
    results = soup.find(id="__NEXT_DATA__")

    # Convert to json to parce the dictionary
    json_data = json.loads(results.string)

    # print(json_data['props']['appProps'].keys()) # prints out irrelevant material
    # keys: dict_keys(['appProps', '__N_SSP', 'pageProps'])

    # print(json_data['props']['pageProps'].keys())
    # dict_keys(['dehydratedState', 'qsContext', 'loaddate'])

    # print(type(json_data['props']['pageProps']['dehydratedState']['queries']))
    # this is a list, but of a single....dict

    # print(json_data['props']['pageProps']['dehydratedState']['queries'][0].keys())
    # dict_keys(['state', 'queryKey', 'queryHash'])

    # print(type(json_data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']))
    # this is finally a list of the players!
    hitproj_l = json_data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']

    # convert it to a pandas dataframe
    hitproj_df = pd.DataFrame.from_dict(hitproj_l)

    # print to a csv if you want
    # hitproj_df.to_csv("hitter_proj.csv")

    return hitproj_df


def calc_top_n(rep_df, N):
    # Function to calculate average of the top N players at each position
    ps = ["C", "1B", "2B", "3B", "SS", "OF"]
    rpv = pd.DataFrame(columns=['Position', 'RPV'])
    for p in ps:
        rp = rep_df[rep_df['Positions'].str.contains(p)][0:N]  # get the first five from the replacement player list
        rpv = rpv.append({'Position': p, 'RPV': np.mean(rp["FPpg"])}, ignore_index=True)

    return rpv


def calc_advanced_metrics(hitproj_df):
    # function that calculates advanced metrics (fantasy points, fantasy points per week, VORP, vorp per wwek, etc)

    # Get the number of games left for each team
    gamesleft_df = get_games_left()
    gamesleft_df['ShortName'] = gamesleft_df["name"].str.split().str[-1]
    gamesleft_df['ShortName'] = np.where(
        gamesleft_df['name'] == "Boston Red Sox",
        'Red Sox', gamesleft_df['ShortName']
    )
    gamesleft_df['ShortName'] = np.where(
        gamesleft_df['name'] == "Chicago White Sox",
        'White Sox', gamesleft_df['ShortName']
    )
    gl_df = gamesleft_df[['ShortName', 'GL']]

    # join games left on the projections
    hitproj_df = hitproj_df.merge(gl_df, on='ShortName', how='left')

    # Get list of positions in Yahoo, and left join on the projections DataFrame
    y_pos = get_yahoo_positions() # TODO remove accents marks for joins
    hitproj_df['PlayerName'] = hitproj_df['PlayerName'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    hitproj_df = hitproj_df.merge(y_pos, on='PlayerName', how='left')
    hitproj_df['Positions'] = hitproj_df['Positions'].fillna('N/A')

    hitproj_df['FP'] = hitproj_df['1B'] + 2 * hitproj_df['2B'] + 3 * hitproj_df['3B'] + 5 * hitproj_df['HR'] + \
                       hitproj_df['R'] + hitproj_df['RBI'] + hitproj_df['SB'] + hitproj_df['BB'] - 0.5 * hitproj_df[
                           'SO']

    # Sort on Fantasy Points
    hitproj_df = hitproj_df.sort_values(by=['FP'], ascending=False)
    hitproj_df = hitproj_df.reset_index(drop=True)

    # Calc the percentage of remaining games they are expected to play in
    hitproj_df['G/GL'] = hitproj_df['G'] / hitproj_df['GL']
    # hitproj_df = hitproj_df.clip(upper=pd.Series({'G/GL': 1}), axis=1) # TODO limit this to 1.0 max

    # calc the Fantasy Points per game
    hitproj_df['FPpg'] = hitproj_df['FP'] / hitproj_df['G']

    # Calc the fantasy points per week (assuming 6.2 games per week)
    hitproj_df['FPpw'] = hitproj_df['FPpg'] * 6.2 * hitproj_df['G/GL']

    # Estimate the level of free agent in league (i.e. available replacement level player
    reps_df = get_replacements(hitproj_df)
    reps_df.to_csv("reps.csv")

    # Calculate the replacement level value at each position
    rep_val_df = calc_top_n(reps_df, 5)
    rep_val_df = rep_val_df.sort_values(by=['RPV'], ascending=False)    # sort in descending order FPpg

    # Calculate VORP stats
    hitproj_df["VORPpg"] = 0
    for index, row in rep_val_df.iterrows():
        hitproj_df.loc[hitproj_df['Positions'].str.contains(row["Position"]), ["VORPpg"]] = hitproj_df["FPpg"] - row["RPV"]
    hitproj_df["aVORPpg"] = hitproj_df["VORPpg"] * hitproj_df["G"] / hitproj_df["GL"]
    hitproj_df["aVORPpw"] = hitproj_df["aVORPpg"] * 6.2
    hitproj_df["VORPpw"] = hitproj_df["VORPpg"] * 6.2

    hitproj_df = hitproj_df.sort_values(by=['aVORPpw'], ascending=False)

    return hitproj_df
