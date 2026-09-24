import copy
import math

import pooltool as pt
from pooltool.ai.pot.core import (
    calc_potting_angle,
    is_object_ball_occluded,
    open_pockets,
    pick_easiest_pot,
)
from pooltool.ruleset.utils import (
    get_id_of_first_ball_hit,
    get_pocketed_ball_ids,
    get_pocketed_ball_ids_during_shot,
    respot,
)

GAME_TYPES = {
    "eightball": pt.GameType.EIGHTBALL,
    "nineball": pt.GameType.NINEBALL,
    "snooker": pt.GameType.SNOOKER,
    "threecushion": pt.GameType.THREECUSHION,
}


# --- Setup -------------------------------------------------------------------

def new_game(game_type="eightball", players=("Player 1", "Player 2")):
    # Sets up a racked table for the game, returns (system, ruleset)
    if game_type not in GAME_TYPES:
        raise ValueError(f"Unknown game type: {game_type}, has to be one of {list(GAME_TYPES)}")

    game_type = GAME_TYPES[game_type]
    table = pt.Table.from_game_type(game_type)
    balls = pt.get_rack(game_type, table)

    player_list = []
    for name in players:
        player_list.append(pt.Player(name))
    ruleset = pt.get_ruleset(game_type)(player_list)

    cue = pt.Cue(cue_ball_id=ruleset.shot_constraints.cueball(balls))
    system = pt.System(cue=cue, table=table, balls=balls)
    return system, ruleset


def copy_game(system, ruleset):
    # Makes a copy of the game (i.e. changing the copy does not change the original)
    return system.copy(), copy.deepcopy(ruleset)


def save_game(system, path):
    # Saves game to computer
    system.save(path)


def load_game(path):
    # Loads game from computer
    return pt.System.load(path)


# --- Display -------------------------------------------------------------------

BALL_COLOURS = {
    "1": "gold", "2": "blue", "3": "red", "4": "purple", "5": "orange",
    "6": "green", "7": "maroon", "8": "black",
    "cue": "white", "white": "white", "yellow": "gold", "green": "green",
    "brown": "saddlebrown", "blue": "blue", "pink": "hotpink", "black": "black",
    "red": "red",
}


def ball_colour(ball_id):
    # Returns (colour, is_stripe) for a ball
    # Balls 9 to 15 are the striped versions of 1 to 7, and in snooker the reds are called "red_01", "red_02" etc.
    if ball_id.isdigit() and int(ball_id) > 8:
        return BALL_COLOURS[str(int(ball_id) - 8)], True

    name = ball_id.split("_")[0]
    if name in BALL_COLOURS:
        return BALL_COLOURS[name], False
    return "grey", False


def display_table(system, ruleset=None, colour_fn=ball_colour, show_numbers=True, ax=None):
    # Draws the table from above in 2D. Close the window to carry on
    # If system is a simulated shot it also draws the path of each ball (start positions are faded)
    #
    # ruleset:      if given, the title says whose turn it is. take_shot has already moved the ruleset
    #               on to the next turn, so for a shot the title says who took it and who plays next
    # colour_fn:    function that gives (colour, is_stripe) for each ball id
    # show_numbers: draws the number on the numbered balls
    # ax:           draws onto this matplotlib axes instead of opening a new window (display_all uses this)

    # idk if there's an easier way to do this, using matplotlib for now
    # pooltools built-in viewer `pt.show()` launches the interactive 3D window
    #   from pooltool.ani.camera import camera_states
    #   pt.show(system, camera_state = camera_states["7_foot_overhead"])
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle

    table = system.table

    new_window = False
    if ax is None:
        new_window = True
        fig, ax = plt.subplots(figsize=(4, 8))  # window size

    cushion_width = 0.075
    rail_width    = 0.075   # brown wooden border outside the cushions
    outer = cushion_width + rail_width

    # The cloth goes under the pockets, so it needs to be bigger than the table by the pocket radius
    # (three cushion tables have no pockets so this stays 0)
    pocket_r = 0.0
    for pocket in table.pockets.values():
        if pocket.radius > pocket_r:
            pocket_r = pocket.radius

    # The table surface
    ax.add_patch(Rectangle((-pocket_r, -pocket_r),
                            table.w + 2 * pocket_r, table.l + 2 * pocket_r,
                            facecolor="#2e7d32"))

    # The straight cushion segments
    for linear_segment in table.cushion_segments.linear.values():
        start = linear_segment.p1[:2]
        end = linear_segment.p2[:2]

        # direction says which side the balls hit the cushion from:
        #       0 = negative side of the normal, 1 = positive side
        # so the cushion itself is on the other side, we flip the normal to point that way
        outward = linear_segment.normal[:2]
        if linear_segment.direction == 1:
            outward = -outward

        corners = [start, end, end + cushion_width * outward, start + cushion_width * outward]
        ax.add_patch(Polygon(corners, color="#285206"))

    # The circular cushion segments (i.e. the rounded ends by the pockets)
    for circular_segment in table.cushion_segments.circular.values():
        ax.add_patch(Circle(circular_segment.center[:2], circular_segment.radius, color="#285206"))

    # The 4 rails around the table
    inner = cushion_width
    rails = [
        (-outer, -outer, table.w + 2 * outer, rail_width),           # bottom rail
        (-outer, table.l + inner, table.w + 2 * outer, rail_width),  # top rail
        (-outer, -outer, rail_width, table.l + 2 * outer),           # left rail
        (table.w + inner, -outer, rail_width, table.l + 2 * outer),  # right rail
    ]
    for x, y, w, h in rails:
        ax.add_patch(Rectangle((x, y), w, h, facecolor="#5d4037"))

    # The pockets
    for pocket in table.pockets.values():
        ax.add_patch(Circle(pocket.center[:2], pocket.radius, color="black"))

    # If any ball has a history then this is a shot, so we can draw the paths
    has_history = False
    for ball in system.balls.values():
        if len(ball.history) > 0:
            has_history = True
    if has_history:
        paths = pt.continuize(system, inplace=False)

    # The balls
    for ball_id, ball in system.balls.items():
        colour, stripe = colour_fn(ball_id)
        radius = ball.params.R

        if has_history:
            # history_cts.vectorize()[0] has shape (states, 3, 3), [:, 0, :2] takes the x and y position of each state
            xy = paths.balls[ball_id].history_cts.vectorize()[0][:, 0, :2]
            ax.plot(xy[:, 0], xy[:, 1], color=colour, linewidth=1)
            ax.add_patch(Circle(xy[0], radius, facecolor=colour, edgecolor="black", alpha=0.3))

        # Pocketed balls are not drawn
        if ball.state.s == pt.constants.pocketed:
            continue

        if stripe:
            ax.add_patch(Circle(ball.xyz[:2], radius, facecolor="white", edgecolor=colour, linewidth=2))
        else:
            ax.add_patch(Circle(ball.xyz[:2], radius, facecolor=colour, edgecolor="black", linewidth=0.5))

        if show_numbers and ball_id.isdigit():
            # White numbers on the dark balls so they can be read
            if colour in ("black", "blue", "purple", "maroon") and not stripe:
                text_colour = "white"
            else:
                text_colour = "black"
            ax.annotate(ball_id, ball.xyz[:2], fontsize=6, ha="center", va="center", color=text_colour)

    ax.set_xlim(-0.2, table.w + 0.2)
    ax.set_ylim(-0.2, table.l + 0.2)

    # Title with whose turn it is
    if ruleset is not None:
        # shot_info only exists after the first shot
        if has_history and hasattr(ruleset, "shot_info"):
            last_info = ruleset.shot_info
            if last_info.game_over:
                if last_info.winner is not None:
                    winner = last_info.winner.name
                else:
                    winner = "nobody"
                ax.set_title(f"{last_info.player.name}'s shot, game over: {winner} wins")
            else:
                ax.set_title(f"{last_info.player.name}'s shot, {current_player(ruleset)} to play next")
        else:
            ax.set_title(f"{current_player(ruleset)}'s turn")

    if new_window:
        plt.show()


class FrameStack:
    # matplotlib's toolbar keeps a history of zoom levels (toolbar._nav_stack) and the Back / Forward / Home
    # buttons (and the left / right arrow keys) move through it
    # We swap it for this class so that those buttons move through our frames instead of zoom levels
    # The toolbar reads _pos and len() to know when to grey out the buttons, so these names have to stay the same
    def __init__(self, number_of_frames):
        self._pos = 0
        self.number_of_frames = number_of_frames

    def __call__(self):
        return self._pos

    def __len__(self):
        return self.number_of_frames

    def back(self):
        if self._pos > 0:
            self._pos -= 1

    def forward(self):
        if self._pos < self.number_of_frames - 1:
            self._pos += 1

    def home(self):
        self._pos = 0

    def push(self, view):
        # Zooming and panning still work, they are just not added to the history
        pass

    def clear(self):
        pass


def display_all(frames, colour_fn=ball_colour, show_numbers=True):
    # Shows a list of tables in one window using display_table
    # Use the Back / Forward arrows on the toolbar (or the left / right arrow keys) to go through them,
    # Home goes back to the first one
    #
    # frames is a list of systems or (system, ruleset) pairs, e.g. every shot in a game
    # The ruleset changes every time take_shot is called, so to get the right titles save a copy for each frame:
    #   frames.append(copy_game(shot, ruleset))
    #
    # Note: this uses toolbar._nav_stack and toolbar._update_view which are not meant to be used outside
    # matplotlib, it works on matplotlib 3.11 but might break if they change them
    import matplotlib.pyplot as plt

    if len(frames) == 0:
        raise ValueError("No frames to display")

    fig, ax = plt.subplots(figsize=(4, 8))

    def draw_frame(i):
        if isinstance(frames[i], tuple):
            system, ruleset = frames[i]
        else:
            system = frames[i]
            ruleset = None

        ax.clear()
        display_table(system, ruleset, colour_fn=colour_fn, show_numbers=show_numbers, ax=ax)
        title = ax.get_title() + f"  ({i + 1}/{len(frames)})"
        ax.set_title(title.strip())
        fig.canvas.draw_idle()

    toolbar = fig.canvas.manager.toolbar

    # There is no toolbar if there is no window (e.g. when saving to a file), then only the first frame is shown
    if toolbar is not None:
        toolbar._nav_stack = FrameStack(len(frames))

        # The buttons move the stack and then call _update_view to redraw, so we make it draw our frame
        def update_view():
            draw_frame(toolbar._nav_stack())

        toolbar._update_view = update_view
        toolbar.set_history_buttons()

    draw_frame(0)
    plt.show()


# --- Shots ---------------------------------------------------------------------

def take_shot(system, ruleset, V0, phi, theta=0.0, a=0.0, b=0.0, call_ball=None, call_pocket=None):
    # Plays a shot with the physics and the rules
    #
    # V0 = speed (m/s), phi = aim angle (degrees), theta = cue elevation (degrees)
    # a = side spin, b = top/draw spin (both as a fraction of the ball radius)
    # call_ball and call_pocket are needed when must_call_shot(ruleset) is True
    # (in 8-ball after the break, and in snooker when a colour is on)
    #
    # Returns (shot, next_system, shot_info):
    #     shot        the simulated shot with every event, used for display_table(shot),
    #                 pocketed_this_shot and first_ball_hit
    #     next_system the board for the next shot (the history is cleared so it does not keep the last shot's events)
    #     shot_info   legal, reason, turn_over, game_over, winner, score

    # shot_info only exists after the first shot
    if hasattr(ruleset, "shot_info") and ruleset.shot_info.game_over:
        raise ValueError("The game is over")
    if call_ball is not None and call_ball not in system.balls:
        raise ValueError(f"There is no ball called {call_ball}")
    if call_pocket is not None and call_pocket not in system.table.pockets:
        raise ValueError(f"There is no pocket called {call_pocket}")

    constraints = ruleset.shot_constraints
    if call_ball is not None:
        constraints.ball_call = call_ball
    if call_pocket is not None:
        constraints.pocket_call = call_pocket

    # Copy first so the cue in the system we were given is not changed
    system = system.copy()
    cue_ball_id = constraints.cueball(system.balls)
    system.cue.set_state(V0=V0, phi=phi, theta=theta, a=a, b=b, cue_ball_id=cue_ball_id)

    shot = pt.simulate(system, inplace=False)

    try:
        ruleset.process_and_advance(shot)
    except ValueError:
        # This is a pooltool bug: in snooker, once the final black is potted the respot step
        # calls min() on the colours left on the table, which is empty so it crashes
        # shot_info is already set by then and the game is over, so we can just carry on
        # If it happens any other time it is a real error so we raise it again
        if not hasattr(ruleset, "shot_info") or not ruleset.shot_info.game_over:
            raise

    next_system = shot.copy()
    next_system.reset_history()
    return shot, next_system, ruleset.shot_info


def preview_shot(system, V0, phi, theta=0.0, a=0.0, b=0.0):
    # Only the physics (no rules and the turn does not change), returns the simulated shot
    preview = system.copy()
    preview.cue.set_state(V0=V0, phi=phi, theta=theta, a=a, b=b)
    return pt.simulate(preview, inplace=False)


def randomise_balls(system):
    # Moves the balls still on the table to random places without overlapping (pocketed balls stay pocketed)
    # Note: this ignores the rules, e.g. the cue ball can end up anywhere
    worked = system.randomize_positions(balls_on_table(system))
    if not worked:
        raise RuntimeError("Could not find a layout where no balls overlap")


def place_ball(system, ball_id, x, y):
    # Puts a ball at (x, y), e.g. the cue ball when we have ball in hand
    # Checks it is on the table and not on top of another ball, but does not check the ball in hand area
    R = system.balls[ball_id].params.R

    if x < R or x > system.table.w - R or y < R or y > system.table.l - R:
        raise ValueError(f"({x}, {y}) is off the table")

    for other_id, other in system.balls.items():
        if other_id == ball_id or other.state.s == pt.constants.pocketed:
            continue
        dx = x - other.xyz[0]
        dy = y - other.xyz[1]
        distance = math.sqrt(dx ** 2 + dy ** 2)
        if distance < R + other.params.R:
            raise ValueError(f"({x}, {y}) overlaps ball {other_id}")

    respot(system, ball_id, x, y)


# --- Board state -----------------------------------------------------------------

def ball_positions(system):
    # Dictionary of {ball_id: (x, y)} for every ball
    positions = {}
    for ball_id, ball in system.balls.items():
        positions[ball_id] = (ball.xyz[0], ball.xyz[1])
    return positions


def balls_on_table(system):
    # List of the ids of the balls still on the table
    # This checks the state of each ball so it works on any system, not only on a simulated shot
    on_table = []
    for ball_id, ball in system.balls.items():
        if ball.state.s != pt.constants.pocketed:
            on_table.append(ball_id)
    return on_table


def pocketed_balls(system):
    # Every ball that is in a pocket
    return get_pocketed_ball_ids(system)


def pocketed_this_shot(shot):
    # Every ball that is pocketed during a shot
    return get_pocketed_ball_ids_during_shot(shot)


def first_ball_hit(shot):
    # First ball the cue ball hits during a shot (None if it does not hit one)
    return get_id_of_first_ball_hit(shot, cue=shot.cue.cue_ball_id)


# --- Rules -------------------------------------------------------------------------

def current_player(ruleset):
    return ruleset.active_player.name


def legal_targets(ruleset):
    return ruleset.shot_constraints.hittable


def ball_in_hand(ruleset):
    # Either 'none', 'anywhere', 'behind_line' or 'semicircle' (the D in snooker)
    # It is a BallInHandOptions, but it can be compared to a normal string, e.g. ball_in_hand(ruleset) == 'none'
    return ruleset.shot_constraints.ball_in_hand


def must_call_shot(ruleset):
    return ruleset.shot_constraints.call_shot


def score(ruleset):
    return ruleset.score


# --- Aiming ------------------------------------------------------------------------

def aim_at_ball(system, ball_id, cut=0.0):
    # Returns the angle (phi) needed to hit the ball with id ball_id
    # With cut=0 it aims at the centre of the ball, otherwise cut is the cut angle in degrees
    # (between -89 and 89, negative cuts to the left)
    return pt.aim.at_ball(system, ball_id, cut=cut)


def aim_at_point(system, x, y):
    # Returns the angle (phi) needed to hit the point (x, y)
    return pt.aim.at_pos(system, (x, y, 0.0))


def aim_to_pot(system, ball_id, pocket_id):
    # Returns the angle (phi) needed to pot ball_id in the pocket with id pocket_id
    # It aims at pooltool's potting point, which is the middle of the mouth for the middle pockets
    # and depends on the angle the ball comes in at for the corners
    # Note: it does not check if anything is in the way, and it only works on tables with pockets
    cue = system.balls[system.cue.cue_ball_id]
    ball = system.balls[ball_id]
    pocket = system.table.pockets[pocket_id]
    return calc_potting_angle(cue, ball, system.table, pocket)


def easiest_pocket(system, ball_id):
    # Returns the id of the pocket that has:
    #       - a clear path from the cue ball to ball_id
    #       - a clear path from ball_id to the pocket
    #       - room for the cue ball behind ball_id, and the jaw not in the way
    #       - a cut of 80 degrees or less
    # If more than one pocket works it returns the one with the lowest
    # precision score from `required_precision(cue_state, ball_state, table, pocket)`
    # `required_precision` gives the angle between the two jaw tips of the pocket
    # as seen from the ball (0 when the ball is lined up straight at the pocket)
    # Returns None if none of the pockets work
    pocket = pick_easiest_pot(system, system.balls[ball_id])
    if pocket is None:
        return None
    return pocket.id


def pockets_open_to(system, ball_id):
    # Set of the pockets the ball has a clear path to (any ball can block it, including the cue ball),
    # with room for the cue ball behind it and the jaw not in the way
    on_table = []
    for other_id in balls_on_table(system):
        on_table.append(system.balls[other_id])
    return open_pockets(system.balls[ball_id], system.table, on_table)


def is_path_blocked(system, ball_id, pocket_id):
    # True if another ball is in the way of the cue ball getting to where it has to hit ball_id
    # to pot it in pocket_id. Only works on tables with pockets
    cue = system.balls[system.cue.cue_ball_id]
    on_table = []
    for other_id in balls_on_table(system):
        on_table.append(system.balls[other_id])
    return is_object_ball_occluded(cue, system.balls[ball_id], system.table,
                                   system.table.pockets[pocket_id], on_table)


if __name__ == "__main__":
    mySystem, myRuleset = new_game()
    display_table(mySystem, myRuleset)

    myShot, mySystem, myShot_info = take_shot(mySystem, myRuleset, 10.0, 89.0)
    #print(myShot_info)
    display_table(myShot, myRuleset)
    display_table(mySystem, myRuleset)
