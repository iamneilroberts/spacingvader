# Space Invaders

A Space Invaders clone written in Python with [pygame](https://www.pygame.org/).
Built and tested on Linux. Runs on the desktop, or in a phone/desktop browser
when packaged with pygbag (with on-screen touch controls). Sound is produced
with short generated "beep" tones, so there are no audio asset files to
download.

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

**Keyboard (desktop):**

| Key | Action |
| --- | --- |
| Left / Right arrows, or A / D | Move |
| Space | Fire |
| P | Pause / resume |
| Enter | Start / restart |
| Esc | Quit |

**Touch / mouse (phone or desktop):** translucent on-screen pads sit in the
bottom corners — hold **◄ / ►** to move and tap **FIRE** to shoot. Tap anywhere
to start or restart from the menu and game-over screens.

## Play on a phone or in a browser

The desktop pygame window can't run inside a phone browser, so for mobile play
the game is packaged to WebAssembly with [pygbag](https://pypi.org/project/pygbag/)
(pygame-ce → WASM). The game loop is already async (see `main.py`), so no code
changes are needed — just build it:

```bash
pip install pygbag
pygbag main.py          # builds and serves at http://localhost:8000
```

- Open `http://localhost:8000` on the same machine to test, or
- host the generated `build/web/` folder anywhere static (GitHub Pages, Netlify,
  etc.) and open that URL on your phone — the touch controls take over.

Audio in the browser only starts after your first tap (browser autoplay policy);
that's also when the first beep fires, so it lines up naturally.

**Android, no build step:** install **Pydroid 3** from the Play Store (it ships
pip + pygame and a real display), copy `space_invaders.py` over, and run it
directly.

### Auto-deploy to a bookmarkable URL (GitHub Pages)

A workflow at `.github/workflows/deploy-web.yml` builds the pygbag bundle and
publishes it to GitHub Pages on every push. **One-time setup:** in the repo,
go to **Settings → Pages → Build and deployment → Source** and pick
**"GitHub Actions"**. After the first run the game is live at:

```
https://<owner>.github.io/spacingvader/
```

(for this repo, `https://iamneilroberts.github.io/spacingvader/`). Bookmark that
on your phone. GitHub Pages can't set cross-origin isolation headers, so the
WASM runtime runs single-threaded — which is plenty for this game.

### Optional: host on a custom domain (Cloudflare Pages)

If you'd rather have a branded URL like `invaders.voygent.ai`, deploy the same
`build/web/` folder to **Cloudflare Pages** instead. The included `web/_headers`
sets `Cross-Origin-Opener-Policy` / `Cross-Origin-Embedder-Policy` so the WASM
runtime can use threads:

```bash
pip install pygbag
pygbag --build main.py
cp web/_headers build/web/_headers
npx wrangler pages deploy build/web --project-name=spacingvader
```

Then attach the subdomain to the Pages project in the Cloudflare dashboard.

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
- **Result:** the game in `space_invaders.py` plus a pygbag entry point
  (`main.py`) for the browser/mobile build, with `README.md`,
  `requirements.txt`, and `.gitignore`.
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

**Follow-up (same session): mobile / browser support.** To make the game
playable from a phone, the loop was converted to `async` (with a per-frame
`await asyncio.sleep(0)`) and a `main.py` pygbag entry point added, so it can be
compiled to WebAssembly. On-screen touch pads (hold ◄/► to move, tap FIRE) were
added alongside the keyboard, wired to both finger and mouse events. A second
headless smoke test verified the pads (hold-to-move, sliding between pads, and
fire-replaces-bullet) and that the async loop runs and exits cleanly.
