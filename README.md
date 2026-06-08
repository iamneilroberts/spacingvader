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

## Build provenance

This game was built in a single Claude Code session.

- **Date:** 2026-06-08
- **Model:** `claude-opus-4-8` (1M context)
- **Language / engine:** Python 3.11, pygame 2.6.1
- **Result:** one self-contained file (`space_invaders.py`, ~560 lines) plus
  `README.md`, `requirements.txt`, and `.gitignore`.
- **Wall-clock time:** _<fill in from session>_
- **Token usage:** _<fill in from session — input / output / total>_

> The time and token figures above are only visible in the Claude Code client
> UI, so they're left as placeholders to be filled in from the session stats.

### Original prompt

> I need you to write me a space invaders clone.
>
> Details it should have include:
>
> - aliens that drop one level when the group hits either side of the screen
> - 4 shield bases the player can hide behind for cover and get smaller when they are hit
> - UFO that appears randomly that can be shot for extra points
> - single bullet in the air at a time from the player base. If the player hits the button again, his bullet disappears and a new one appears.
> - aliens firing at random. Don't make it a bullet storm. The fire maybe 1 to 4 rounds at a time from the whole group.
> - Aliens that get faster the less of them that are
> - Use Pythons beeps for sound. Pygame as I am on Linux.

### Build log

The implementation came together in a single straight-through pass:

1. **Explored the workspace.** Found the `spacingvader` repo empty (a fresh
   clone with only `.git`) and the working branch already checked out — a clean
   home for the game.
2. **Wrote `space_invaders.py`** in one pass: the `Beeper` tone generator, then
   the `Player`, `Bullet`, `Alien`, `Ufo`, and `Shield` objects, then the `Game`
   loop (state machine for menu / playing / paused / game-over).
3. **Compile check** (`python3 -m py_compile`) — clean. pygame wasn't installed
   yet, so the import failed at this point.
4. **Installed pygame** (2.6.1) to enable real testing.
5. **Headless smoke test** using SDL's `dummy` video/audio drivers, exercising
   the actual update loop rather than just imports. Verified each requested
   mechanic:
   - 55 aliens and 4 shields spawn correctly.
   - March interval shrinks as aliens die (700 ms → 107 ms after 50 kills) —
     confirms the speed-up.
   - Firing replaces the existing bullet object (single-bullet rule).
   - A shield loses blocks when hit (erosion).
   - Killing an alien scores points.
   - Alien volleys are bounded to 1–4 and never exceed the in-air cap of 6.
   - Hitting a wall reverses the group's direction.
   - A 3000-tick run completes with no crashes and progresses cleanly.
6. **Added `README.md`, `requirements.txt`, `.gitignore`**, staged each file by
   name, committed, and pushed to the feature branch.

No render-on-a-real-display check was possible from the headless build
environment; correctness was established through the logic-level smoke test
above. All tunable gameplay constants live at the top of `space_invaders.py`.
