"""
Mini RTS — 真正的 Pygame RTS 游戏
蓝色=你 | 红色=AI | 金色=金矿
左键选择/框选 | 右键移动/攻击 | 摧毁敌方HQ=胜利
"""
import pygame
import sys
import random
import math
from typing import List, Optional, Tuple

pygame.init()
W, H = 1200, 800
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Mini RTS — 蓝色=你 | 红色=AI")
clock = pygame.time.Clock()
# 字体：直接用系统字体文件路径（最可靠）
_FONT_PATHS = [
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/simsun.ttc',
    'C:/Windows/Fonts/simkai.ttf',
]
font = None
for _fp in _FONT_PATHS:
    try:
        font = pygame.font.Font(_fp, 16)
        font_big = pygame.font.Font(_fp, 22)
        break
    except:
        continue
if font is None:
    font = pygame.font.Font(None, 18)
    font_big = pygame.font.Font(None, 26)

# ── 颜色 ──
BLUE    = (40, 100, 220)
RED     = (220, 40, 40)
GOLD    = (240, 180, 30)
WHITE   = (255, 255, 255)
BLACK   = (20, 20, 20)
GREEN   = (40, 200, 40)
GRAY    = (100, 100, 100)
DARK    = (40, 40, 40)
PANEL_W = 240


# ═══════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════

class Unit:
    """游戏中的单位：工人、士兵、坦克"""
    __slots__ = ('owner', 'utype', 'x', 'y', 'hp', 'max_hp', 'atk',
                 'speed', 'target_x', 'target_y', 'target_enemy',
                 'attack_cd', 'carry_gold', 'selected')
    
    def __init__(self, owner: str, utype: str, x: float, y: float):
        self.owner = owner          # 'player' | 'enemy'
        self.utype = utype          # 'worker' | 'soldier' | 'tank'
        self.x, self.y = x, y
        self.target_x, self.target_y = x, y
        self.target_enemy = None    # 攻击目标
        self.attack_cd = 0
        self.carry_gold = 0
        self.selected = False
        
        if utype == 'worker':
            self.hp = self.max_hp = 40
            self.atk = 3
            self.speed = 1.8
        elif utype == 'soldier':
            self.hp = self.max_hp = 80
            self.atk = 12
            self.speed = 2.2
        else:  # tank
            self.hp = self.max_hp = 200
            self.atk = 35
            self.speed = 1.3


class Building:
    """建筑：HQ、兵营"""
    __slots__ = ('owner', 'btype', 'x', 'y', 'w', 'h', 'hp', 'max_hp')
    
    def __init__(self, owner: str, btype: str, x: float, y: float):
        self.owner = owner
        self.btype = btype
        self.x, self.y = x, y
        self.w, self.h = (60, 60) if btype == 'hq' else (40, 40)
        self.hp = self.max_hp = 600 if btype == 'hq' else 300


class Mine:
    """金矿"""
    __slots__ = ('x', 'y', 'amount')
    def __init__(self, x: float, y: float):
        self.x, self.y = x, y
        self.amount = 9999  # 无限矿


# ═══════════════════════════════════════════════
# 游戏状态
# ═══════════════════════════════════════════════

class Game:
    def __init__(self):
        self.units: List[Unit] = []
        self.buildings: List[Building] = []
        self.mines: List[Mine] = []
        self.player_gold = 500
        self.enemy_gold = 500
        self.selection: List[Unit] = []
        self.drag_start: Optional[Tuple[int,int]] = None
        self.drag_end: Optional[Tuple[int,int]] = None
        self.mouse_pos = (0, 0)
        self.log: List[str] = []
        self.winner: Optional[str] = None
        
        # 初始化地图
        self._init_map()
    
    def _init_map(self):
        # 玩家HQ（左上）
        self.buildings.append(Building('player', 'hq', 120, 120))
        # 敌方HQ（右下）
        self.buildings.append(Building('enemy', 'hq', W - PANEL_W - 180, H - 180))
        
        # 金矿：8个，分布在地图各处（避开HQ）
        margin = 80
        map_w = W - PANEL_W
        for _ in range(8):
            mx = random.randint(margin, map_w - margin)
            my = random.randint(margin, H - margin)
            # 远离HQ
            while ((mx-120)**2 + (my-120)**2 < 200**2 or
                   (mx-(map_w-180))**2 + (my-(H-180))**2 < 200**2):
                mx = random.randint(margin, map_w - margin)
                my = random.randint(margin, H - margin)
            self.mines.append(Mine(mx, my))
        
        # 初始单位：各2个工人 + 2个士兵
        hq = self.buildings[0]
        for _ in range(2):
            self.units.append(Unit('player', 'worker', hq.x+30, hq.y+70))
        for _ in range(2):
            self.units.append(Unit('player', 'soldier', hq.x+30, hq.y+70))
        
        ehq = self.buildings[1]
        for _ in range(2):
            self.units.append(Unit('enemy', 'worker', ehq.x+10, ehq.y-20))
        for _ in range(2):
            self.units.append(Unit('enemy', 'soldier', ehq.x+10, ehq.y-20))
        
        self.log_add("游戏开始！框选单位 → 右键移动/攻击 → 摧毁敌方HQ！")
    
    def log_add(self, msg: str):
        self.log.append(msg)
        if len(self.log) > 8:
            self.log.pop(0)
    
    def player_hq(self) -> Optional[Building]:
        for b in self.buildings:
            if b.owner == 'player' and b.btype == 'hq':
                return b
        return None
    
    def enemy_hq(self) -> Optional[Building]:
        for b in self.buildings:
            if b.owner == 'enemy' and b.btype == 'hq':
                return b
        return None
    
    def has_barracks(self, owner: str) -> bool:
        for b in self.buildings:
            if b.owner == owner and b.btype == 'barracks':
                return True
        return False
    
    def units_of(self, owner: str) -> List[Unit]:
        return [u for u in self.units if u.owner == owner]
    
    def nearest_enemy(self, unit: Unit) -> Optional[Unit | Building]:
        """找到最近的敌方单位或建筑"""
        best, best_dist = None, 99999
        for u in self.units:
            if u.owner != unit.owner:
                d = math.hypot(u.x - unit.x, u.y - unit.y)
                if d < best_dist:
                    best, best_dist = u, d
        for b in self.buildings:
            if b.owner != unit.owner:
                cx, cy = b.x + b.w/2, b.y + b.h/2
                d = math.hypot(cx - unit.x, cy - unit.y)
                if d < best_dist:
                    best, best_dist = b, d
        return best
    
    def nearest_mine(self, unit: Unit) -> Optional[Mine]:
        best, best_dist = None, 99999
        for m in self.mines:
            d = math.hypot(m.x - unit.x, m.y - unit.y)
            if d < best_dist:
                best, best_dist = m, d
        return best


game = Game()


# ═══════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════

def clamp_to_map(x: float, y: float) -> Tuple[float, float]:
    map_w = W - PANEL_W
    return max(10, min(map_w-10, x)), max(10, min(H-10, y))


def move_toward(unit: Unit, tx: float, ty: float, speed: float):
    """朝目标移动，返回是否到达"""
    dx, dy = tx - unit.x, ty - unit.y
    dist = math.hypot(dx, dy)
    if dist < speed + 2:
        unit.x, unit.y = tx, ty
        return True
    unit.x += dx / dist * speed
    unit.y += dy / dist * speed
    return False


# ═══════════════════════════════════════════════
# 渲染
# ═══════════════════════════════════════════════

def draw_map():
    screen.fill(DARK)
    map_w = W - PANEL_W
    # 网格
    for gx in range(0, map_w, 40):
        pygame.draw.line(screen, (30,30,30), (gx,0), (gx,H))
    for gy in range(0, H, 40):
        pygame.draw.line(screen, (30,30,30), (0,gy), (map_w,gy))
    # 面板分隔线
    pygame.draw.line(screen, WHITE, (map_w, 0), (map_w, H), 2)


def draw_mines():
    for m in game.mines:
        r = 10
        cx, cy = int(m.x), int(m.y)
        pygame.draw.circle(screen, GOLD, (cx, cy), r)
        pygame.draw.circle(screen, (180,130,10), (cx, cy), r, 2)
        # ⛏ 符号
        t = font.render("矿", True, BLACK)
        screen.blit(t, (cx-8, cy-8))


def draw_buildings():
    for b in game.buildings:
        color = BLUE if b.owner == 'player' else RED
        rx, ry = int(b.x), int(b.y)
        pygame.draw.rect(screen, color, (rx, ry, b.w, b.h))
        pygame.draw.rect(screen, WHITE, (rx, ry, b.w, b.h), 2)
        
        # HP 条
        hp_pct = b.hp / b.max_hp
        bar_w, bar_h = b.w, 6
        bar_y = ry - 10
        pygame.draw.rect(screen, (60,60,60), (rx, bar_y, bar_w, bar_h))
        hp_color = GREEN if hp_pct > 0.5 else (200,200,0) if hp_pct > 0.25 else RED
        pygame.draw.rect(screen, hp_color, (rx, bar_y, int(bar_w*hp_pct), bar_h))
        
        # 标签
        label = "HQ" if b.btype == 'hq' else "兵营"
        t = font.render(label, True, WHITE)
        screen.blit(t, (rx+2, ry+2))


def draw_units():
    for u in game.units:
        color = BLUE if u.owner == 'player' else RED
        if u.utype == 'worker':
            r = 8
        elif u.utype == 'soldier':
            r = 10
        else:
            r = 14
        
        cx, cy = int(u.x), int(u.y)
        pygame.draw.circle(screen, color, (cx, cy), r)
        pygame.draw.circle(screen, WHITE, (cx, cy), r, 1)
        
        # 选中光圈
        if u.selected:
            pygame.draw.circle(screen, GREEN, (cx, cy), r+4, 2)
        
        # 图标
        icon = {'worker':'工','soldier':'兵','tank':'坦'}[u.utype]
        t = font.render(icon, True, WHITE)
        screen.blit(t, (cx-7, cy-7))
        
        # HP 条（仅战斗单位）
        if u.utype != 'worker':
            hp_pct = u.hp / u.max_hp
            bw, bh = 20, 4
            bx = cx - bw//2
            by = cy - r - 8
            pygame.draw.rect(screen, (60,60,60), (bx, by, bw, bh))
            c = GREEN if hp_pct > 0.5 else (200,200,0) if hp_pct > 0.25 else RED
            pygame.draw.rect(screen, c, (bx, by, int(bw*hp_pct), bh))
        
        # 搬金图标
        if u.carry_gold > 0:
            t = font.render(f"${u.carry_gold}", True, GOLD)
            screen.blit(t, (cx-15, cy-r-18))


def draw_selection_box():
    if game.drag_start and game.drag_end:
        x1, y1 = game.drag_start
        x2, y2 = game.drag_end
        rx, ry = min(x1,x2), min(y1,y2)
        rw, rh = abs(x2-x1), abs(y2-y1)
        pygame.draw.rect(screen, GREEN, (rx, ry, rw, rh), 1)
        s = pygame.Surface((rw, rh), pygame.SRCALPHA)
        s.fill((0,255,0,30))
        screen.blit(s, (rx, ry))


def draw_panel():
    map_w = W - PANEL_W
    px = map_w
    
    # 面板背景
    pygame.draw.rect(screen, (25,25,30), (px, 0, PANEL_W, H))
    
    y = 20
    # 标题
    t = font_big.render("Mini RTS", True, WHITE)
    screen.blit(t, (px+20, y))
    y += 40
    
    # 金币
    t = font_big.render(f"$ {game.player_gold}", True, GOLD)
    screen.blit(t, (px+20, y))
    y += 30
    
    # 单位统计
    pu = game.units_of('player')
    workers = sum(1 for u in pu if u.utype == 'worker')
    soldiers = sum(1 for u in pu if u.utype == 'soldier')
    tanks = sum(1 for u in pu if u.utype == 'tank')
    
    t = font.render(f"👷 工人: {workers}  ⚔ 士兵: {soldiers}  🛡 坦克: {tanks}", True, WHITE)
    screen.blit(t, (px+15, y))
    y += 35
    
    # ── 按钮 ──
    buttons = [
        ("[营] 建造兵营", 'build_barracks', 200, not game.has_barracks('player')),
        ("[工] 训练工人", 'train_worker', 100, True),
        ("[兵] 训练士兵", 'train_soldier', 150, game.has_barracks('player')),
        ("[坦] 训练坦克", 'train_tank', 300, game.has_barracks('player')),
    ]
    
    for label, action, cost, enabled in buttons:
        color = WHITE if enabled else GRAY
        bx, by = px+15, y
        bw, bh = PANEL_W-30, 32
        pygame.draw.rect(screen, (50,50,60) if enabled else (35,35,40), (bx, by, bw, bh))
        pygame.draw.rect(screen, color, (bx, by, bw, bh), 1)
        t = font.render(f"{label}  ({cost}$)", True, color)
        screen.blit(t, (bx+10, by+7))
        y += 38
    
    y += 10
    
    # 操作提示
    tips = [
        "> 左键拖拽 = 框选",
        "> 左键单击 = 选中",
        "> 右键空地 = 移动",
        "> 右键红方 = 攻击",
    ]
    for tip in tips:
        t = font.render(tip, True, (180,180,180))
        screen.blit(t, (px+15, y))
        y += 22
    
    y += 10
    
    # 日志
    t = font_big.render("📋 日志", True, WHITE)
    screen.blit(t, (px+20, y))
    y += 25
    for msg in game.log[-6:]:
        t = font.render(msg[:28], True, (200,200,200))
        screen.blit(t, (px+10, y))
        y += 20


def draw_victory():
    if game.winner:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        screen.blit(overlay, (0,0))
        
        color = BLUE if game.winner == 'player' else RED
        msg = "🏆 胜利！" if game.winner == 'player' else "💀 失败！"
        t = font_big.render(msg, True, color)
        screen.blit(t, (W//2-60, H//2-30))
        
        t2 = font.render("按 R 重新开始 | 按 Q 退出", True, WHITE)
        screen.blit(t2, (W//2-100, H//2+10))


def render():
    draw_map()
    draw_mines()
    draw_buildings()
    draw_units()
    draw_selection_box()
    draw_panel()
    draw_victory()
    pygame.display.flip()


# ═══════════════════════════════════════════════
# 输入处理
# ═══════════════════════════════════════════════

def handle_mouse_down(pos: Tuple[int,int]):
    x, y = pos
    map_w = W - PANEL_W
    
    if game.winner:
        return
    
    # 检查面板按钮点击
    if x >= map_w:
        handle_panel_click(x, y)
        return
    
    # 检查是否点击了单位
    clicked_unit = None
    for u in game.units:
        if u.owner == 'player':
            dist = math.hypot(u.x - x, u.y - y)
            if dist < 16:
                clicked_unit = u
                break
    
    if clicked_unit:
        # Shift+点击 = 多选
        keys = pygame.key.get_pressed()
        if not (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]):
            for u in game.units:
                u.selected = False
            game.selection.clear()
        clicked_unit.selected = True
        if clicked_unit not in game.selection:
            game.selection.append(clicked_unit)
        game.drag_start = None
    else:
        # 清空选择，开始框选
        for u in game.units:
            u.selected = False
        game.selection.clear()
        game.drag_start = (x, y)
        game.drag_end = (x, y)


def handle_mouse_up(pos: Tuple[int,int]):
    x, y = pos
    map_w = W - PANEL_W
    
    if game.winner:
        return
    
    # 框选结束
    if game.drag_start:
        game.drag_end = (x, y)
        x1, y1 = game.drag_start
        x2, y2 = game.drag_end
        rx, ry = min(x1,x2), min(y1,y2)
        rw, rh = abs(x2-x1), abs(y2-y1)
        
        if rw > 5 or rh > 5:
            # 框选
            game.selection.clear()
            for u in game.units:
                if u.owner == 'player':
                    if rx <= u.x <= rx+rw and ry <= u.y <= ry+rh:
                        u.selected = True
                        game.selection.append(u)
            sel = [u.utype for u in game.selection]
            game.log_add(f"选中: {len(game.selection)} 个单位")
        
        game.drag_start = None
        game.drag_end = None


def handle_right_click(pos: Tuple[int,int]):
    """右键：命令选中的单位移动或攻击"""
    x, y = pos
    map_w = W - PANEL_W
    
    if game.winner:
        return
    if x >= map_w:
        return
    if not game.selection:
        return
    
    # 检查右键目标：敌方单位？
    target_enemy = None
    for u in game.units:
        if u.owner == 'enemy':
            if math.hypot(u.x-x, u.y-y) < 20:
                target_enemy = u
                break
    
    # 敌方建筑？
    target_building = None
    if not target_enemy:
        for b in game.buildings:
            if b.owner == 'enemy':
                if b.x <= x <= b.x+b.w and b.y <= y <= b.y+b.h:
                    target_building = b
                    break
    
    for u in game.selection:
        if target_enemy:
            u.target_enemy = target_enemy
            u.target_x, u.target_y = target_enemy.x, target_enemy.y
        elif target_building:
            u.target_enemy = target_building
            u.target_x, u.target_y = target_building.x + target_building.w/2, target_building.y + target_building.h/2
        else:
            u.target_enemy = None
            u.target_x, u.target_y = clamp_to_map(x, y)
    
    if target_enemy:
        game.log_add(f"⚔ 攻击敌方 {target_enemy.utype}！")
    elif target_building:
        game.log_add(f"⚔ 攻击敌方 {target_building.btype}！")
    else:
        game.log_add(f"📍 移动到 ({int(x)},{int(y)})")


def handle_panel_click(x: int, y: int):
    """右侧面板按钮"""
    map_w = W - PANEL_W
    rel_y = y
    
    buttons_y = [100, 138, 176, 214]  # 按钮Y坐标（相对于面板顶部）
    # 实际需要根据draw_panel中的布局计算
    # 简化：根据Y偏移判断
    
    offset = rel_y - 95
    if offset < 0:
        return
    
    btn_idx = offset // 38
    
    hq = game.player_hq()
    if not hq:
        return
    
    if btn_idx == 0:
        # 建造兵营
        if not game.has_barracks('player') and game.player_gold >= 200:
            game.player_gold -= 200
            bx, by = hq.x + 80, hq.y + 10
            game.buildings.append(Building('player', 'barracks', bx, by))
            game.log_add("🏚 兵营建造完成！")
    elif btn_idx == 1:
        # 训练工人
        if game.player_gold >= 100:
            game.player_gold -= 100
            u = Unit('player', 'worker', hq.x+30, hq.y+70)
            game.units.append(u)
            game.log_add("👷 新工人报到！")
    elif btn_idx == 2:
        # 训练士兵
        if game.has_barracks('player') and game.player_gold >= 150:
            game.player_gold -= 150
            u = Unit('player', 'soldier', hq.x+30, hq.y+70)
            game.units.append(u)
            game.log_add("⚔ 新士兵就绪！")
    elif btn_idx == 3:
        # 训练坦克
        if game.has_barracks('player') and game.player_gold >= 300:
            game.player_gold -= 300
            u = Unit('player', 'tank', hq.x+30, hq.y+70)
            game.units.append(u)
            game.log_add("🛡 坦克出厂！")


# ═══════════════════════════════════════════════
# 游戏逻辑
# ═══════════════════════════════════════════════

def update_worker(unit: Unit):
    """工人AI：去采矿 → 满15 → 回HQ交付"""
    hq = game.player_hq() if unit.owner == 'player' else game.enemy_hq()
    if not hq:
        return
    
    if unit.carry_gold >= 15:
        # 回HQ交付
        tx, ty = hq.x + hq.w/2, hq.y + hq.h/2
        if move_toward(unit, tx, ty, unit.speed):
            if unit.owner == 'player':
                game.player_gold += unit.carry_gold
            else:
                game.enemy_gold += unit.carry_gold
            unit.carry_gold = 0
            unit.target_x, unit.target_y = unit.x, unit.y
    else:
        # 找最近的矿
        mine = game.nearest_mine(unit)
        if mine:
            if move_toward(unit, mine.x, mine.y, unit.speed):
                unit.carry_gold = min(15, unit.carry_gold + 5)
        else:
            # 没有矿了，回HQ待命
            move_toward(unit, hq.x+hq.w/2, hq.y+hq.h/2, unit.speed)


def update_combat_unit(unit: Unit):
    """战斗单位AI"""
    # 如果被命令攻击
    if unit.target_enemy:
        target = unit.target_enemy
        # 获取目标位置
        if isinstance(target, Unit):
            tx, ty = target.x, target.y
        else:  # Building
            tx, ty = target.x + target.w/2, target.y + target.h/2
        
        dist = math.hypot(tx - unit.x, ty - unit.y)
        
        if isinstance(target, Unit):
            attack_range = 25
        else:
            attack_range = 40
        
        if dist <= attack_range:
            # 在攻击范围内
            if unit.attack_cd <= 0:
                target.hp -= unit.atk
                unit.attack_cd = 20
                if target.hp <= 0:
                    unit.target_enemy = None
            return
        else:
            move_toward(unit, tx, ty, unit.speed)
    else:
        # 移动到目标点
        move_toward(unit, unit.target_x, unit.target_y, unit.speed)


def update_enemy_ai():
    """简单AI"""
    hq = game.enemy_hq()
    if not hq:
        return
    
    eu = game.units_of('enemy')
    workers = sum(1 for u in eu if u.utype == 'worker')
    soldiers = sum(1 for u in eu if u.utype == 'soldier')
    tanks = sum(1 for u in eu if u.utype == 'tank')
    
    # 保证至少2个工人
    if workers < 2 and game.enemy_gold >= 100:
        game.enemy_gold -= 100
        game.units.append(Unit('enemy', 'worker', hq.x+10, hq.y-20))
    
    # 建造兵营
    if not game.has_barracks('enemy') and game.enemy_gold >= 200:
        game.enemy_gold -= 200
        bx, by = hq.x - 50, hq.y - 20
        game.buildings.append(Building('enemy', 'barracks', bx, by))
    
    # 造兵
    if game.has_barracks('enemy') and game.enemy_gold >= 200:
        if soldiers < 6:
            game.enemy_gold -= 150
            game.units.append(Unit('enemy', 'soldier', hq.x+10, hq.y-20))
        elif game.enemy_gold >= 300 and tanks < 3:
            game.enemy_gold -= 300
            game.units.append(Unit('enemy', 'tank', hq.x+10, hq.y-20))
    
    # 命令闲置的战斗单位攻击
    for u in eu:
        if u.utype != 'worker' and u.target_enemy is None:
            # 每15帧检查
            if random.random() < 0.03:
                target = game.nearest_enemy(u)
                if target:
                    u.target_enemy = target
                    if isinstance(target, Unit):
                        u.target_x, u.target_y = target.x, target.y
                    else:
                        u.target_x = target.x + target.w/2
                        u.target_y = target.y + target.h/2


def check_victory():
    """检查胜负"""
    phq = game.player_hq()
    ehq = game.enemy_hq()
    
    if ehq and ehq.hp <= 0:
        game.winner = 'player'
        game.log_add("🏆 摧毁敌方HQ，胜利！")
        return
    if phq and phq.hp <= 0:
        game.winner = 'enemy'
        game.log_add("💀 你的HQ被摧毁，失败！")
        return
    
    # 清理死亡单位
    dead = [u for u in game.units if u.hp <= 0]
    for u in dead:
        if u in game.selection:
            game.selection.remove(u)
        game.units.remove(u)
        # 击杀奖励
        killer_owner = 'player' if u.owner == 'enemy' else 'enemy'
        if killer_owner == 'player':
            game.player_gold += 50
    
    # 清理死亡建筑
    dead_b = [b for b in game.buildings if b.hp <= 0 and b.btype != 'hq']
    for b in dead_b:
        game.buildings.remove(b)


def update():
    if game.winner:
        return
    
    # 更新所有单位
    for u in game.units:
        if u.attack_cd > 0:
            u.attack_cd -= 1
        
        if u.utype == 'worker':
            update_worker(u)
        else:
            update_combat_unit(u)
    
    update_enemy_ai()
    check_victory()


# ═══════════════════════════════════════════════
# 主循环
# ═══════════════════════════════════════════════

def main():
    global game
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键
                    handle_mouse_down(event.pos)
                elif event.button == 3:  # 右键
                    handle_right_click(event.pos)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    handle_mouse_up(event.pos)
            
            elif event.type == pygame.MOUSEMOTION:
                game.mouse_pos = event.pos
                if game.drag_start:
                    game.drag_end = event.pos
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and game.winner:
                    # 重新开始
                    game = Game()
                elif event.key == pygame.K_q and game.winner:
                    running = False
                elif event.key == pygame.K_ESCAPE:
                    for u in game.units:
                        u.selected = False
                    game.selection.clear()
        
        update()
        render()
        clock.tick(60)
    
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
