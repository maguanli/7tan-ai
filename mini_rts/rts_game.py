#!/usr/bin/env python3
"""
Mini RTS — A Real-Time Strategy Game
Built with Pygame | A* Pathfinding | Independent AI Economy
"""

import pygame
import heapq
import math
import random
import sys
from collections import deque
from enum import Enum
from typing import List, Tuple, Optional, Set

# ============================================================
# CONFIGURATION
# ============================================================
WINDOW_W, WINDOW_H = 1280, 800
MAP_W, MAP_H = 2400, 1800
FPS = 60
TILE = 40

# Colors (vibrant, readable)
COLOR_GRASS = (34, 139, 34)
COLOR_DIRT = (139, 119, 80)
COLOR_WATER = (30, 80, 180)
COLOR_GOLD = (255, 215, 0)
COLOR_PLAYER = (30, 144, 255)
COLOR_ENEMY = (220, 40, 40)
COLOR_HP_GREEN = (0, 200, 0)
COLOR_HP_RED = (200, 0, 0)
COLOR_UI_BG = (20, 20, 30)
COLOR_UI_BORDER = (80, 80, 100)
COLOR_WHITE = (240, 240, 240)
COLOR_BLACK = (0, 0, 0)
COLOR_SELECTION = (0, 255, 100)
COLOR_MINIMAP_BG = (0, 0, 0, 180)
COLOR_PLAYER_LIGHT = (100, 180, 255)
COLOR_ENEMY_LIGHT = (255, 120, 120)

# Game balance
START_GOLD = 600
WORKER_COST, WORKER_HP, WORKER_DMG, WORKER_SPD = 100, 80, 5, 2.5
SOLDIER_COST, SOLDIER_HP, SOLDIER_DMG, SOLDIER_SPD = 200, 200, 15, 2.0
TANK_COST, TANK_HP, TANK_DMG, TANK_SPD = 500, 600, 50, 1.2
HQ_HP = 2000
BARRACKS_COST = 250
BARRACKS_HP = 500
MINE_CAPACITY = 15
MINE_VALUE = 50
SUPPLY_PER_BARRACKS = 8
KILL_BOUNTY = 80

# ============================================================
# A* PATHFINDING (with building avoidance)
# ============================================================

class Node:
    __slots__ = ('x', 'y', 'g', 'h', 'parent')
    def __init__(self, x, y, g=0, h=0, parent=None):
        self.x, self.y = x, y
        self.g, self.h = g, h
        self.parent = parent
    @property
    def f(self): return self.g + self.h
    def __lt__(self, o): return self.f < o.f

def astar_path(world, sx, sy, tx, ty, blocker_set: Set[Tuple[int,int]], grid_size=40) -> List[Tuple[float,float]]:
    """A* pathfinding, returns list of (cx,cy) waypoints."""
    gs = grid_size
    sgx, sgy = int(sx)//gs, int(sy)//gs
    tgx, tgy = int(tx)//gs, int(ty)//gs

    if (tgx, tgy) in blocker_set:
        # Find nearest non-blocked adjacent cell
        best = None
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                nx, ny = tgx+dx, tgy+dy
                if (nx, ny) not in blocker_set:
                    d = abs(dx)+abs(dy)
                    if best is None or d < best[0]:
                        best = (d, nx, ny)
        if best:
            tgx, tgy = best[1], best[2]
        else:
            return [(tx, ty)]

    if (sgx, sgy) == (tgx, tgy):
        return [(tx, ty)]

    open_set = []
    heapq.heappush(open_set, Node(sgx, sgy, 0, abs(sgx-tgx)+abs(sgy-tgy)))
    closed = {}
    max_iter = 600

    while open_set and max_iter > 0:
        max_iter -= 1
        cur = heapq.heappop(open_set)
        key = (cur.x, cur.y)
        if key in closed and closed[key] <= cur.g:
            continue
        closed[key] = cur.g
        if key == (tgx, tgy):
            # Reconstruct path
            path = []
            while cur:
                path.append((cur.x * gs + gs//2, cur.y * gs + gs//2))
                cur = cur.parent
            path.reverse()
            if len(path) >= 2:
                path[-1] = (tx, ty)
            return path
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)]:
            nx, ny = cur.x+dx, cur.y+dy
            if not (0 <= nx < MAP_W//gs and 0 <= ny < MAP_H//gs):
                continue
            if (nx, ny) in blocker_set:
                continue
            cost = 1.414 if dx and dy else 1.0
            ng = cur.g + cost
            nk = (nx, ny)
            if nk in closed and closed[nk] <= ng:
                continue
            heapq.heappush(open_set, Node(nx, ny, ng, abs(nx-tgx)+abs(ny-tgy), cur))
    return [(tx, ty)]  # fallback: direct

# ============================================================
# ENTITY TYPES
# ============================================================

class UnitType(Enum):
    WORKER = "worker"
    SOLDIER = "soldier"
    TANK = "tank"

class BuildingType(Enum):
    HQ = "hq"
    BARRACKS = "barracks"

# ============================================================
# ENTITIES
# ============================================================

class Unit:
    __slots__ = ('x','y','utype','hp','max_hp','dmg','speed','owner','target_x','target_y',
                 'path','path_idx','attack_target','attack_cd','attack_timer','carrying',
                 'selected','alive','id')
    _next_id = 0
    def __init__(self, x, y, utype: UnitType, owner: str):
        self.x, self.y = float(x), float(y)
        self.utype = utype
        self.owner = owner
        self.alive = True
        self.selected = False
        self.carrying = 0
        self.attack_target = None
        self.attack_cd = 30
        self.attack_timer = 0
        self.path = []
        self.path_idx = 0
        self.target_x = x
        self.target_y = y
        self.id = Unit._next_id
        Unit._next_id += 1
        if utype == UnitType.WORKER:
            self.hp = self.max_hp = WORKER_HP
            self.dmg = WORKER_DMG
            self.speed = WORKER_SPD
        elif utype == UnitType.SOLDIER:
            self.hp = self.max_hp = SOLDIER_HP
            self.dmg = SOLDIER_DMG
            self.speed = SOLDIER_SPD
        else:
            self.hp = self.max_hp = TANK_HP
            self.dmg = TANK_DMG
            self.speed = TANK_SPD

    @property
    def is_fighter(self): return self.utype in (UnitType.SOLDIER, UnitType.TANK)
    @property
    def is_worker(self): return self.utype == UnitType.WORKER
    @property
    def rect(self): return pygame.Rect(self.x-12, self.y-12, 24, 24)

class Building:
    __slots__ = ('x','y','btype','hp','max_hp','owner','alive','rally_x','rally_y')
    def __init__(self, x, y, btype: BuildingType, owner: str):
        self.x, self.y = x, y
        self.btype = btype
        self.owner = owner
        self.alive = True
        self.rally_x, self.rally_y = x, y+60
        if btype == BuildingType.HQ:
            self.hp = self.max_hp = HQ_HP
        else:
            self.hp = self.max_hp = BARRACKS_HP
    @property
    def rect(self): return pygame.Rect(self.x-30, self.y-30, 60, 60)
    @property
    def is_hq(self): return self.btype == BuildingType.HQ

class GoldMine:
    __slots__ = ('x','y','amount')
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.amount = 9999
    @property
    def rect(self): return pygame.Rect(self.x-16, self.y-16, 32, 32)

# ============================================================
# PLAYER STATE
# ============================================================

class Player:
    __slots__ = ('name','gold','units','buildings','color','light_color','supply_used','supply_max')
    def __init__(self, name, color, light_color):
        self.name = name
        self.gold = START_GOLD
        self.units: List[Unit] = []
        self.buildings: List[Building] = []
        self.color = color
        self.light_color = light_color
        self.supply_used = 0
        self.supply_max = 8

    @property
    def hq(self):
        for b in self.buildings:
            if b.is_hq:
                return b
        return None

    @property
    def alive(self):
        return self.hq is not None and self.hq.alive

    def update_supply(self):
        self.supply_max = 8
        for b in self.buildings:
            if b.btype == BuildingType.BARRACKS and b.alive:
                self.supply_max += SUPPLY_PER_BARRACKS
        self.supply_used = len([u for u in self.units if u.alive and u.is_fighter])

# ============================================================
# WORLD / GAME STATE
# ============================================================

class World:
    def __init__(self):
        self.mines: List[GoldMine] = []
        self.player: Player = None
        self.ai: Player = None
        self.blocked_cells: Set[Tuple[int,int]] = set()
        self.time = 0
        self.game_over = False
        self.winner = ""
        self._init_map()

    def _init_map(self):
        # Gold mines scattered around map
        rng = random.Random(42)
        for _ in range(16):
            mx = rng.randint(4, MAP_W//TILE - 5) * TILE + TILE//2
            my = rng.randint(4, MAP_H//TILE - 5) * TILE + TILE//2
            self.mines.append(GoldMine(mx, my))

        # Player HQ (top-left area)
        phq_x = 6 * TILE + TILE//2
        phq_y = 6 * TILE + TILE//2
        self.player = Player("Player", COLOR_PLAYER, COLOR_PLAYER_LIGHT)
        self.player.buildings.append(Building(phq_x, phq_y, BuildingType.HQ, "player"))

        # AI HQ (bottom-right area)
        ahq_x = (MAP_W//TILE - 7) * TILE + TILE//2
        ahq_y = (MAP_H//TILE - 7) * TILE + TILE//2
        self.ai = Player("AI", COLOR_ENEMY, COLOR_ENEMY_LIGHT)
        self.ai.buildings.append(Building(ahq_x, ahq_y, BuildingType.HQ, "ai"))

        # Starting workers
        for _ in range(3):
            self.player.units.append(Unit(phq_x+30+random.uniform(-30,30), phq_y+50, UnitType.WORKER, "player"))
            self.ai.units.append(Unit(ahq_x-30+random.uniform(-30,30), ahq_y-50, UnitType.WORKER, "ai"))

        self._update_blocked()

    def _update_blocked(self):
        self.blocked_cells.clear()
        for p in (self.player, self.ai):
            for b in p.buildings:
                if b.alive:
                    gx, gy = int(b.x)//TILE, int(b.y)//TILE
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            self.blocked_cells.add((gx+dx, gy+dy))

    def all_units(self):
        for u in self.player.units + self.ai.units:
            if u.alive:
                yield u

    def all_buildings(self):
        for b in self.player.buildings + self.ai.buildings:
            if b.alive:
                yield b

    def get_owner(self, owner_name):
        return self.player if owner_name == "player" else self.ai

    def get_enemy(self, owner_name):
        return self.ai if owner_name == "player" else self.player

# ============================================================
# AI CONTROLLER
# ============================================================

class AIController:
    def __init__(self, world: World):
        self.world = world
        self.timer = 0

    def update(self):
        self.timer += 1
        if self.timer % 30 != 0:
            return
        ai = self.world.ai
        enemy = self.world.player

        # Build barracks if needed
        has_barracks = any(b.alive and b.btype == BuildingType.BARRACKS for b in ai.buildings)
        if not has_barracks and ai.gold >= BARRACKS_COST:
            hq = ai.hq
            if hq:
                bx = hq.x - 120
                by = hq.y
                ai.buildings.append(Building(bx, by, BuildingType.BARRACKS, "ai"))
                ai.gold -= BARRACKS_COST
                self.world._update_blocked()
                return

        # Train units
        ai.update_supply()
        workers = [u for u in ai.units if u.alive and u.is_worker]
        fighters = [u for u in ai.units if u.alive and u.is_fighter]
        supply_free = ai.supply_max - ai.supply_used

        if workers and ai.gold >= SOLDIER_COST and supply_free > 0 and has_barracks:
            ai.gold -= SOLDIER_COST
            bx, by = self._rally_point(ai)
            ai.units.append(Unit(bx, by, UnitType.SOLDIER, "ai"))
            return

        if workers and ai.gold >= TANK_COST and supply_free > 0 and len(fighters) >= 4 and has_barracks:
            ai.gold -= TANK_COST
            bx, by = self._rally_point(ai)
            ai.units.append(Unit(bx, by, UnitType.TANK, "ai"))
            return

        if len(workers) < 5 and ai.gold >= WORKER_COST:
            ai.gold -= WORKER_COST
            hq = ai.hq
            if hq:
                ai.units.append(Unit(hq.x+30, hq.y+50, UnitType.WORKER, "ai"))
            return

    def _rally_point(self, player):
        for b in player.buildings:
            if b.btype == BuildingType.BARRACKS and b.alive:
                return b.rally_x + random.uniform(-20,20), b.rally_y + random.uniform(-20,20)
        hq = player.hq
        return (hq.x+30, hq.y+50) if hq else (100, 100)

    def update_units(self):
        """Give orders to AI units."""
        ai = self.world.ai
        enemy = self.world.player
        if not enemy.alive:
            return

        enemy_hq = enemy.hq
        enemy_units = [u for u in enemy.units if u.alive]
        mines = self.world.mines

        for unit in ai.units:
            if not unit.alive:
                continue

            # Workers: mine and return
            if unit.is_worker:
                if unit.attack_target:
                    # Check if target still alive
                    if isinstance(unit.attack_target, Unit) and not unit.attack_target.alive:
                        unit.attack_target = None
                        unit.path = []
                    elif isinstance(unit.attack_target, Building) and not unit.attack_target.alive:
                        unit.attack_target = None
                        unit.path = []

                if unit.carrying >= MINE_CAPACITY:
                    # Return to HQ
                    hq = ai.hq
                    if hq:
                        if self._dist(unit, hq) < 60:
                            ai.gold += unit.carrying * MINE_VALUE
                            unit.carrying = 0
                            unit.path = []
                        elif not unit.path:
                            unit.path = astar_path(self.world, unit.x, unit.y, hq.x, hq.y, self.world.blocked_cells)
                            unit.path_idx = 0
                else:
                    # Find nearest mine
                    nearest = min(mines, key=lambda m: self._dist(unit, m))
                    if self._dist(unit, nearest) < 50:
                        unit.carrying = min(unit.carrying + 1, MINE_CAPACITY)
                    elif not unit.path:
                        unit.path = astar_path(self.world, unit.x, unit.y, nearest.x, nearest.y, self.world.blocked_cells)
                        unit.path_idx = 0
                continue

            # Fighters: attack-move toward enemy
            if unit.attack_target and isinstance(unit.attack_target, Unit) and not unit.attack_target.alive:
                unit.attack_target = None
                unit.path = []
            if unit.attack_target and isinstance(unit.attack_target, Building) and not unit.attack_target.alive:
                unit.attack_target = None
                unit.path = []

            if not unit.attack_target and not unit.path:
                # Find nearest enemy target
                targets = [(self._dist(unit, u), u) for u in enemy_units]
                if enemy_hq:
                    targets.append((self._dist(unit, enemy_hq), enemy_hq))
                if targets:
                    _, tgt = min(targets, key=lambda x: x[0])
                    unit.path = astar_path(self.world, unit.x, unit.y, 
                                          tgt.x if hasattr(tgt,'x') else tgt.x,
                                          tgt.y if hasattr(tgt,'y') else tgt.y,
                                          self.world.blocked_cells)
                    unit.path_idx = 0

    def _dist(self, a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

# ============================================================
# RENDERER
# ============================================================

class Camera:
    def __init__(self):
        self.x, self.y = 0, 0
        self.zoom = 1.0
        self.speed = 8

    def update(self, keys, mx, my):
        if keys[pygame.K_w] or keys[pygame.K_UP] or (my < 10 and mx < WINDOW_W-260):
            self.y -= self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN] or (my > WINDOW_H-10 and mx < WINDOW_W-260):
            self.y += self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT] or (mx < 10 and my < WINDOW_H):
            self.x -= self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT] or (mx > WINDOW_W-270 and mx < WINDOW_W-260 and my < WINDOW_H):
            self.x += self.speed
        self.x = max(0, min(self.x, MAP_W - WINDOW_W + 260))
        self.y = max(0, min(self.y, MAP_H - WINDOW_H))

    def world_to_screen(self, wx, wy):
        return int(wx - self.x), int(wy - self.y)

    def screen_to_world(self, sx, sy):
        return sx + self.x, sy + self.y

class Renderer:
    def __init__(self, screen, world, camera):
        self.screen = screen
        self.world = world
        self.cam = camera
        self.font_sm = pygame.font.Font("C:/Windows/Fonts/simhei.ttf", 13)
        self.font_md = pygame.font.Font("C:/Windows/Fonts/simhei.ttf", 16)
        self.font_lg = pygame.font.Font("C:/Windows/Fonts/simhei.ttf", 22)
        self.font_xl = pygame.font.Font("C:/Windows/Fonts/simhei.ttf", 32)

    def draw(self, selection: List[Unit], drag_rect=None):
        screen = self.screen
        cam = self.cam
        w = self.world

        # --- Terrain ---
        screen.fill(COLOR_GRASS)
        # Draw grid lines for visual reference
        gs = TILE
        sx0 = (cam.x // gs) * gs
        sy0 = (cam.y // gs) * gs
        for gx in range(int(sx0), int(cam.x + WINDOW_W - 260 + gs), gs):
            px = int(gx - cam.x)
            if 0 <= px < WINDOW_W - 260:
                pygame.draw.line(screen, (50,160,50), (px, 0), (px, WINDOW_H), 1)
        for gy in range(int(sy0), int(cam.y + WINDOW_H + gs), gs):
            py = int(gy - cam.y)
            if 0 <= py < WINDOW_H:
                pygame.draw.line(screen, (50,160,50), (0, py), (WINDOW_W-260, py), 1)

        # --- Gold Mines ---
        for mine in w.mines:
            sx, sy = cam.world_to_screen(mine.x, mine.y)
            if -32 < sx < WINDOW_W-228 and -32 < sy < WINDOW_H+32:
                pygame.draw.rect(screen, COLOR_GOLD, (sx-14, sy-14, 28, 28))
                pygame.draw.rect(screen, (200,160,0), (sx-14, sy-14, 28, 28), 2)
                label = self.font_sm.render("$", True, COLOR_BLACK)
                screen.blit(label, (sx-5, sy-8))

        # --- Buildings ---
        for b in w.all_buildings():
            sx, sy = cam.world_to_screen(b.x, b.y)
            if -60 < sx < WINDOW_W-200 and -60 < sy < WINDOW_H+60:
                owner = w.get_owner(b.owner)
                col = owner.color
                if b.is_hq:
                    # HQ: large square with flag
                    pygame.draw.rect(screen, col, (sx-32, sy-32, 64, 64))
                    pygame.draw.rect(screen, COLOR_WHITE, (sx-32, sy-32, 64, 64), 3)
                    label = self.font_md.render("HQ", True, COLOR_WHITE)
                    screen.blit(label, (sx-14, sy-10))
                else:
                    pygame.draw.rect(screen, col, (sx-28, sy-28, 56, 56))
                    pygame.draw.rect(screen, (200,200,200), (sx-28, sy-28, 56, 56), 2)
                    label = self.font_sm.render("营", True, COLOR_WHITE)
                    screen.blit(label, (sx-8, sy-8))

                # HP bar
                hp_pct = b.hp / b.max_hp
                bar_w = 50
                pygame.draw.rect(screen, COLOR_HP_RED, (sx-bar_w//2, sy-42, bar_w, 5))
                pygame.draw.rect(screen, COLOR_HP_GREEN, (sx-bar_w//2, sy-42, int(bar_w*hp_pct), 5))

        # --- Units ---
        for u in w.all_units():
            sx, sy = cam.world_to_screen(u.x, u.y)
            if -20 < sx < WINDOW_W-240 and -20 < sy < WINDOW_H+20:
                owner = w.get_owner(u.owner)
                col = owner.color
                lcol = owner.light_color

                # Draw unit based on type
                if u.utype == UnitType.WORKER:
                    pygame.draw.circle(screen, col, (sx, sy), 9)
                    pygame.draw.circle(screen, lcol, (sx, sy), 5)
                    if u.carrying > 0:
                        pygame.draw.circle(screen, COLOR_GOLD, (sx, sy-12), 4)
                elif u.utype == UnitType.SOLDIER:
                    pts = [(sx, sy-10), (sx-8, sy+8), (sx+8, sy+8)]
                    pygame.draw.polygon(screen, col, pts)
                    pygame.draw.polygon(screen, lcol, pts, 2)
                else:  # Tank
                    pygame.draw.rect(screen, col, (sx-11, sy-9, 22, 18))
                    pygame.draw.rect(screen, lcol, (sx-11, sy-9, 22, 18), 2)
                    # Turret
                    pygame.draw.circle(screen, col, (sx, sy), 6)

                # HP bar (only if damaged)
                if u.hp < u.max_hp:
                    hp_pct = u.hp / u.max_hp
                    bar_w = 20
                    pygame.draw.rect(screen, COLOR_HP_RED, (sx-bar_w//2, sy-16, bar_w, 3))
                    pygame.draw.rect(screen, COLOR_HP_GREEN, (sx-bar_w//2, sy-16, int(bar_w*hp_pct), 3))

                # Selection ring
                if u in selection:
                    pygame.draw.circle(screen, COLOR_SELECTION, (sx, sy), 14, 2)

        # --- Drag selection box ---
        if drag_rect:
            rx, ry, rw, rh = drag_rect
            pygame.draw.rect(screen, COLOR_SELECTION, (rx, ry, rw, rh), 2)

        # --- UI Panel (right side) ---
        self._draw_ui(selection)

        # --- Minimap ---
        self._draw_minimap(selection)

        # --- Game Over ---
        if w.game_over:
            overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            txt = self.font_xl.render(f"{'你赢了!' if w.winner == 'player' else '你输了...'} 按R重新开始", True, COLOR_WHITE)
            screen.blit(txt, (WINDOW_W//2 - txt.get_width()//2, WINDOW_H//2 - 30))

    def _draw_ui(self, selection):
        screen = self.screen
        ux = WINDOW_W - 260  # UI x start
        w = self.world
        p = w.player

        # Background
        pygame.draw.rect(screen, COLOR_UI_BG, (ux, 0, 260, WINDOW_H))
        pygame.draw.line(screen, COLOR_UI_BORDER, (ux, 0), (ux, WINDOW_H), 2)

        y = 10
        # Title
        t = self.font_lg.render("Mini RTS", True, COLOR_WHITE)
        screen.blit(t, (ux+10, y))
        y += 32

        # Gold
        t = self.font_md.render(f"金币: {p.gold}", True, COLOR_GOLD)
        screen.blit(t, (ux+10, y))
        y += 28

        # Supply
        p.update_supply()
        t = self.font_sm.render(f"人口: {p.supply_used}/{p.supply_max}", True, COLOR_WHITE)
        screen.blit(t, (ux+10, y))
        y += 24

        # Divider
        pygame.draw.line(screen, COLOR_UI_BORDER, (ux+10, y), (ux+250, y), 1)
        y += 14

        # Build buttons
        t = self.font_md.render("--- 建造 ---", True, COLOR_WHITE)
        screen.blit(t, (ux+10, y))
        y += 26

        self._btn(screen, ux+10, y, 240, 32, f"营房 ({BARRACKS_COST}$)", COLOR_UI_BORDER, p.gold >= BARRACKS_COST)
        y += 38
        self._btn(screen, ux+10, y, 240, 32, f"工人 ({WORKER_COST}$)", COLOR_UI_BORDER, p.gold >= WORKER_COST)
        y += 38
        self._btn(screen, ux+10, y, 240, 32, f"士兵 ({SOLDIER_COST}$)", COLOR_UI_BORDER, p.gold >= SOLDIER_COST and p.supply_used < p.supply_max)
        y += 38
        self._btn(screen, ux+10, y, 240, 32, f"坦克 ({TANK_COST}$)", COLOR_UI_BORDER, p.gold >= TANK_COST and p.supply_used < p.supply_max)
        y += 46

        # Selection info
        pygame.draw.line(screen, COLOR_UI_BORDER, (ux+10, y), (ux+250, y), 1)
        y += 14
        t = self.font_md.render("--- 选中单位 ---", True, COLOR_WHITE)
        screen.blit(t, (ux+10, y))
        y += 24

        if selection:
            for u in selection[:6]:
                utype_name = {UnitType.WORKER:"工人", UnitType.SOLDIER:"士兵", UnitType.TANK:"坦克"}[u.utype]
                owner_name = "我方" if u.owner == "player" else "敌方"
                t = self.font_sm.render(f"{owner_name} {utype_name} HP:{u.hp}/{u.max_hp}", True, COLOR_WHITE)
                screen.blit(t, (ux+10, y))
                y += 18
        else:
            t = self.font_sm.render("(框选单位以选中)", True, (120,120,140))
            screen.blit(t, (ux+10, y))
            y += 18

        # Help
        y = WINDOW_H - 130
        pygame.draw.line(screen, COLOR_UI_BORDER, (ux+10, y), (ux+250, y), 1)
        y += 10
        for line in ["左键拖拽: 框选", "右键敌人: 攻击", "右键空地: 移动", "WASD/边缘: 移动视野", "R: 重新开始"]:
            t = self.font_sm.render(line, True, (160,160,180))
            screen.blit(t, (ux+10, y))
            y += 17

    def _btn(self, screen, x, y, w, h, text, color, enabled):
        alpha = 255 if enabled else 80
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((*color[:3], 60 if enabled else 30))
        screen.blit(surf, (x, y))
        pygame.draw.rect(screen, (*color[:3], alpha), (x, y, w, h), 1)
        t = self.font_sm.render(text, True, (*COLOR_WHITE[:3], alpha))
        screen.blit(t, (x+8, y+8))

    def _draw_minimap(self, selection):
        mm_w, mm_h = 180, 130
        mm_x = WINDOW_W - 260 - mm_w - 10
        mm_y = WINDOW_H - mm_h - 10
        screen = self.screen
        w = self.world

        # Background
        mm_surf = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
        mm_surf.fill((0, 0, 0, 180))
        screen.blit(mm_surf, (mm_x, mm_y))
        pygame.draw.rect(screen, COLOR_UI_BORDER, (mm_x, mm_y, mm_w, mm_h), 1)

        sx = mm_w / MAP_W
        sy = mm_h / MAP_H

        # Mines
        for mine in w.mines:
            mx = mm_x + int(mine.x * sx)
            my = mm_y + int(mine.y * sy)
            pygame.draw.rect(screen, COLOR_GOLD, (mx-1, my-1, 2, 2))

        # Buildings
        for b in w.all_buildings():
            mx = mm_x + int(b.x * sx)
            my = mm_y + int(b.y * sy)
            col = COLOR_PLAYER if b.owner == "player" else COLOR_ENEMY
            sz = 3 if b.is_hq else 2
            pygame.draw.rect(screen, col, (mx-sz, my-sz, sz*2, sz*2))

        # Units
        for u in w.all_units():
            mx = mm_x + int(u.x * sx)
            my = mm_y + int(u.y * sy)
            col = COLOR_PLAYER if u.owner == "player" else COLOR_ENEMY
            screen.set_at((mx, my), col)

        # Camera viewport
        vx = mm_x + int(self.cam.x * sx)
        vy = mm_y + int(self.cam.y * sy)
        vw = int((WINDOW_W-260) * sx)
        vh = int(WINDOW_H * sy)
        pygame.draw.rect(screen, COLOR_WHITE, (vx, vy, vw, vh), 1)

# ============================================================
# MAIN GAME
# ============================================================

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Mini RTS")
        self.clock = pygame.time.Clock()
        self.running = True
        self.reset()

    def reset(self):
        self.world = World()
        self.camera = Camera()
        self.renderer = Renderer(self.screen, self.world, self.camera)
        self.ai = AIController(self.world)
        self.selection: List[Unit] = []
        self.dragging = False
        self.drag_start = (0, 0)
        self.drag_rect = None

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            self._handle_events()
            if not self.world.game_over:
                self._update()
            self.renderer.draw(self.selection, self.drag_rect if self.dragging else None)
            pygame.display.flip()
        pygame.quit()

    def _handle_events(self):
        mx, my = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()
        self.camera.update(keys, mx, my)

        for evt in pygame.event.get():
            if evt.type == pygame.QUIT:
                self.running = False

            elif evt.type == pygame.KEYDOWN:
                if evt.key == pygame.K_r and self.world.game_over:
                    self.reset()
                if evt.key == pygame.K_ESCAPE:
                    self.selection.clear()

            elif evt.type == pygame.MOUSEBUTTONDOWN:
                ux = WINDOW_W - 260
                # UI button clicks
                if mx >= ux:
                    self._handle_ui_click(mx, my)
                elif evt.button == 1:  # Left click - start drag
                    self.dragging = True
                    self.drag_start = (mx, my)
                    self.drag_rect = None
                    # Check single click on unit
                    wx, wy = self.camera.screen_to_world(mx, my)
                    clicked = None
                    for u in self.world.player.units:
                        if u.alive and math.hypot(u.x-wx, u.y-wy) < 14:
                            clicked = u
                            break
                    if clicked:
                        if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                            self.selection.clear()
                        if clicked not in self.selection:
                            self.selection.append(clicked)
                    elif not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                        self.selection.clear()

                elif evt.button == 3 and self.selection:  # Right click - command
                    wx, wy = self.camera.screen_to_world(mx, my)
                    # Check if targeting enemy
                    target = None
                    for u in self.world.ai.units:
                        if u.alive and math.hypot(u.x-wx, u.y-wy) < 20:
                            target = u
                            break
                    if target is None:
                        for b in self.world.ai.buildings:
                            if b.alive and math.hypot(b.x-wx, b.y-wy) < 40:
                                target = b
                                break

                    for u in self.selection:
                        if not u.alive:
                            continue
                        if target and u.is_fighter:
                            u.attack_target = target
                            u.path = []
                        elif not target:
                            u.attack_target = None
                            u.path = astar_path(self.world, u.x, u.y, wx, wy, self.world.blocked_cells)
                            u.path_idx = 0

            elif evt.type == pygame.MOUSEBUTTONUP:
                if evt.button == 1 and self.dragging:
                    self.dragging = False
                    if self.drag_rect and self.drag_rect[2] > 4 and self.drag_rect[3] > 4:
                        # Box select
                        rx, ry, rw, rh = self.drag_rect
                        if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                            self.selection.clear()
                        for u in self.world.player.units:
                            if not u.alive:
                                continue
                            sx, sy = self.camera.world_to_screen(u.x, u.y)
                            if rx <= sx <= rx+rw and ry <= sy <= ry+rh:
                                if u not in self.selection:
                                    self.selection.append(u)
                    self.drag_rect = None

            elif evt.type == pygame.MOUSEMOTION and self.dragging:
                sx, sy = self.drag_start
                self.drag_rect = (min(sx,mx), min(sy,my), abs(mx-sx), abs(my-sy))

    def _handle_ui_click(self, mx, my):
        p = self.world.player
        ux = WINDOW_W - 260
        # Button positions
        btns = [
            (34, 174, "barracks"),
            (72, 212, "worker"),
            (110, 250, "soldier"),
            (148, 288, "tank"),
        ]
        for by, cost_needed, action in btns:
            if ux+10 <= mx <= ux+250 and by <= my <= by+32:
                self._do_action(action)
                return

    def _do_action(self, action):
        p = self.world.player
        hq = p.hq

        if action == "barracks":
            if p.gold < BARRACKS_COST:
                return
            has_barracks = any(b.alive and b.btype == BuildingType.BARRACKS for b in p.buildings)
            if has_barracks:
                return
            if hq:
                bx = hq.x + 120
                by = hq.y
                p.buildings.append(Building(bx, by, BuildingType.BARRACKS, "player"))
                p.gold -= BARRACKS_COST
                self.world._update_blocked()

        elif action == "worker":
            if p.gold < WORKER_COST or not hq:
                return
            p.gold -= WORKER_COST
            p.units.append(Unit(hq.x+30, hq.y+50, UnitType.WORKER, "player"))

        elif action == "soldier":
            p.update_supply()
            if p.gold < SOLDIER_COST or p.supply_used >= p.supply_max:
                return
            barracks = [b for b in p.buildings if b.btype == BuildingType.BARRACKS and b.alive]
            if not barracks:
                return
            p.gold -= SOLDIER_COST
            b = barracks[0]
            p.units.append(Unit(b.rally_x, b.rally_y, UnitType.SOLDIER, "player"))

        elif action == "tank":
            p.update_supply()
            if p.gold < TANK_COST or p.supply_used >= p.supply_max:
                return
            barracks = [b for b in p.buildings if b.btype == BuildingType.BARRACKS and b.alive]
            if not barracks:
                return
            p.gold -= TANK_COST
            b = barracks[0]
            p.units.append(Unit(b.rally_x, b.rally_y, UnitType.TANK, "player"))

    def _update(self):
        w = self.world
        w.time += 1

        # Update all units
        for unit in list(w.player.units + w.ai.units):
            if not unit.alive:
                continue

            # Attack cooldown
            if unit.attack_timer > 0:
                unit.attack_timer -= 1

            # Check attack target
            if unit.attack_target and unit.attack_target.alive:
                dist = math.hypot(unit.x - unit.attack_target.x, unit.y - unit.attack_target.y)
                atk_range = 40 if isinstance(unit.attack_target, Building) else 32
                if dist <= atk_range:
                    unit.path = []
                    if unit.attack_timer <= 0:
                        unit.attack_target.hp -= unit.dmg
                        unit.attack_timer = unit.attack_cd
                        if unit.attack_target.hp <= 0:
                            unit.attack_target.alive = False
                            if isinstance(unit.attack_target, Unit):
                                # Kill bounty
                                killer_owner = w.get_owner(unit.owner)
                                killer_owner.gold += KILL_BOUNTY
                            unit.attack_target = None
                            self._check_game_over()
                elif not unit.path:
                    unit.path = astar_path(w, unit.x, unit.y, unit.attack_target.x, unit.attack_target.y, w.blocked_cells)
                    unit.path_idx = 0

            # Worker auto-mining (player workers without orders)
            if unit.owner == "player" and unit.is_worker and not unit.attack_target:
                if unit.carrying >= MINE_CAPACITY:
                    hq = w.player.hq
                    if hq and not unit.path:
                        unit.path = astar_path(w, unit.x, unit.y, hq.x, hq.y, w.blocked_cells)
                        unit.path_idx = 0
                    if hq and math.hypot(unit.x-hq.x, unit.y-hq.y) < 60:
                        w.player.gold += unit.carrying * MINE_VALUE
                        unit.carrying = 0
                        unit.path = []
                elif not unit.path and w.mines:
                    nearest = min(w.mines, key=lambda m: math.hypot(unit.x-m.x, unit.y-m.y))
                    if math.hypot(unit.x-nearest.x, unit.y-nearest.y) < 50:
                        unit.carrying = min(unit.carrying + 1, MINE_CAPACITY)
                    else:
                        unit.path = astar_path(w, unit.x, unit.y, nearest.x, nearest.y, w.blocked_cells)
                        unit.path_idx = 0

            # Follow path
            if unit.path and unit.path_idx < len(unit.path):
                tx, ty = unit.path[unit.path_idx]
                dx, dy = tx - unit.x, ty - unit.y
                dist = math.hypot(dx, dy)
                if dist < 4:
                    unit.path_idx += 1
                else:
                    unit.x += (dx/dist) * unit.speed
                    unit.y += (dy/dist) * unit.speed

        # AI logic
        self.ai.update()
        self.ai.update_units()

        # Clean up dead units
        for p in (w.player, w.ai):
            p.units = [u for u in p.units if u.alive]
            p.buildings = [b for b in p.buildings if b.alive]
        w._update_blocked()

        # Clean selection of dead units
        self.selection = [u for u in self.selection if u.alive]

    def _check_game_over(self):
        w = self.world
        if not w.player.alive:
            w.game_over = True
            w.winner = "ai"
        elif not w.ai.alive:
            w.game_over = True
            w.winner = "player"

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    game = Game()
    game.run()
