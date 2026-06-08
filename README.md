# Space Invaders

A Space Invaders clone written in Python with [pygame](https://www.pygame.org/).
Built and tested on Linux. Sound is produced with short generated "beep" tones,
so there are no audio asset files to download.

## Features

- **Marching alien grid** that moves side to side and **drops one level** when
  the group hits either wall, then reverses.
- **4 shield bases** you can hide behind. They **erode block-by-block** as they
  take hits from either side.
- **Bonus UFO** that flies across the top at random intervals — shoot it for
  extra points (50/100/150/300).
- **One player bullet at a time.** Press fire again and your current shot is
  cancelled and replaced by a fresh one.
- **Aliens fire in small volleys** — 1 to 4 shots at a time from the whole
  group, with a cap on how many can be in the air. No bullet storm.
- **Aliens speed up** as their numbers thin out (and each cleared wave is a
  little faster than the last).

## Install & run

```bash
pip install -r requirements.txt
python3 space_invaders.py
```

If you don't have audio hardware (e.g. running headless), the game detects that
and runs silently rather than crashing.

## Controls

| Key | Action |
| --- | --- |
| Left / Right arrows, or A / D | Move |
| Space | Fire |
| P | Pause / resume |
| Enter | Start / restart |
| Esc | Quit |

## Scoring

- Aliens: 40 / 30 / 20 / 10 / 10 points by row (top rows worth more).
- UFO: 50, 100, 150, or 300 points (random).

Clearing all aliens starts the next, faster wave. The game ends when you run out
of lives or the aliens reach your line.
