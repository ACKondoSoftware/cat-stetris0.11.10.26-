import pygame
import random
import sys
import math
from array import array

# Initialize Pygame and Mixer (44.1kHz, 16-bit signed mono)
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# Constants
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 560
FPS = 60

GRID_WIDTH = 10
GRID_HEIGHT = 20
BLOCK_SIZE = 22

PLAYFIELD_X = 230
PLAYFIELD_Y = 80

# Colors (Authentic NES Palette)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (124, 124, 124)
DARK_GRAY = (60, 60, 60)
RED = (216, 40, 0)
CYAN = (0, 232, 216)
GOLD = (252, 152, 56)

# NES Level Color Palettes: (Primary Color, Secondary Color)
LEVEL_PALETTES = [
    ((0, 88, 248), (60, 188, 252)),     # Level 0: Blue / Light Blue
    ((0, 168, 0), (184, 248, 24)),      # Level 1: Green / Light Green
    ((216, 0, 204), (248, 120, 248)),   # Level 2: Magenta / Pink
    ((0, 88, 248), (88, 216, 84)),      # Level 3: Blue / Green
    ((228, 0, 88), (88, 248, 152)),     # Level 4: Red-Pink / Mint
    ((88, 248, 152), (104, 136, 252)),  # Level 5: Mint / Periwinkle
    ((216, 40, 0), (124, 124, 124)),    # Level 6: Red / Gray
    ((104, 68, 252), (168, 0, 32)),     # Level 7: Purple / Dark Red
    ((0, 88, 248), (216, 40, 0)),       # Level 8: Blue / Red
    ((216, 40, 0), (252, 152, 56)),     # Level 9: Red / Orange
]

# NES Gravity Table (Frames per grid row drop at 60 FPS)
GRAVITY_FRAMES = [
    48, 43, 38, 33, 28, 23, 18, 13, 8, 6,
    5, 5, 5, 4, 4, 4, 3, 3, 3, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 1
]

# Tetromino Shapes and their NES Block Style:
# Style 3: Hollow (colored border with white interior)
# Style 1: Solid Primary Color with pixel shine
# Style 2: Solid Secondary Color with pixel shine
SHAPES = {
    'T': {'blocks': [(0, 0), (-1, 0), (1, 0), (0, 1)], 'style': 3},
    'J': {'blocks': [(0, 0), (-1, 0), (1, 0), (1, 1)], 'style': 1},
    'Z': {'blocks': [(0, 0), (-1, 0), (0, 1), (1, 1)], 'style': 2},
    'O': {'blocks': [(0, 0), (1, 0), (0, 1), (1, 1)], 'style': 3},
    'S': {'blocks': [(0, 0), (1, 0), (-1, 1), (0, 1)], 'style': 1},
    'L': {'blocks': [(0, 0), (-1, 0), (1, 0), (-1, 1)], 'style': 2},
    'I': {'blocks': [(0, 0), (-2, 0), (-1, 0), (1, 0)], 'style': 3},
}

SHAPE_ORDER = ['T', 'J', 'Z', 'O', 'S', 'L', 'I']


# ==========================================
# 8-BIT NES AUDIO SYNTHESIZER (NO FILES NEEDED)
# ==========================================
NOTE_FREQS = {
    'A3': 220.00, 'G#3': 207.65,
    'E4': 329.63, 'F4': 349.23, 'G4': 392.00, 'G#4': 415.30, 'A4': 440.00, 'B4': 493.88,
    'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'F5': 698.46, 'G5': 783.99, 'A5': 880.00,
    'REST': 0.0
}

# Classic Tetris Theme A (Korobeiniki) - (Note, Beats)
KOROBEINIKI_NOTES = [
    # Part A (x2)
    ('E5', 1.0), ('B4', 0.5), ('C5', 0.5), ('D5', 1.0), ('C5', 0.5), ('B4', 0.5),
    ('A4', 1.0), ('A4', 0.5), ('C5', 0.5), ('E5', 1.0), ('D5', 0.5), ('C5', 0.5),
    ('B4', 1.5), ('C5', 0.5), ('D5', 1.0), ('E5', 1.0),
    ('C5', 1.0), ('A4', 1.0), ('A4', 1.0), ('REST', 1.0),

    ('REST', 0.5), ('D5', 1.0), ('F5', 0.5), ('A5', 1.0), ('G5', 0.5), ('F5', 0.5),
    ('E5', 1.5), ('C5', 0.5), ('E5', 1.0), ('D5', 0.5), ('C5', 0.5),
    ('B4', 1.0), ('B4', 0.5), ('C5', 0.5), ('D5', 1.0), ('E5', 1.0),
    ('C5', 1.0), ('A4', 1.0), ('A4', 1.0), ('REST', 1.0),

    # Part B (Bridge)
    ('E4', 2.0), ('C4_A', 2.0), ('D4_B', 2.0), ('B3_G', 2.0),
    ('C4_A', 2.0), ('A3', 2.0), ('G#3', 2.0), ('B4', 1.0), ('REST', 1.0),
    ('E4', 2.0), ('C4_A', 2.0), ('D4_B', 2.0), ('B3_G', 2.0),
    ('C4_A', 1.0), ('E4', 1.0), ('A4', 2.0), ('G#4', 3.0), ('REST', 1.0)
]

# Additional lower bridge frequencies
NOTE_FREQS.update({'C4_A': 261.63, 'D4_B': 293.66, 'B3_G': 246.94})


def generate_square_wave(freq, duration, volume=0.18, duty=0.5):
    """Generates a raw 16-bit PCM square wave sample list."""
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    buf = array('h')
    if freq <= 0:
        buf.extend([0] * num_samples)
        return buf

    period = sample_rate / freq
    amp = int(32767 * volume)
    # Leave a tiny articulation gap at the end of each note
    active_samples = int(num_samples * 0.90)

    for i in range(num_samples):
        if i < active_samples:
            phase = (i % period) / period
            val = amp if phase < duty else -amp
            buf.append(val)
        else:
            buf.append(0)
    return buf


def build_soundtrack_and_sfx():
    """Synthesizes the full looping NES Tetris theme and sound effects in memory."""
    beat_sec = 60.0 / 148.0  # 148 BPM
    song_pcm = array('h')

    for note, beats in KOROBEINIKI_NOTES:
        freq = NOTE_FREQS.get(note, 0.0)
        song_pcm.extend(generate_square_wave(freq, beats * beat_sec, volume=0.14, duty=0.25))

    theme_sound = pygame.mixer.Sound(buffer=song_pcm)

    # Synthesize 8-bit Sound Effects
    sfx_move = pygame.mixer.Sound(buffer=generate_square_wave(600, 0.03, volume=0.15))

    rot_pcm = generate_square_wave(520, 0.035, volume=0.15)
    rot_pcm.extend(generate_square_wave(780, 0.04, volume=0.15))
    sfx_rotate = pygame.mixer.Sound(buffer=rot_pcm)

    sfx_lock = pygame.mixer.Sound(buffer=generate_square_wave(180, 0.06, volume=0.20))

    clear_pcm = array('h')
    for f in (523.25, 659.25, 783.99, 1046.50):
        clear_pcm.extend(generate_square_wave(f, 0.07, volume=0.22))
    sfx_clear = pygame.mixer.Sound(buffer=clear_pcm)

    over_pcm = array('h')
    for f in (440.0, 415.3, 392.0, 349.23):
        over_pcm.extend(generate_square_wave(f, 0.16, volume=0.20))
    sfx_gameover = pygame.mixer.Sound(buffer=over_pcm)

    return {
        'theme': theme_sound,
        'move': sfx_move,
        'rotate': sfx_rotate,
        'lock': sfx_lock,
        'clear': sfx_clear,
        'gameover': sfx_gameover
    }


def draw_nes_block(surface, x, y, size, level, style):
    """Draws an authentic 8-bit NES Tetris block."""
    c1, c2 = LEVEL_PALETTES[level % 10]
    rect = pygame.Rect(x, y, size, size)
    pygame.draw.rect(surface, BLACK, rect)  # 1px dark grid border

    inner = pygame.Rect(x + 1, y + 1, size - 2, size - 2)
    shine_size = max(2, size // 7)

    if style == 3:
        # Hollow block with white center (T, O, I pieces)
        pygame.draw.rect(surface, c1, inner)
        center = pygame.Rect(x + 4, y + 4, size - 8, size - 8)
        pygame.draw.rect(surface, WHITE, center)
        pygame.draw.rect(surface, WHITE, (x + 1, y + 1, shine_size, shine_size))
    else:
        # Solid colored block with top-left pixel highlight (J, Z, S, L pieces)
        color = c1 if style == 1 else c2
        pygame.draw.rect(surface, color, inner)
        pygame.draw.rect(surface, WHITE, (x + 1, y + 1, shine_size, shine_size))
        pygame.draw.rect(surface, WHITE, (x + 1 + shine_size, y + 1 + shine_size, shine_size, shine_size))


def draw_panel_box(surface, x, y, w, h, title="", font=None):
    """Draws a classic NES bordered UI box."""
    pygame.draw.rect(surface, WHITE, (x, y, w, h), 3)
    pygame.draw.rect(surface, DARK_GRAY, (x + 3, y + 3, w - 6, h - 6), 2)
    if title and font:
        label = font.render(title, True, WHITE)
        surface.blit(label, (x + (w - label.get_width()) // 2, y + 10))


class Piece:
    def __init__(self, shape_key):
        self.shape_key = shape_key
        self.blocks = list(SHAPES[shape_key]['blocks'])
        self.style = SHAPES[shape_key]['style']
        self.x = GRID_WIDTH // 2
        self.y = 1

    def get_positions(self, dx=0, dy=0, custom_blocks=None):
        blocks = custom_blocks if custom_blocks is not None else self.blocks
        return [(self.x + bx + dx, self.y + by + dy) for bx, by in blocks]

    def rotate_clockwise(self):
        if self.shape_key == 'O':
            return self.blocks
        return [(-by, bx) for bx, by in self.blocks]

    def rotate_counter_clockwise(self):
        if self.shape_key == 'O':
            return self.blocks
        return [(by, -bx) for bx, by in self.blocks]


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Cat's Tetris")
        self.clock = pygame.time.Clock()

        self.font_large = pygame.font.SysFont("courier", 32, bold=True)
        self.font_med = pygame.font.SysFont("courier", 22, bold=True)
        self.font_small = pygame.font.SysFont("courier", 16, bold=True)

        # Build and initialize 8-bit chiptune audio
        self.audio = build_soundtrack_and_sfx()
        self.music_muted = False

        self.state = "MAIN_MENU"  # MAIN_MENU, LEVEL_SELECT, PLAYING, GAME_OVER
        self.start_level = 0
        self.top_score = 10000
        self.reset_game()

    def start_music(self):
        self.audio['theme'].stop()
        if not self.music_muted:
            self.audio['theme'].play(loops=-1)

    def stop_music(self):
        self.audio['theme'].stop()

    def reset_game(self):
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.score = 0
        self.lines = 0
        self.level = self.start_level
        self.stats = {k: 0 for k in SHAPE_ORDER}

        self.current_piece = self.spawn_piece()
        self.next_piece = self.spawn_piece()
        self.stats[self.current_piece.shape_key] += 1

        self.fall_timer = 0
        self.das_timer = 0
        self.das_dir = 0

    def spawn_piece(self):
        return Piece(random.choice(SHAPE_ORDER))

    def valid_space(self, positions):
        for x, y in positions:
            if x < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT:
                return False
            if y >= 0 and self.grid[y][x] != 0:
                return False
        return True

    def lock_piece(self):
        for x, y in self.current_piece.get_positions():
            if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                self.grid[y][x] = self.current_piece.style

        # Check for completed lines
        cleared = 0
        new_grid = []
        for row in self.grid:
            if all(cell != 0 for cell in row):
                cleared += 1
            else:
                new_grid.append(row)

        while len(new_grid) < GRID_HEIGHT:
            new_grid.insert(0, [0 for _ in range(GRID_WIDTH)])
        self.grid = new_grid

        # NES Scoring & Audio Feedback
        if cleared > 0:
            self.audio['clear'].play()
            line_points = {1: 40, 2: 100, 3: 300, 4: 1200}
            self.score += line_points.get(cleared, 0) * (self.level + 1)
            self.lines += cleared
            if self.score > self.top_score:
                self.top_score = self.score

            # NES Level Transition Logic
            transition_lines = min(self.start_level * 10 + 10, max(100, self.start_level * 10 - 50))
            if self.lines >= transition_lines:
                self.level = self.start_level + 1 + (self.lines - transition_lines) // 10
        else:
            self.audio['lock'].play()

        # Spawn next piece
        self.current_piece = self.next_piece
        self.next_piece = self.spawn_piece()
        self.stats[self.current_piece.shape_key] += 1

        if not self.valid_space(self.current_piece.get_positions()):
            self.state = "GAME_OVER"
            self.stop_music()
            self.audio['gameover'].play()

    def move_horizontal(self, dx):
        if self.valid_space(self.current_piece.get_positions(dx=dx)):
            self.current_piece.x += dx
            self.audio['move'].play()

    def rotate_piece(self, clockwise=True):
        rotated = (self.current_piece.rotate_clockwise() if clockwise
                   else self.current_piece.rotate_counter_clockwise())
        if self.valid_space(self.current_piece.get_positions(custom_blocks=rotated)):
            self.current_piece.blocks = rotated
            self.audio['rotate'].play()

    def get_gravity_speed(self):
        idx = min(self.level, len(GRAVITY_FRAMES) - 1)
        return GRAVITY_FRAMES[idx]

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # Toggle Music Mute anytime with 'M'
                if event.key == pygame.K_m:
                    self.music_muted = not self.music_muted
                    if self.music_muted:
                        self.stop_music()
                    elif self.state == "PLAYING":
                        self.start_music()

                if self.state == "MAIN_MENU":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.audio['rotate'].play()
                        self.state = "LEVEL_SELECT"

                elif self.state == "LEVEL_SELECT":
                    if event.key == pygame.K_RIGHT:
                        self.start_level = (self.start_level + 1) % 10
                        self.audio['move'].play()
                    elif event.key == pygame.K_LEFT:
                        self.start_level = (self.start_level - 1) % 10
                        self.audio['move'].play()
                    elif event.key == pygame.K_DOWN:
                        self.start_level = (self.start_level + 5) % 10
                        self.audio['move'].play()
                    elif event.key == pygame.K_UP:
                        self.start_level = (self.start_level - 5) % 10
                        self.audio['move'].play()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.reset_game()
                        self.state = "PLAYING"
                        self.start_music()

                elif self.state == "PLAYING":
                    if event.key == pygame.K_LEFT:
                        self.move_horizontal(-1)
                        self.das_dir = -1
                        self.das_timer = 0
                    elif event.key == pygame.K_RIGHT:
                        self.move_horizontal(1)
                        self.das_dir = 1
                        self.das_timer = 0
                    elif event.key in (pygame.K_UP, pygame.K_x):
                        self.rotate_piece(clockwise=True)
                    elif event.key == pygame.K_z:
                        self.rotate_piece(clockwise=False)
                    elif event.key == pygame.K_SPACE:
                        # Hard drop
                        drop_dist = 0
                        while self.valid_space(self.current_piece.get_positions(dy=1)):
                            self.current_piece.y += 1
                            drop_dist += 1
                        self.score += drop_dist
                        self.lock_piece()

                elif self.state == "GAME_OVER":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.state = "MAIN_MENU"

            if event.type == pygame.KEYUP and self.state == "PLAYING":
                if event.key == pygame.K_LEFT and self.das_dir == -1:
                    self.das_dir = 0
                elif event.key == pygame.K_RIGHT and self.das_dir == 1:
                    self.das_dir = 0

    def update(self):
        if self.state != "PLAYING":
            return

        # Delayed Auto Shift (DAS) for holding Left/Right
        if self.das_dir != 0:
            self.das_timer += 1
            if self.das_timer >= 16 and (self.das_timer - 16) % 6 == 0:
                self.move_horizontal(self.das_dir)

        # Soft Drop check
        keys = pygame.key.get_pressed()
        gravity = 2 if keys[pygame.K_DOWN] else self.get_gravity_speed()

        self.fall_timer += 1
        if self.fall_timer >= gravity:
            self.fall_timer = 0
            if self.valid_space(self.current_piece.get_positions(dy=1)):
                self.current_piece.y += 1
                if keys[pygame.K_DOWN]:
                    self.score += 1
            else:
                self.lock_piece()

    def draw_main_menu(self):
        self.screen.fill(BLACK)
        draw_panel_box(self.screen, 50, 60, 540, 440)

        # Main Menu Title: Cat's Space Invaders
        title1 = self.font_large.render("CAT'S SPACE INVADERS", True, GOLD)
        sub = self.font_med.render("- NES TETRIS EDITION -", True, CYAN)
        prompt = self.font_med.render("PRESS ENTER TO START", True, WHITE)
        controls = self.font_small.render("ARROWS: Move | Z/X/UP: Rotate | SPACE: Drop | M: Mute", True, GRAY)

        self.screen.blit(title1, (SCREEN_WIDTH // 2 - title1.get_width() // 2, 160))
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 220))

        # Blinking prompt at 60 FPS
        if (pygame.time.get_ticks() // 400) % 2 == 0:
            self.screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 330))

        self.screen.blit(controls, (SCREEN_WIDTH // 2 - controls.get_width() // 2, 430))

    def draw_level_select(self):
        self.screen.fill(BLACK)
        draw_panel_box(self.screen, 80, 60, 480, 440, "A-TYPE GAME", self.font_large)

        lbl = self.font_med.render("SELECT STARTING LEVEL", True, CYAN)
        self.screen.blit(lbl, (SCREEN_WIDTH // 2 - lbl.get_width() // 2, 150))

        # Draw 2x5 Level Grid (0 - 9)
        grid_x = 170
        grid_y = 220
        for lvl in range(10):
            row = lvl // 5
            col = lvl % 5
            bx = grid_x + col * 62
            by = grid_y + row * 62

            color = GOLD if lvl == self.start_level else DARK_GRAY
            pygame.draw.rect(self.screen, color, (bx, by, 50, 50), 3)
            num_surf = self.font_med.render(str(lvl), True, WHITE)
            self.screen.blit(num_surf, (bx + 25 - num_surf.get_width() // 2, by + 13))

        music_lbl = self.font_small.render(
            f"MUSIC: {'OFF (PRESS M)' if self.music_muted else 'TYPE-A KOROBEINIKI (M TO MUTE)'}",
            True, GOLD
        )
        self.screen.blit(music_lbl, (SCREEN_WIDTH // 2 - music_lbl.get_width() // 2, 375))

        hint = self.font_small.render("PRESS ENTER TO PLAY", True, WHITE)
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 420))

    def draw_playing(self):
        self.screen.fill(BLACK)

        # 1. Statistics Panel (Left)
        draw_panel_box(self.screen, 25, 80, 185, 445, "STATISTICS", self.font_med)
        for i, key in enumerate(SHAPE_ORDER):
            py = 135 + i * 52
            mini_size = 12
            for bx, by in SHAPES[key]['blocks']:
                draw_nes_block(
                    self.screen,
                    75 + bx * mini_size,
                    py + by * mini_size,
                    mini_size,
                    self.level,
                    SHAPES[key]['style']
                )
            count_text = self.font_med.render(f"{self.stats[key]:03d}", True, RED)
            self.screen.blit(count_text, (130, py - 4))

        # 2. Lines Counter (Top Center)
        draw_panel_box(self.screen, PLAYFIELD_X - 4, 20, GRID_WIDTH * BLOCK_SIZE + 8, 50)
        lines_txt = self.font_med.render(f"LINES-{self.lines:03d}", True, WHITE)
        self.screen.blit(lines_txt, (PLAYFIELD_X + 45, 34))

        # 3. Playfield Border & Locked Blocks
        draw_panel_box(
            self.screen,
            PLAYFIELD_X - 4,
            PLAYFIELD_Y - 4,
            GRID_WIDTH * BLOCK_SIZE + 8,
            GRID_HEIGHT * BLOCK_SIZE + 8
        )

        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if self.grid[r][c] != 0:
                    draw_nes_block(
                        self.screen,
                        PLAYFIELD_X + c * BLOCK_SIZE,
                        PLAYFIELD_Y + r * BLOCK_SIZE,
                        BLOCK_SIZE,
                        self.level,
                        self.grid[r][c]
                    )

        # Draw Active Falling Piece
        for x, y in self.current_piece.get_positions():
            if y >= 0:
                draw_nes_block(
                    self.screen,
                    PLAYFIELD_X + x * BLOCK_SIZE,
                    PLAYFIELD_Y + y * BLOCK_SIZE,
                    BLOCK_SIZE,
                    self.level,
                    self.current_piece.style
                )

        # 4. Right HUD Panels (Score, Next, Level)
        hud_x = PLAYFIELD_X + GRID_WIDTH * BLOCK_SIZE + 20

        # Score Box
        draw_panel_box(self.screen, hud_x, 20, 155, 150)
        self.screen.blit(self.font_med.render("TOP", True, WHITE), (hud_x + 15, 32))
        self.screen.blit(self.font_med.render(f"{self.top_score:06d}", True, WHITE), (hud_x + 15, 58))
        self.screen.blit(self.font_med.render("SCORE", True, WHITE), (hud_x + 15, 96))
        self.screen.blit(self.font_med.render(f"{self.score:06d}", True, WHITE), (hud_x + 15, 122))

        # Next Piece Box
        draw_panel_box(self.screen, hud_x, 190, 155, 140, "NEXT", self.font_med)
        nx_center = hud_x + 75
        ny_center = 260
        for bx, by in self.next_piece.blocks:
            draw_nes_block(
                self.screen,
                nx_center + bx * BLOCK_SIZE,
                ny_center + by * BLOCK_SIZE,
                BLOCK_SIZE,
                self.level,
                self.next_piece.style
            )

        # Level Box
        draw_panel_box(self.screen, hud_x, 350, 155, 95, "LEVEL", self.font_med)
        lvl_txt = self.font_large.render(f"{self.level:02d}", True, WHITE)
        self.screen.blit(lvl_txt, (hud_x + 77 - lvl_txt.get_width() // 2, 390))

        # Audio status indicator
        mute_txt = self.font_small.render(
            "M: MUTE [OFF]" if self.music_muted else "M: MUSIC [ON]",
            True, GRAY
        )
        self.screen.blit(mute_txt, (hud_x + 10, 465))

        # Game Over Overlay
        if self.state == "GAME_OVER":
            overlay = pygame.Rect(PLAYFIELD_X + 10, PLAYFIELD_Y + 140, GRID_WIDTH * BLOCK_SIZE - 20, 110)
            pygame.draw.rect(self.screen, BLACK, overlay)
            pygame.draw.rect(self.screen, WHITE, overlay, 3)
            go_txt = self.font_med.render("GAME OVER", True, RED)
            re_txt = self.font_small.render("PRESS ENTER", True, WHITE)
            self.screen.blit(go_txt, (overlay.centerx - go_txt.get_width() // 2, overlay.y + 25))
            self.screen.blit(re_txt, (overlay.centerx - re_txt.get_width() // 2, overlay.y + 65))

    def run(self):
        while True:
            self.handle_events()
            self.update()

            if self.state == "MAIN_MENU":
                self.draw_main_menu()
            elif self.state == "LEVEL_SELECT":
                self.draw_level_select()
            elif self.state in ("PLAYING", "GAME_OVER"):
                self.draw_playing()

            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()