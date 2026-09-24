# poolToolsAILearn

Use `winget install Python.Python.3.13` in Windows PowerShell to get Python version 3.13. PoolTools from GitHub
is only available for Python versions 3.10 - 3.13.

`pool_tools.py` is a set of small wrappers around [pooltool](https://github.com/ekiefl/pooltool) for writing a pool AI.

```bash
pip install -r requirements.txt
```

Game types (see GAME_TYPES): "eightball", "nineball", "snooker", "threecushion"

Note that, "eightball" refers to American 8-ball, not English 8-ball so there
is no implementation for English 8-ball in here
```
Functions:
    Setup:
        new_game
        copy_game
        save_game
        load_game

    Display:
        display_table
        display_all
        ball_colour

    Actions:
        take_shot
        preview_shot
        randomise_balls
        place_ball

    Board state Information:
        ball_positions
        balls_on_table
        pocketed_balls
        pocketed_this_shot
        first_ball_hit

    Rules:
        current_player
        legal_targets
        ball_in_hand
        must_call_shot
        score

    Aiming:
        aim_at_ball
        aim_at_point
        aim_to_pot
        easiest_pocket
        pockets_open_to
        is_path_blocked

Examples:
    system
    ├── .cue        Cue(
    │                   id='cue_stick', cue_ball_id='cue', V0=2.0, phi=0.0, theta=0.0, a=0.0, b=0.25,
    │                   specs=CueSpecs(...))    # stick mass, length, tip size
    ├── .table      Table(
    │                   table_type=TableType.POCKET,
    │                   pockets={'lb','lc','lt','rb','rc','rt'},
    │                   cushion_segments=<18 linear + 12 circular segments>,
    │                   model_descr=..., height=..., lights_height=...)
    │                   # .w = 0.9906 and .l = 1.9812 are properties worked out from the cushions
    ├── .balls      {'7': Ball, '10': Ball, '3': Ball, ... '6': Ball, 'cue': Ball}   # 16 balls
    ├── .t          0.0      # simulation time
    └── .events     []       # filled in by pt.simulate

    Table looks like this:
            lt ──── rt
            │        │
            lc      rc
            │        │
            lb ──── rb



    system.table.cushion_segments       is a CushionSegments object with two dictionaries, .linear and .circular
    ├── .linear         '1'  : p1=[ 0.0222 -0.0508], p2=[ 0.0776 -0.0048], direction=1,   # lb jaw
    │                   '2'  : p1=[-0.0508  0.0222], p2=[-0.0048  0.0776], direction=0,   # lb jaw
    │                   ...
    │                   '18' : p1=[ 0.091   0.    ], p2=[ 0.8996  0.    ], direction=1,   # BOTTOM rail
    │
    └── .circular       '1t'  : center=[ 0.091  -0.0209], radius=0.02095,   # lb
                        ...
                        '17t' : center=[ 0.8996 -0.0209], radius=0.02095,   # rb

    Direction tells the physics engine which side of the line-segment that ball can hit
    So, `direction=0` \\implies `only check side 1`, `direction=1` \\implies `only check side 2`,
    `direction=2` \\implies `check both sides`. direction \\in {0, 1, 2}, built-in tables only use 0 and 1

    system.balls['cue']
    ├── .id         'cue'
    ├── .state      BallState(
    │                   rvw=[[0.5944, 0.4557, 0.028575],    # r: position x, y, z (m)
    │                        [0.0,    0.0,    0.0     ],    # v: velocity (m/s)
    │                        [0.0,    0.0,    0.0     ]],   # w: spin (rad/s)
    │                   s=0,    # motion states: 0 stationary, 1 spinning, 2 sliding, 3 rolling, 4 pocketed
    │                   t=0.0)  # simulation time at current state
    ├── .params     BallParams(
    │                   m=0.170097, R=0.028575, u_s=0.2, u_r=0.01, u_b=0.05,
    │                   u_sp_proportionality=0.4444,
    │                   e_b=0.95, e_c=0.85, f_c=0.2, g=9.81)
    ├── .ballset    BallSet(name='pooltool_pocket')
    │                   # .ids = ['1', '10', ..., '9', 'cue', 'shadow'] is a property read from the model folder
    ├── .initial_orientation  BallOrientation(...)          # 3D viewer rotation only
    ├── .history    BallHistory(
    │                   .states = [BallState, BallState, ...],  # per-event states after a pt.simulate
    │                   .empty = True/False
    │                   .add()
    │                   .copy()
    │                   .vectorize() --> (rvws, ss, ts))
    └── .history_cts BallHistory(states=[])                     # dense path, filled by pt.continuize

    All balls in play point to the same BallSet instance

    system.balls['cue'].params:
            .m       mass
            .R       radius
            .u_s     sliding friction ball-cloth
            .u_r     rolling friction ball-cloth
            .u_sp    spinning friction ball-cloth (calculated using u_sp_proportionality * R)
            .u_b     sliding friction ball-ball
            .e_b     restitution ball-ball
            .e_c     restitution ball-cushion
            .f_c     friction ball-cushion
            .g       gravity

    system.events       is a list of event objects, containing events of the form:
    ├── .event_type   EventType.BALL_LINEAR_CUSHION    # what happened
    ├── .time         0.3642                           # when (s after the cue strike)
    ├── .agents       (Agent, Agent)                   # what was involved
    └── .ids          ('7', '9')                       # property: ids of the agents

    system.events[i].agents     is a tuple containing the agents involved in the event, each of the form:
    ├── .agent_type   'ball'
    ├── .id           '7'
    ├── .initial      Ball      # copy from just before the event
    └── .final        Ball      # copy from just after, None for cushions and pockets

    ruleset
    ├── .players            [Player('Player 1'), Player('Player 2')]
    ├── .active_idx         0                       # index of whose turn it is
    ├── .active_player      Player('Player 1')      # property: players[active_idx]
    ├── .shot_number        0                       # shots played so far
    ├── .turn_number        0                       # goes up when the turn passes to the other player
    ├── .score              Counter()               # e.g. {'Player 1': 3, 'Player 2': 1}
    ├── .shot_constraints   ShotConstraints(...)    # what the NEXT shot must follow (below)
    ├── .shot_info          ShotInfo(...)           # result of the LAST shot, only exists after the first shot
    └── .log                messages pooltool records during play


    ruleset.shot_constraints(
        .ball_in_hand = ANYWHERE,          # ball_in_hand(ruleset)
        .movable      = ['cue'],           # balls you may place by hand
        .cueable      = ['cue'],           # ball you strike
        .hittable     = ('1', ..., '15'),  # legal_targets(ruleset)
        .call_shot    = True,              # must_call_shot(ruleset)
        .ball_call    = None,              # set by take_shot(call_ball=...)
        .pocket_call  = None,              # set by take_shot(call_pocket=...)
    )

    ruleset.shot_info(
        .player=Player('Player 1'),
        .legal=False,
        .reason='Cue ball in pocket!',
        .turn_over=True,
        .game_over=False,
        .winner=None,
        .score=Counter()
    )
```
