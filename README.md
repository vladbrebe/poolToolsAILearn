# poolToolsAILearn

Use `winget install Python.Python.3.13` in Windows PowerShell to get Python version 3.13. PoolTools from GitHub
is only available for Python versions 3.10 - 3.13.

`pool_tools.py` is a set of small wrappers around [pooltool](https://github.com/ekiefl/pooltool) for writing a pool AI.

```bash
pip install -r requirements.txt
```

```python
import pool_tools as p

system, ruleset = p.new_game("eightball")
p.display_table(system)
shot, system, info = p.take_shot(system, ruleset, V0=6, phi=p.aim_at_ball(system, "1"))
print(info.legal, info.reason, p.pocketed_this_shot(shot))
```
