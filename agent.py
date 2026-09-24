# Hello Jacob my beloved I hope this is documented enough
from pool_tools import (
    # Starting a game and resetting it (i.e. starting a new episode)
    new_game,
    copy_game,
    randomise_balls,
    place_ball,         # also needed when the agent has ball in hand

    # Actions
    take_shot,          # a real shot, uses the physics and the rules and moves the game on
    preview_shot,       # only the physics, so we can try shots out without changing the game

    # Observations (i.e. what the board looks like)
    ball_positions,
    balls_on_table,
    pocketed_balls,

    # What happened in the shot (for the rewards)
    pocketed_this_shot,
    first_ball_hit,
    score,              # the shot_info from take_shot also has legal, reason, turn_over, game_over and winner

    # Rules (what the agent is allowed to do)
    current_player,
    legal_targets,
    ball_in_hand,
    must_call_shot,

    # Aiming (turns "pot ball X in pocket Y" into a phi angle, also useful for making simple players to test against)
    aim_at_ball,
    aim_at_point,
    aim_to_pot,
    easiest_pocket,
    pockets_open_to,
    is_path_blocked,

    # Watching the agent play
    display_table,
    display_all,
)
