import pandas as pd
import numpy as np

def finalize_loading_features(state):
    # put all together in one dataframe for scoring, polygons and points
    state.features_to_score = pd.concat([state.points, state.polygons], ignore_index=True)

    # actually all rows in this dataframe should now get an additional column named score_time and score with an empty list
    state.features_to_score['score'] = [[] for _ in range(len(state.features_to_score))]

    # add a new column with the information about the ice position relative to this point/polygon
    state.features_to_score['icecover'] = np.nan

    # sort the scores dataframe by the max_age and reset index
    state.features_to_score.sort_values(by='min_age', ascending=False, inplace=True)

    # for debugging, remove all but single entry
    # state.features_to_score = state.features_to_score.iloc[26:27] # 98 for 14C-1-7

    # very important to reset, otherwise the indices do not match later on together with the distance_array
    state.features_to_score.reset_index(drop=True, inplace=True)
