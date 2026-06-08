#!/usr/bin/env python3
"""
Space Invaders clone (pygame).

Features:
  * Alien grid that marches side to side and drops one level when it hits a wall.
  * 4 shield bases the player can hide behind; they erode block-by-block when hit.
  * A UFO that appears at random across the top and is worth bonus points.
  * A single player bullet at a time -- firing again cancels the old shot and
    launches a fresh one.
  * Aliens fire in small volleys (1-4 shots at a time from the whole group),
    not a constant bullet storm.
  * Aliens speed up as their numbers thin out.
  * Sound via short generated "beep" tones (no audio files needed), which works
    well on Linux through pygame's mixer.

Controls (keyboard):
  Left / Right arrows (or A / D) : move
  Space                          : fire
  P                              : pause
  Enter                          : start / restart
  Esc                            : quit

Controls (touch / mouse):
  On-screen buttons at the bottom: hold left/right to move, tap FIRE to shoot.
  Tap anywhere to start or restart from the menu / game-over screens.

Runs on the desktop directly (`python3 space_invaders.py`) and in a web/mobile
browser when packaged with pygbag (the loop is async; see main.py and README).
"""

import asyncio
import math
import random
import struct

import pygame

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 800, 600
FPS = 60

BLACK = (0, 0, 0)
WHITE = (235, 235, 235)
GREEN = (60, 230, 90)
CYAN = (80, 220, 235)
YELLOW = (240, 220, 70)
RED = (235, 70, 70)
MAGENTA = (220, 90, 200)

# Player
PLAYER_W, PLAYER_H = 46, 20
PLAYER_SPEED = 6
PLAYER_Y = SCREEN_H - 60
PLAYER_BULLET_SPEED = 10

# Aliens
ALIEN_ROWS = 5
ALIEN_COLS = 11
ALIEN_W, ALIEN_H = 32, 24
ALIEN_H_GAP = 16
ALIEN_V_GAP = 14
ALIEN_X_STEP = 10          # pixels moved per "march" tick
ALIEN_DROP = 20            # pixels dropped when the group hits a wall
ALIEN_BULLET_SPEED = 5
ALIEN_TOP = 80
ALIEN_LEFT = 60

# Marching speed: milliseconds between steps. The group moves faster as fewer
# aliens remain -- interpolated between these two bounds.
MARCH_INTERVAL_FULL = 700   # all aliens alive: slow
MARCH_INTERVAL_ONE = 60     # one alien left: frantic

# Alien fire: small volleys, occasionally, with a cap on bullets in the air.
ALIEN_FIRE_MIN_MS = 800
ALIEN_FIRE_MAX_MS = 2000
ALIEN_VOLLEY_MIN = 1
ALIEN_VOLLEY_MAX = 4
ALIEN_BULLET_CAP = 6

# UFO
UFO_W, UFO_H = 48, 20
UFO_SPEED = 3
UFO_MIN_MS = 8000
UFO_MAX_MS = 18000

# Shields
SHIELD_COUNT = 4
SHIELD_BLOCK = 6           # size of each erodable block in pixels
SHIELD_Y = SCREEN_H - 150

# Row point values (top rows worth more), classic-style.
ROW_POINTS = [40, 30, 20, 10, 10]
UFO_POINTS = [50, 100, 150, 300]


# ---------------------------------------------------------------------------
# Sound -- generate simple square-wave beeps so no asset files are needed.
# ---------------------------------------------------------------------------
class Beeper:
    """Generates short tones on the fly using pygame's mixer."""

    def __init__(self):
        self.enabled = False
        self.sample_rate = 22050
        try:
            pygame.mixer.pre_init(self.sample_rate, -16, 1, 512)
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            # No audio device (e.g. headless). Game still runs, just silent.
            self.enabled = False
        self._cache = {}

    def _tone(self, freq, ms, volume=0.35, wave="square"):
        """Build (and cache) a pygame Sound for a tone."""
        key = (freq, ms, round(volume, 3), wave)
        if key in self._cache:
            return self._cache[key]

        n_samples = int(self.sample_rate * ms / 1000.0)
        amp = int(32767 * volume)
        buf = bytearray()
        for i in range(n_samples):
            t = i / self.sample_rate
            if wave == "square":
                val = amp if math.sin(2 * math.pi * freq * t) >= 0 else -amp
            elif wave == "saw":
                frac = (freq * t) % 1.0
                val = int(amp * (2 * frac - 1))
            else:  # sine
                val = int(amp * math.sin(2 * math.pi * freq * t))
            # Quick linear fade-out to avoid clicks at the tail.
            fade = min(1.0, (n_samples - i) / max(1, n_samples * 0.2))
            val = int(val * fade)
            buf += struct.pack("<h", val)

        sound = pygame.mixer.Sound(buffer=bytes(buf))
        self._cache[key] = sound
        return sound

    def play(self, freq, ms, volume=0.35, wave="square"):
        if not self.enabled:
            return
        try:
            self._tone(freq, ms, volume, wave).play()
        except pygame.error:
            pass

    # Named effects ---------------------------------------------------------
    def shoot(self):
        self.play(880, 70, 0.25, "square")

    def alien_die(self):
        self.play(160, 120, 0.4, "saw")

    def player_die(self):
        self.play(110, 450, 0.5, "saw")

    def ufo_die(self):
        self.play(660, 200, 0.4, "sine")

    def shield_hit(self):
        self.play(220, 40, 0.2, "square")

    def march(self, step):
        # Four-note marching loop like the original.
        notes = [70, 80, 90, 100]
        self.play(notes[step % 4], 60, 0.18, "square")


# ---------------------------------------------------------------------------
# Game objects
# ---------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, PLAYER_W, PLAYER_H)
        self.rect.centerx = SCREEN_W // 2
        self.rect.top = PLAYER_Y
        self.lives = 3

    def move(self, dx):
        self.rect.x += dx
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_W, SCREEN_H))

    def draw(self, surf):
        # Body + a little cannon barrel.
        pygame.draw.rect(surf, GREEN, self.rect, border_radius=4)
        barrel = pygame.Rect(0, 0, 6, 10)
        barrel.centerx = self.rect.centerx
        barrel.bottom = self.rect.top + 4
        pygame.draw.rect(surf, GREEN, barrel)


class Bullet:
    def __init__(self, x, y, vy, color):
        self.rect = pygame.Rect(0, 0, 4, 12)
        self.rect.center = (x, y)
        self.vy = vy
        self.color = color

    def update(self):
        self.rect.y += self.vy

    def offscreen(self):
        return self.rect.bottom < 0 or self.rect.top > SCREEN_H

    def draw(self, surf):
        pygame.draw.rect(surf, self.color, self.rect)


class Alien:
    def __init__(self, col, row, x, y):
        self.col = col
        self.row = row
        self.rect = pygame.Rect(x, y, ALIEN_W, ALIEN_H)
        self.alive = True
        self.points = ROW_POINTS[row] if row < len(ROW_POINTS) else 10
        # Use row to pick a color/shape variant.
        self.color = [MAGENTA, CYAN, CYAN, GREEN, GREEN][row % 5]

    def draw(self, surf, frame):
        r = self.rect
        pygame.draw.rect(surf, self.color, r, border_radius=3)
        # Eyes.
        eye = 4
        ey = r.y + 7
        pygame.draw.rect(surf, BLACK, (r.x + 8, ey, eye, eye))
        pygame.draw.rect(surf, BLACK, (r.right - 12, ey, eye, eye))
        # Animated legs (two-frame).
        leg_y = r.bottom - 4
        if frame % 2 == 0:
            pygame.draw.rect(surf, self.color, (r.x + 4, leg_y, 4, 4))
            pygame.draw.rect(surf, self.color, (r.right - 8, leg_y, 4, 4))
        else:
            pygame.draw.rect(surf, self.color, (r.x + 10, leg_y, 4, 4))
            pygame.draw.rect(surf, self.color, (r.right - 14, leg_y, 4, 4))


class Ufo:
    def __init__(self, direction):
        self.rect = pygame.Rect(0, 0, UFO_W, UFO_H)
        self.rect.top = 40
        self.direction = direction
        if direction > 0:
            self.rect.right = 0
        else:
            self.rect.left = SCREEN_W
        self.points = random.choice(UFO_POINTS)

    def update(self):
        self.rect.x += UFO_SPEED * self.direction

    def offscreen(self):
        return self.rect.left > SCREEN_W or self.rect.right < 0

    def draw(self, surf):
        r = self.rect
        pygame.draw.ellipse(surf, RED, r)
        dome = pygame.Rect(0, 0, UFO_W // 2, UFO_H)
        dome.center = (r.centerx, r.centery - 4)
        pygame.draw.ellipse(surf, YELLOW, dome)


class Shield:
    """A shield made of small erodable blocks arranged in a classic bunker shape."""

    # 1 = block present. Shape is a rounded bunker with a notch in the bottom.
    PATTERN = [
        "0011111100",
        "0111111110",
        "1111111111",
        "1111111111",
        "1111111111",
        "1111001111",
        "1110000111",
        "1100000011",
    ]

    def __init__(self, cx, top):
        self.blocks = []
        for ry, line in enumerate(self.PATTERN):
            for cxi, ch in enumerate(line):
                if ch == "1":
                    bx = cx - (len(line) * SHIELD_BLOCK) // 2 + cxi * SHIELD_BLOCK
                    by = top + ry * SHIELD_BLOCK
                    self.blocks.append(pygame.Rect(bx, by, SHIELD_BLOCK, SHIELD_BLOCK))

    def hit(self, bullet_rect):
        """Remove blocks the bullet overlaps. Returns True if anything was hit.

        Erodes a small splash radius so impacts feel chunky, like the original.
        """
        hit_index = bullet_rect.collidelist(self.blocks)
        if hit_index == -1:
            return False
        impact = self.blocks[hit_index].copy()
        # Erode a small area around the impact point.
        splash = impact.inflate(SHIELD_BLOCK, SHIELD_BLOCK)
        self.blocks = [b for b in self.blocks if not b.colliderect(splash)]
        return True

    def draw(self, surf):
        for b in self.blocks:
            pygame.draw.rect(surf, GREEN, b)


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.beeper = Beeper()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Space Invaders")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 22, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 52, bold=True)
        self.state = "menu"   # menu | playing | paused | gameover | win
        self.high_score = 0

        # On-screen touch controls (also usable with the mouse). Placed in the
        # bottom corners so they don't sit on top of the cannon at center.
        self.left_btn = pygame.Rect(20, SCREEN_H - 72, 72, 58)
        self.right_btn = pygame.Rect(104, SCREEN_H - 72, 72, 58)
        self.fire_btn = pygame.Rect(SCREEN_W - 116, SCREEN_H - 72, 96, 58)
        # finger_id / "mouse" -> "left" | "right" for currently-held moves.
        self.active_touches = {}
        self.touch_left = False
        self.touch_right = False

        self.reset()

    # -- setup -------------------------------------------------------------
    def reset(self):
        self.player = Player()
        self.player_bullet = None
        self.alien_bullets = []
        self.aliens = self._make_aliens()
        self.direction = 1            # 1 = right, -1 = left
        self.shields = self._make_shields()
        self.ufo = None
        self.score = 0
        self.level = 1
        self.march_step = 0
        self.frame = 0

        now = pygame.time.get_ticks()
        self.last_march = now
        self.next_alien_fire = now + random.randint(ALIEN_FIRE_MIN_MS, ALIEN_FIRE_MAX_MS)
        self.next_ufo = now + random.randint(UFO_MIN_MS, UFO_MAX_MS)

    def _make_aliens(self):
        aliens = []
        for row in range(ALIEN_ROWS):
            for col in range(ALIEN_COLS):
                x = ALIEN_LEFT + col * (ALIEN_W + ALIEN_H_GAP)
                y = ALIEN_TOP + row * (ALIEN_H + ALIEN_V_GAP)
                aliens.append(Alien(col, row, x, y))
        return aliens

    def _make_shields(self):
        shields = []
        shield_span = SCREEN_W / (SHIELD_COUNT + 1)
        for i in range(SHIELD_COUNT):
            cx = int(shield_span * (i + 1))
            shields.append(Shield(cx, SHIELD_Y))
        return shields

    def _start_new_wave(self):
        """Keep score/lives, bring on a fresh, faster wave."""
        self.level += 1
        self.aliens = self._make_aliens()
        self.alien_bullets = []
        self.player_bullet = None
        self.direction = 1
        # Shields are partially restored between waves.
        self.shields = self._make_shields()

    # -- alien logic -------------------------------------------------------
    def _alive_aliens(self):
        return [a for a in self.aliens if a.alive]

    def _march_interval(self):
        """Faster as fewer aliens remain."""
        total = ALIEN_ROWS * ALIEN_COLS
        alive = len(self._alive_aliens())
        if alive <= 0:
            return MARCH_INTERVAL_ONE
        frac = (alive - 1) / max(1, total - 1)   # 1.0 full -> 0.0 last one
        interval = MARCH_INTERVAL_ONE + frac * (MARCH_INTERVAL_FULL - MARCH_INTERVAL_ONE)
        # Each cleared wave also nudges the whole thing faster.
        interval *= max(0.45, 1.0 - 0.08 * (self.level - 1))
        return int(interval)

    def _march(self):
        alive = self._alive_aliens()
        if not alive:
            return

        # Will the group hit a wall if it moves this step?
        min_x = min(a.rect.left for a in alive)
        max_x = max(a.rect.right for a in alive)
        step = ALIEN_X_STEP * self.direction
        hit_wall = (max_x + step > SCREEN_W) or (min_x + step < 0)

        if hit_wall:
            # Drop one level and reverse direction.
            for a in alive:
                a.rect.y += ALIEN_DROP
            self.direction *= -1
        else:
            for a in alive:
                a.rect.x += step

        self.march_step += 1
        self.beeper.march(self.march_step)

        # Lose if aliens reach the player / shields line.
        if any(a.rect.bottom >= self.player.rect.top for a in alive):
            self._lose_life(invasion=True)

    def _alien_fire(self):
        alive = self._alive_aliens()
        if not alive:
            return
        if len(self.alien_bullets) >= ALIEN_BULLET_CAP:
            return

        # Only the lowest alien in each column may fire.
        bottom_by_col = {}
        for a in alive:
            cur = bottom_by_col.get(a.col)
            if cur is None or a.rect.bottom > cur.rect.bottom:
                bottom_by_col[a.col] = a
        shooters = list(bottom_by_col.values())
        random.shuffle(shooters)

        volley = random.randint(ALIEN_VOLLEY_MIN, ALIEN_VOLLEY_MAX)
        room = ALIEN_BULLET_CAP - len(self.alien_bullets)
        volley = min(volley, room, len(shooters))
        for shooter in shooters[:volley]:
            self.alien_bullets.append(
                Bullet(shooter.rect.centerx, shooter.rect.bottom + 6,
                       ALIEN_BULLET_SPEED, YELLOW)
            )

    # -- player logic ------------------------------------------------------
    def _fire_player_bullet(self):
        # Single bullet rule: a new shot replaces the old one.
        self.player_bullet = Bullet(
            self.player.rect.centerx, self.player.rect.top - 6,
            -PLAYER_BULLET_SPEED, WHITE
        )
        self.beeper.shoot()

    def _lose_life(self, invasion=False):
        self.player.lives -= 1
        self.beeper.player_die()
        self.alien_bullets = []
        self.player_bullet = None
        if invasion or self.player.lives <= 0:
            if invasion:
                self.player.lives = 0
        if self.player.lives <= 0:
            self.high_score = max(self.high_score, self.score)
            self.state = "gameover"
        else:
            # Reset player to center, brief breather.
            self.player.rect.centerx = SCREEN_W // 2

    # -- collisions --------------------------------------------------------
    def _handle_collisions(self):
        # Player bullet vs shields, aliens, ufo.
        pb = self.player_bullet
        if pb:
            for shield in self.shields:
                if shield.hit(pb.rect):
                    self.beeper.shield_hit()
                    self.player_bullet = None
                    pb = None
                    break
        if pb:
            for a in self._alive_aliens():
                if pb.rect.colliderect(a.rect):
                    a.alive = False
                    self.score += a.points
                    self.beeper.alien_die()
                    self.player_bullet = None
                    pb = None
                    break
        if pb and self.ufo and pb.rect.colliderect(self.ufo.rect):
            self.score += self.ufo.points
            self.beeper.ufo_die()
            self.ufo = None
            self.player_bullet = None
            pb = None

        # Alien bullets vs shields and player.
        surviving = []
        for b in self.alien_bullets:
            consumed = False
            for shield in self.shields:
                if shield.hit(b.rect):
                    self.beeper.shield_hit()
                    consumed = True
                    break
            if consumed:
                continue
            if b.rect.colliderect(self.player.rect):
                self._lose_life()
                consumed = True
                continue
            surviving.append(b)
        self.alien_bullets = surviving

    # -- main update -------------------------------------------------------
    def update(self):
        now = pygame.time.get_ticks()
        self.frame += 1

        keys = pygame.key.get_pressed()
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a] or self.touch_left:
            dx -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d] or self.touch_right:
            dx += PLAYER_SPEED
        self.player.move(dx)

        # March on a timer (this is what makes them speed up as they thin out).
        if now - self.last_march >= self._march_interval():
            self._march()
            self.last_march = now

        # Alien fire on a randomized timer.
        if now >= self.next_alien_fire:
            self._alien_fire()
            self.next_alien_fire = now + random.randint(ALIEN_FIRE_MIN_MS, ALIEN_FIRE_MAX_MS)

        # UFO spawn / movement.
        if self.ufo is None and now >= self.next_ufo:
            self.ufo = Ufo(random.choice([1, -1]))
            self.next_ufo = now + random.randint(UFO_MIN_MS, UFO_MAX_MS)
        if self.ufo:
            self.ufo.update()
            if self.ufo.offscreen():
                self.ufo = None

        # Bullets.
        if self.player_bullet:
            self.player_bullet.update()
            if self.player_bullet.offscreen():
                self.player_bullet = None
        for b in self.alien_bullets:
            b.update()
        self.alien_bullets = [b for b in self.alien_bullets if not b.offscreen()]

        self._handle_collisions()

        # Wave cleared?
        if not self._alive_aliens():
            self._start_new_wave()

    # -- drawing -----------------------------------------------------------
    def draw_hud(self):
        score = self.font.render(f"SCORE {self.score}", True, WHITE)
        self.screen.blit(score, (16, 12))
        hi = self.font.render(f"HI {self.high_score}", True, CYAN)
        self.screen.blit(hi, (SCREEN_W // 2 - hi.get_width() // 2, 12))
        lvl = self.font.render(f"LVL {self.level}", True, YELLOW)
        self.screen.blit(lvl, (SCREEN_W - lvl.get_width() - 16, 12))
        # Lives as little ships, just under the score (bottom corners are
        # reserved for the touch controls).
        for i in range(self.player.lives):
            x = 16 + i * (PLAYER_W // 2 + 8)
            pygame.draw.rect(self.screen, GREEN,
                             (x, 44, PLAYER_W // 2, PLAYER_H // 2),
                             border_radius=3)

    def draw_touch_controls(self):
        """Translucent on-screen pads for touch / mouse play."""
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

        def pad(rect, active):
            fill = (255, 255, 255, 90 if active else 40)
            pygame.draw.rect(overlay, fill, rect, border_radius=12)
            pygame.draw.rect(overlay, (255, 255, 255, 120), rect, width=2,
                             border_radius=12)

        pad(self.left_btn, self.touch_left)
        pad(self.right_btn, self.touch_right)
        pad(self.fire_btn, False)
        self.screen.blit(overlay, (0, 0))

        def label(text, rect):
            surf = self.font.render(text, True, WHITE)
            self.screen.blit(surf, (rect.centerx - surf.get_width() // 2,
                                    rect.centery - surf.get_height() // 2))

        label("<", self.left_btn)
        label(">", self.right_btn)
        label("FIRE", self.fire_btn)

    def draw_playing(self):
        for shield in self.shields:
            shield.draw(self.screen)
        for a in self._alive_aliens():
            a.draw(self.screen, self.march_step)
        if self.ufo:
            self.ufo.draw(self.screen)
        self.player.draw(self.screen)
        if self.player_bullet:
            self.player_bullet.draw(self.screen)
        for b in self.alien_bullets:
            b.draw(self.screen)
        self.draw_hud()
        self.draw_touch_controls()

    def draw_center_text(self, lines):
        total_h = sum(f.get_height() for f, _ in lines) + 10 * (len(lines) - 1)
        y = SCREEN_H // 2 - total_h // 2
        for surf, _ in lines:
            self.screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, y))
            y += surf.get_height() + 10

    def draw_menu(self):
        self.draw_center_text([
            (self.big_font.render("SPACE INVADERS", True, GREEN), None),
            (self.font.render("Arrows / A D to move, Space to fire", True, WHITE), None),
            (self.font.render("P pauses, Esc quits", True, WHITE), None),
            (self.font.render("Press ENTER to start", True, YELLOW), None),
        ])

    def draw_gameover(self):
        self.draw_center_text([
            (self.big_font.render("GAME OVER", True, RED), None),
            (self.font.render(f"Score {self.score}   Hi {self.high_score}", True, WHITE), None),
            (self.font.render("Press ENTER to play again", True, YELLOW), None),
        ])

    def draw_paused(self):
        self.draw_center_text([
            (self.big_font.render("PAUSED", True, CYAN), None),
            (self.font.render("Press P to resume", True, WHITE), None),
        ])

    # -- touch / mouse input ----------------------------------------------
    def _point_region(self, x, y):
        if self.left_btn.collidepoint(x, y):
            return "left"
        if self.right_btn.collidepoint(x, y):
            return "right"
        if self.fire_btn.collidepoint(x, y):
            return "fire"
        return None

    def _recompute_touch_move(self):
        regions = set(self.active_touches.values())
        self.touch_left = "left" in regions
        self.touch_right = "right" in regions

    def _touch_down(self, fid, x, y):
        # Outside of play, any tap advances the screen.
        if self.state in ("menu", "gameover"):
            self.reset()
            self.state = "playing"
            return
        if self.state == "paused":
            self.state = "playing"
            return
        region = self._point_region(x, y)
        if region == "fire":
            self._fire_player_bullet()
        elif region in ("left", "right"):
            self.active_touches[fid] = region
        self._recompute_touch_move()

    def _touch_move(self, fid, x, y):
        # Let a held finger slide between the left and right pads.
        if fid not in self.active_touches:
            return
        region = self._point_region(x, y)
        if region in ("left", "right"):
            self.active_touches[fid] = region
        else:
            self.active_touches.pop(fid, None)
        self._recompute_touch_move()

    def _touch_up(self, fid):
        self.active_touches.pop(fid, None)
        self._recompute_touch_move()

    # -- event / loop ------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if self.state in ("menu", "gameover") and event.key in (
                        pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.reset()
                    self.state = "playing"
                elif self.state == "playing":
                    if event.key == pygame.K_SPACE:
                        self._fire_player_bullet()
                    elif event.key == pygame.K_p:
                        self.state = "paused"
                elif self.state == "paused" and event.key == pygame.K_p:
                    self.state = "playing"
            elif event.type == pygame.FINGERDOWN:
                self._touch_down(event.finger_id,
                                 event.x * SCREEN_W, event.y * SCREEN_H)
            elif event.type == pygame.FINGERMOTION:
                self._touch_move(event.finger_id,
                                 event.x * SCREEN_W, event.y * SCREEN_H)
            elif event.type == pygame.FINGERUP:
                self._touch_up(event.finger_id)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._touch_down("mouse", event.pos[0], event.pos[1])
            elif event.type == pygame.MOUSEMOTION:
                if event.buttons[0]:
                    self._touch_move("mouse", event.pos[0], event.pos[1])
            elif event.type == pygame.MOUSEBUTTONUP:
                self._touch_up("mouse")
        return True

    async def run(self):
        running = True
        while running:
            running = self.handle_events()

            if self.state == "playing":
                self.update()

            self.screen.fill(BLACK)
            if self.state == "menu":
                self.draw_menu()
            elif self.state == "playing":
                self.draw_playing()
            elif self.state == "paused":
                self.draw_playing()
                self.draw_paused()
            elif self.state == "gameover":
                self.draw_playing()
                self.draw_gameover()

            pygame.display.flip()
            self.clock.tick(FPS)
            # Yield to the event loop every frame. Required for the browser
            # (pygbag) build; a harmless no-op cost on the desktop.
            await asyncio.sleep(0)

        pygame.quit()


async def main():
    await Game().run()


if __name__ == "__main__":
    asyncio.run(main())
