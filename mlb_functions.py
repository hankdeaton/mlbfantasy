import json

import pandas as pd
import requests
import statsapi
from bs4 import BeautifulSoup as bs


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

# TODO: Write a function that takes in the full tabel of ROS projections, and calculates projected Fantasy Points,
#  Fantasy Points per week, VORP and VORP per week (among other stats)