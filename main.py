import mlb_functions

# Test out the get_games_left function
# print(mlb_functions.get_games_left())

# Test out the get_thebat_ros_proj function
data_df = mlb_functions.get_thebat_ros_proj()
data_adv_df = mlb_functions.calc_advanced_metrics(data_df)

data_adv_df.to_csv("adv.csv")