"""
A simple player that plays a whole game of 8-ball against itself.

Every turn it:
    1. Checks if it has ball in hand, if so it places the cue ball
    2. Finds all the legal balls it can hit
    3. Pots the easiest one it can
    4. If it cannot pot any it just aims at one and hits it
    5. Calls the ball and pocket (when the rules say it has to)

At the end every shot is shown in one window, use the arrows on the toolbar to go through them.
"""

import random

from agent import (
    aim_at_ball, aim_to_pot, ball_in_hand, balls_on_table, copy_game, current_player,
    display_all, easiest_pocket, legal_targets, must_call_shot, new_game, place_ball,
    pocketed_this_shot, take_shot,
)

system, ruleset = new_game("eightball")

# We save a copy of (system, ruleset) for every frame, otherwise the next shots would change them
# and display_all would show the wrong player in the titles
frames = []
frames.append(copy_game(system, ruleset))

# The break, we hit the rack hard straight up the table
shot, system, info = take_shot(system, ruleset, V0=8.0, phi=90.0)
frames.append(copy_game(shot, ruleset))
print(f"{info.player.name} breaks: potted {pocketed_this_shot(shot)}")

for shot_number in range(1, 200):
    # This is checked at the start so it also works if the game ends on the break (e.g. the 8 goes in)
    if info.game_over:
        if info.winner is not None:
            print(f"Game over, {info.winner.name} wins")
        else:
            print("Game over, nobody wins")
        break

    player = current_player(ruleset)

    # Ball in hand after a foul, so we put the cue ball somewhere random that is free
    if ball_in_hand(ruleset) != "none":
        placed = False
        while not placed:
            x = random.uniform(0.1, system.table.w - 0.1)
            y = random.uniform(0.1, system.table.l / 4)
            try:
                place_ball(system, "cue", x, y)
                placed = True
            except ValueError:
                # It was on top of another ball, so we try again
                pass

    # The balls we are allowed to hit that are still on the table
    targets = []
    for ball_id in legal_targets(ruleset):
        if ball_id in balls_on_table(system):
            targets.append(ball_id)

    # This should not happen, but if there are none we hit any ball instead of crashing
    if len(targets) == 0:
        for ball_id in balls_on_table(system):
            if ball_id != system.cue.cue_ball_id:
                targets.append(ball_id)

    # Go through the targets until we find one that can be potted
    target = targets[0]
    pocket = None
    for ball_id in targets:
        pocket = easiest_pocket(system, ball_id)
        if pocket is not None:
            target = ball_id
            break

    if pocket is not None:
        phi = aim_to_pot(system, target, pocket)
    else:
        # Nothing can be potted so we just hit a legal ball
        phi = aim_at_ball(system, target)
        pocket = "lt"   # we still have to call a pocket in some games

    if must_call_shot(ruleset):
        call_ball = target
        call_pocket = pocket
    else:
        call_ball = None
        call_pocket = None

    shot, system, info = take_shot(system, ruleset, V0=2.5, phi=phi,
                                   call_ball=call_ball, call_pocket=call_pocket)
    frames.append(copy_game(shot, ruleset))

    print(f"{shot_number:3} {player}: {target} -> {pocket}, potted {pocketed_this_shot(shot)}, "
          f"legal={info.legal} {info.reason}")

# Go through the shots with the back / forward arrows on the toolbar
display_all(frames)
