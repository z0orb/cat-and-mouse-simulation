import pygame
import random
from collections import deque
from enum import Enum
import time
import os

pygame.init()

WINDOW_WIDTH = 600
WINDOW_HEIGHT = 670  
GRID_SIZE = 12
CELL_SIZE = 600 // GRID_SIZE  
FPS = 60
BASE_TURN_DELAY = 800  
BASE_MOVE_ANIMATION_SPEED = 0.3  

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
BROWN = (139, 69, 19)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
LIGHT_BLUE = (135, 206, 250)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
DARK_GRAY = (64, 64, 64)

class TextureManager:   
    def __init__(self):
        self.textures = {}
        self.load_textures()
    
    def load_textures(self):
        """Attempt to load texture images, fallback to None if not found"""
        texture_files = {
            'wall': 'wall.jpg',
            'path': 'path.jpg',
            'door_closed': 'door_closed.jpg',
            'door_open': 'door_open.jpg',
            'cat': 'cat.jpg',
            'mouse1': 'mouse1.jpg',
            'mouse2': 'mouse2.jpg',
            'cheese': 'cheese.png',
            'menu_bg': 'menu_bg.jpg'   
        }
        
        for key, filename in texture_files.items():
            try:
                if os.path.exists(filename):
                    image = pygame.image.load(filename)

                    if key == 'menu_bg':
                        image = pygame.transform.scale(image, (WINDOW_WIDTH, WINDOW_HEIGHT))
                    else:
                        image = pygame.transform.scale(image, (CELL_SIZE, CELL_SIZE))

                    self.textures[key] = image
                    print(f"✓ Loaded texture: {filename}")
                else:
                    self.textures[key] = None
            except Exception as e:
                print(f"✗ Failed to load {filename}: {e}")
                self.textures[key] = None
    
    def get_texture(self, texture_name):
        """Get texture if available, returns None for fallback to solid color"""
        return self.textures.get(texture_name)


class GridType(Enum):
    PATH = 0
    WALL = 1
    DOOR = 2

class Character:
    def __init__(self, x, y, mp, color, texture_name=None):
        self.x = x
        self.y = y
        self.display_x = float(x)
        self.display_y = float(y)
        self.mp = mp
        self.max_mp = mp
        self.color = color
        self.texture_name = texture_name
        self.path = []
        self.target = None
        self.is_animating = False
        
    def draw(self, screen, texture_manager, highlight=False):
        rect = pygame.Rect(int(self.display_x * CELL_SIZE), int(self.display_y * CELL_SIZE), CELL_SIZE, CELL_SIZE)
        
        if highlight:
            pygame.draw.rect(screen, GREEN, rect.inflate(4, 4), 3)
        
        texture = texture_manager.get_texture(self.texture_name) if self.texture_name else None
        if texture:
            screen.blit(texture, rect)
        else:
            pygame.draw.circle(screen, self.color, rect.center, CELL_SIZE // 3)
    
    def get_center(self):
        return (int(self.display_x * CELL_SIZE + CELL_SIZE // 2), 
                int(self.display_y * CELL_SIZE + CELL_SIZE // 2))
    
    def update_animation(self, speed_multiplier=1.0):
        """Smoothly animate character towards target position"""
        animation_speed = BASE_MOVE_ANIMATION_SPEED * speed_multiplier
        
        if abs(self.display_x - self.x) > 0.01:
            dx = (self.x - self.display_x)
            self.display_x += dx * animation_speed
            self.is_animating = True
        else:
            self.display_x = float(self.x)
            
        if abs(self.display_y - self.y) > 0.01:
            dy = (self.y - self.display_y)
            self.display_y += dy * animation_speed
            self.is_animating = True
        else:
            self.display_y = float(self.y)
        
        if abs(self.display_x - self.x) <= 0.01 and abs(self.display_y - self.y) <= 0.01:
            self.is_animating = False
            self.display_x = float(self.x)
            self.display_y = float(self.y)
        
        return self.is_animating
        
class Cat(Character):
    def __init__(self, x, y):
        super().__init__(x, y, 2, RED, texture_name='cat')
        
class Mouse(Character):
    def __init__(self, x, y, mouse_id=1):
        color = BLUE if mouse_id == 1 else LIGHT_BLUE
        texture_name = 'mouse1' if mouse_id == 1 else 'mouse2'
        super().__init__(x, y, 1, color, texture_name=texture_name)
        self.alive = True
        self.mouse_id = mouse_id

class Cheese:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.eaten = False
        
    def draw(self, screen, texture_manager, highlight=False):
        if not self.eaten:
            rect = pygame.Rect(self.x * CELL_SIZE, self.y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            
            if highlight:
                pygame.draw.rect(screen, GREEN, rect.inflate(4, 4), 3)
            
            texture = texture_manager.get_texture('cheese')
            if texture:
                screen.blit(texture, rect)
            else:
                pygame.draw.circle(screen, YELLOW, rect.center, CELL_SIZE // 4)
    
    def get_center(self):
        return (self.x * CELL_SIZE + CELL_SIZE // 2, 
                self.y * CELL_SIZE + CELL_SIZE // 2)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Cat and Mouse Simulation")
        self.clock = pygame.time.Clock()
        self.texture_manager = TextureManager()
        self.state = "MENU"
        self.grid = [[GridType.PATH for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.door_states = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.cat = None
        self.mice = []
        self.cheeses = []
        self.current_turn = 0
        self.turn_phase = "ANNOUNCE_CAT"
        self.winner = None
        self.last_turn_time = 0
        self.current_mouse_index = 0
        self.pending_moves = []
        self.current_character = None
        self.door_opening_animation = None
        self.claimed_cheeses = {}
        self.speed_multiplier = 1.0
        
        self.speed_1x_button = pygame.Rect(420, 610, 80, 50)
        self.speed_2x_button = pygame.Rect(510, 610, 80, 50)
    
    def generate_maze_dfs(self):
        """Generate maze using DFS algorithm"""
        maze = [[GridType.WALL for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        
        stack = [(1, 1)]
        maze[1][1] = GridType.PATH
        
        while stack:
            current = stack[-1]
            x, y = current
            
            neighbors = []
            for dx, dy in [(0, 2), (2, 0), (0, -2), (-2, 0)]:
                nx, ny = x + dx, y + dy
                if 1 <= nx < GRID_SIZE - 1 and 1 <= ny < GRID_SIZE - 1:
                    if maze[ny][nx] == GridType.WALL:
                        neighbors.append((nx, ny, dx, dy))
            
            if neighbors:
                nx, ny, dx, dy = random.choice(neighbors)
                maze[y + dy // 2][x + dx // 2] = GridType.PATH
                maze[ny][nx] = GridType.PATH
                stack.append((nx, ny))
            else:
                stack.pop()
        
        for _ in range(GRID_SIZE * 2):
            x = random.randrange(2, GRID_SIZE - 2, 2)
            y = random.randrange(2, GRID_SIZE - 2, 2)
            
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if maze[ny][nx] == GridType.WALL:
                    if maze[y + dy * 2][x + dx * 2] == GridType.PATH:
                        maze[ny][nx] = GridType.PATH
                        break
        
        return maze
    
    def place_doors_at_chokepoints(self, maze):
        """Place doors at strategic chokepoints"""
        door_count = 0
        max_doors = 3
        
        for i in range(2, GRID_SIZE - 2):
            for j in range(2, GRID_SIZE - 2):
                if maze[i][j] == GridType.PATH and door_count < max_doors:
                    adjacent_paths = 0
                    for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        if maze[i + dy][j + dx] == GridType.PATH:
                            adjacent_paths += 1
                    
                    if adjacent_paths == 2 and random.random() < 0.15:
                        maze[i][j] = GridType.DOOR
                        door_count += 1
        
        return maze
    
    def generate_map(self):
        """Generate complete map"""
        self.grid = self.generate_maze_dfs()
        self.grid = self.place_doors_at_chokepoints(self.grid)
        self.door_states = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        
        valid_positions = []
        for i in range(1, GRID_SIZE - 1):
            for j in range(1, GRID_SIZE - 1):
                if self.grid[i][j] == GridType.PATH:
                    valid_positions.append((i, j))
        
        if len(valid_positions) < 9:
            return self.generate_map()
        
        random.shuffle(valid_positions)
        
        cat_pos = valid_positions.pop()
        self.cat = Cat(cat_pos[1], cat_pos[0])
        
        self.mice = []
        for i in range(2):
            mouse_pos = valid_positions.pop()
            self.mice.append(Mouse(mouse_pos[1], mouse_pos[0], mouse_id=i+1))
        
        self.cheeses = []
        for _ in range(6):
            cheese_pos = valid_positions.pop()
            self.cheeses.append(Cheese(cheese_pos[1], cheese_pos[0]))
        
        self.claimed_cheeses = {}
    
    def bfs_pathfind(self, start_x, start_y, target_x, target_y):
        """BFS pathfinding"""
        queue = deque([(start_x, start_y, [])])
        visited = {(start_x, start_y)}
        
        while queue:
            x, y, path = queue.popleft()
            
            if x == target_x and y == target_y:
                return path
            
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    if (nx, ny) not in visited:
                        cell = self.grid[ny][nx]
                        
                        if cell == GridType.WALL:
                            continue
                        
                        visited.add((nx, ny))
                        new_path = path + [(nx, ny)]
                        queue.append((nx, ny, new_path))
        
        return []
    
    def find_nearest_target(self, character, targets):
        """Find nearest target using BFS"""
        min_dist = float('inf')
        nearest = None
        
        for target in targets:
            path = self.bfs_pathfind(character.x, character.y, target.x, target.y)
            if path and len(path) < min_dist:
                min_dist = len(path)
                nearest = target
        
        return nearest
    
    def find_nearest_unclaimed_cheese(self, mouse):
        """Find nearest cheese that isn't claimed by another mouse"""
        uneaten_cheese = [c for c in self.cheeses if not c.eaten]
        
        available_cheese = []
        for cheese in uneaten_cheese:
            cheese_id = id(cheese)
            if cheese_id not in self.claimed_cheeses or self.claimed_cheeses[cheese_id] == id(mouse):
                available_cheese.append(cheese)
        
        if not available_cheese:
            available_cheese = uneaten_cheese
        
        return self.find_nearest_target(mouse, available_cheese)
    
    def plan_cat_turn(self):
        """Plan cat's turn"""
        alive_mice = [m for m in self.mice if m.alive]
        if not alive_mice:
            return []
        
        target = self.find_nearest_target(self.cat, alive_mice)
        if not target:
            return []
        
        self.cat.target = target
        path = self.bfs_pathfind(self.cat.x, self.cat.y, target.x, target.y)
        
        if not path:
            return []
        
        moves = []
        mp_remaining = 2
        
        for next_x, next_y in path:
            if mp_remaining <= 0:
                break
                
            if self.grid[next_y][next_x] == GridType.DOOR and not self.door_states[next_y][next_x]:
                moves.append(('open_door', next_x, next_y))
                mp_remaining -= 1
                
                if mp_remaining > 0:
                    moves.append(('move', next_x, next_y))
                    mp_remaining -= 1
                else:
                    break
            else:
                moves.append(('move', next_x, next_y))
                mp_remaining -= 1
        
        return moves
    
    def plan_mouse_turn(self, mouse):
        """Plan mouse's turn"""
        if not mouse.alive:
            return []
        
        target = self.find_nearest_unclaimed_cheese(mouse)
        if not target:
            return []
        
        self.claimed_cheeses[id(target)] = id(mouse)
        
        mouse.target = target
        path = self.bfs_pathfind(mouse.x, mouse.y, target.x, target.y)
        
        if not path:
            return []
        
        next_x, next_y = path[0]
        
        if self.grid[next_y][next_x] == GridType.DOOR and not self.door_states[next_y][next_x]:
            return [('open_door', next_x, next_y)]
        else:
            return [('move', next_x, next_y)]
    
    def execute_next_move(self):
        """Execute the next move in the queue"""
        if not self.pending_moves:
            return True
        
        if self.current_character and self.current_character.is_animating:
            return False
        
        if self.door_opening_animation:
            elapsed = pygame.time.get_ticks() - self.door_opening_animation
            door_delay = int(300 / self.speed_multiplier)
            if elapsed < door_delay:
                return False
            else:
                self.door_opening_animation = None
        
        action, x, y = self.pending_moves.pop(0)
        
        if action == 'open_door':
            self.door_states[y][x] = True
            self.door_opening_animation = pygame.time.get_ticks()
        elif action == 'move':
            self.current_character.x = x
            self.current_character.y = y
            self.current_character.is_animating = True
            
            if isinstance(self.current_character, Cat):
                for mouse in self.mice:
                    if mouse.alive and mouse.x == self.current_character.x and mouse.y == self.current_character.y:
                        mouse.alive = False
                        mouse.target = None
                        cheese_to_unclaim = [k for k, v in self.claimed_cheeses.items() if v == id(mouse)]
                        for cheese_id in cheese_to_unclaim:
                            del self.claimed_cheeses[cheese_id]
            
            if isinstance(self.current_character, Mouse):
                for cheese in self.cheeses:
                    if not cheese.eaten and cheese.x == self.current_character.x and cheese.y == self.current_character.y:
                        cheese.eaten = True
                        self.current_character.target = None
                        if id(cheese) in self.claimed_cheeses:
                            del self.claimed_cheeses[id(cheese)]
        
        return False
    
    def process_turn(self):
        """Process turn phases"""
        current_time = pygame.time.get_ticks()
        
        if self.pending_moves or (self.current_character and self.current_character.is_animating):
            turn_complete = self.execute_next_move()
            if not turn_complete:
                return
        
        turn_delay = int(BASE_TURN_DELAY / self.speed_multiplier)
        if current_time - self.last_turn_time < turn_delay:
            return
        
        self.last_turn_time = current_time
        
        if self.turn_phase == "ANNOUNCE_CAT":
            self.turn_phase = "EXECUTE_CAT"
        
        elif self.turn_phase == "EXECUTE_CAT":
            self.current_character = self.cat
            self.pending_moves = self.plan_cat_turn()
            if not self.pending_moves:
                if len(self.mice) > 0 and self.mice[0].alive:
                    self.turn_phase = "ANNOUNCE_MOUSE1"
                elif len(self.mice) > 1 and self.mice[1].alive:
                    self.turn_phase = "ANNOUNCE_MOUSE2"
                else:
                    self.current_turn += 1
                    self.turn_phase = "ANNOUNCE_CAT"
            else:
                self.turn_phase = "EXECUTING_CAT"
        
        elif self.turn_phase == "EXECUTING_CAT":
            if not self.pending_moves and not self.current_character.is_animating:
                if len(self.mice) > 0 and self.mice[0].alive:
                    self.turn_phase = "ANNOUNCE_MOUSE1"
                elif len(self.mice) > 1 and self.mice[1].alive:
                    self.turn_phase = "ANNOUNCE_MOUSE2"
                else:
                    self.current_turn += 1
                    self.turn_phase = "ANNOUNCE_CAT"
                self.last_turn_time = current_time
        
        elif self.turn_phase == "ANNOUNCE_MOUSE1":
            self.current_mouse_index = 0
            if len(self.mice) > 0 and self.mice[0].alive:
                self.turn_phase = "EXECUTE_MOUSE1"
            else:
                if len(self.mice) > 1 and self.mice[1].alive:
                    self.turn_phase = "ANNOUNCE_MOUSE2"
                else:
                    self.current_turn += 1
                    self.turn_phase = "ANNOUNCE_CAT"
        
        elif self.turn_phase == "EXECUTE_MOUSE1":
            if len(self.mice) > 0 and self.mice[0].alive:
                self.current_character = self.mice[0]
                self.pending_moves = self.plan_mouse_turn(self.mice[0])
            if not self.pending_moves:
                if len(self.mice) > 1 and self.mice[1].alive:
                    self.turn_phase = "ANNOUNCE_MOUSE2"
                else:
                    self.current_turn += 1
                    self.turn_phase = "ANNOUNCE_CAT"
            else:
                self.turn_phase = "EXECUTING_MOUSE1"
        
        elif self.turn_phase == "EXECUTING_MOUSE1":
            if not self.pending_moves and not self.current_character.is_animating:
                if len(self.mice) > 1 and self.mice[1].alive:
                    self.turn_phase = "ANNOUNCE_MOUSE2"
                else:
                    self.current_turn += 1
                    self.turn_phase = "ANNOUNCE_CAT"
                self.last_turn_time = current_time
        
        elif self.turn_phase == "ANNOUNCE_MOUSE2":
            self.current_mouse_index = 1
            if len(self.mice) > 1 and self.mice[1].alive:
                self.turn_phase = "EXECUTE_MOUSE2"
            else:
                self.current_turn += 1
                self.turn_phase = "ANNOUNCE_CAT"
        
        elif self.turn_phase == "EXECUTE_MOUSE2":
            if len(self.mice) > 1 and self.mice[1].alive:
                self.current_character = self.mice[1]
                self.pending_moves = self.plan_mouse_turn(self.mice[1])
            if not self.pending_moves:
                self.current_turn += 1
                self.turn_phase = "ANNOUNCE_CAT"
            else:
                self.turn_phase = "EXECUTING_MOUSE2"
        
        elif self.turn_phase == "EXECUTING_MOUSE2":
            if not self.pending_moves and not self.current_character.is_animating:
                self.current_turn += 1
                self.turn_phase = "ANNOUNCE_CAT"
                self.last_turn_time = current_time
        
        self.check_victory()
    
    def check_victory(self):
        """Check if either side has won"""
        alive_mice = [m for m in self.mice if m.alive]
        uneaten_cheese = [c for c in self.cheeses if not c.eaten]
        
        if not alive_mice:
            self.winner = "CAT"
        elif not uneaten_cheese:
            self.winner = "MICE"
    
    def draw_pathfinding_lines(self):
        """Draw lines from characters to their targets"""
        if self.cat and self.cat.target and self.cat.target.alive:
            cat_center = self.cat.get_center()
            mouse_center = self.cat.target.get_center()
            pygame.draw.line(self.screen, self.cat.color, cat_center, mouse_center, 2)
        
        for mouse in self.mice:
            if mouse.alive and mouse.target and not mouse.target.eaten:
                mouse_center = mouse.get_center()
                cheese_center = mouse.target.get_center()
                pygame.draw.line(self.screen, mouse.color, mouse_center, cheese_center, 2)
    
    def draw_menu(self):

        bg = self.texture_manager.get_texture("menu_bg")
        if bg:
            self.screen.blit(bg, (0, 0))
        else:
            self.screen.fill(WHITE)  


        font_large = pygame.font.Font(None, 64)

        title = font_large.render("Cat and Mouse", True, BLACK)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3))
        self.screen.blit(title, title_rect)
            
        subtitle = font_large.render("Simulation", True, BLACK)
        subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3 + 70))
        self.screen.blit(subtitle, subtitle_rect)

        
        font = pygame.font.Font(None, 42)
            
        start_button = pygame.Rect(WINDOW_WIDTH // 2 - 150, WINDOW_HEIGHT * 2 // 3, 300, 60)
        quit_button = pygame.Rect(WINDOW_WIDTH // 2 - 150, WINDOW_HEIGHT * 2 // 3 + 80, 300, 60)
            
        pygame.draw.rect(self.screen, GREEN, start_button)
        pygame.draw.rect(self.screen, RED, quit_button)
            
        start_text = font.render("Start Simulation", True, BLACK)
        quit_text = font.render("Quit Game", True, BLACK)
            
        self.screen.blit(start_text, start_text.get_rect(center=start_button.center))
        self.screen.blit(quit_text, quit_text.get_rect(center=quit_button.center))
            
        return start_button, quit_button

    
    def draw_turn_announcement(self):
        """Draw turn announcement (only for alive entities)"""
        overlay = pygame.Surface((WINDOW_WIDTH, 600))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        font_large = pygame.font.Font(None, 80)
        
        if "CAT" in self.turn_phase:
            text = font_large.render("CAT'S TURN", True, RED)
        elif "MOUSE1" in self.turn_phase and len(self.mice) > 0 and self.mice[0].alive:
            text = font_large.render("MOUSE 1'S TURN", True, BLUE)
        elif "MOUSE2" in self.turn_phase and len(self.mice) > 1 and self.mice[1].alive:
            text = font_large.render("MOUSE 2'S TURN", True, LIGHT_BLUE)
        else:
            return
        
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, 300))
        self.screen.blit(text, text_rect)
    
    def draw_speed_controls(self):
        """Draw speed control buttons"""
        color_1x = GREEN if self.speed_multiplier == 1.0 else DARK_GRAY
        pygame.draw.rect(self.screen, color_1x, self.speed_1x_button)
        pygame.draw.rect(self.screen, BLACK, self.speed_1x_button, 2)
        
        color_2x = GREEN if self.speed_multiplier == 2.0 else DARK_GRAY
        pygame.draw.rect(self.screen, color_2x, self.speed_2x_button)
        pygame.draw.rect(self.screen, BLACK, self.speed_2x_button, 2)
        
        font = pygame.font.Font(None, 32)
        text_1x = font.render("1x", True, WHITE)
        text_2x = font.render("2x", True, WHITE)
        
        self.screen.blit(text_1x, text_1x.get_rect(center=self.speed_1x_button.center))
        self.screen.blit(text_2x, text_2x.get_rect(center=self.speed_2x_button.center))
    
    def draw_game(self):
        self.screen.fill(WHITE)
        
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                rect = pygame.Rect(j * CELL_SIZE, i * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                
                if self.grid[i][j] == GridType.WALL:
                    texture = self.texture_manager.get_texture('wall')
                    if texture:
                        self.screen.blit(texture, rect)
                    else:
                        pygame.draw.rect(self.screen, GRAY, rect)
                        
                elif self.grid[i][j] == GridType.DOOR:
                    if self.door_states[i][j]:
                        texture = self.texture_manager.get_texture('door_open')
                        if texture:
                            self.screen.blit(texture, rect)
                        else:
                            pygame.draw.rect(self.screen, WHITE, rect)
                            pygame.draw.rect(self.screen, BROWN, rect, 2)
                    else:
                        texture = self.texture_manager.get_texture('door_closed')
                        if texture:
                            self.screen.blit(texture, rect)
                        else:
                            pygame.draw.rect(self.screen, BROWN, rect)
                else:
                    texture = self.texture_manager.get_texture('path')
                    if texture:
                        self.screen.blit(texture, rect)
                    else:
                        pygame.draw.rect(self.screen, WHITE, rect)
                
                pygame.draw.rect(self.screen, BLACK, rect, 1)
        
        self.draw_pathfinding_lines()
        
        for cheese in self.cheeses:
            cheese.draw(self.screen, self.texture_manager)
        
        for mouse in self.mice:
            if mouse.alive:
                mouse.draw(self.screen, self.texture_manager)
        
        self.cat.draw(self.screen, self.texture_manager)
        
        if "CAT" in self.turn_phase and self.cat.target and self.cat.target.alive:
            self.cat.target.draw(self.screen, self.texture_manager, True)
        elif "MOUSE1" in self.turn_phase and len(self.mice) > 0 and self.mice[0].alive:
            if self.mice[0].target:
                self.mice[0].target.draw(self.screen, self.texture_manager, True)
        elif "MOUSE2" in self.turn_phase and len(self.mice) > 1 and self.mice[1].alive:
            if self.mice[1].target:
                self.mice[1].target.draw(self.screen, self.texture_manager, True)
        
        if "ANNOUNCE" in self.turn_phase:
            self.draw_turn_announcement()
        
        overlay = pygame.Surface((WINDOW_WIDTH, 70))
        overlay.set_alpha(220)
        overlay.fill(WHITE)
        self.screen.blit(overlay, (0, 0))
        
        font = pygame.font.Font(None, 24)
        turn_text = font.render(f"Turn: {self.current_turn}", True, BLACK)
        self.screen.blit(turn_text, (10, 10))
        
        alive_mice = sum(1 for m in self.mice if m.alive)
        uneaten_cheese = sum(1 for c in self.cheeses if not c.eaten)
        
        status_text = font.render(f"Mice: {alive_mice}/2 | Cheese: {uneaten_cheese}/6", True, BLACK)
        self.screen.blit(status_text, (10, 35))
        
        self.draw_speed_controls()
        
        if self.winner:
            font_large = pygame.font.Font(None, 64)
            if self.winner == "CAT":
                winner_text = font_large.render("CAT WINS!", True, RED)
            else:
                winner_text = font_large.render("MICE WIN!", True, BLUE)
            winner_rect = winner_text.get_rect(center=(WINDOW_WIDTH // 2, 300))
            
            overlay = pygame.Surface((WINDOW_WIDTH, 600))
            overlay.set_alpha(200)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
            
            self.screen.blit(winner_text, winner_rect)
            
            font_small = pygame.font.Font(None, 32)
            continue_text = font_small.render("Press SPACE to return to menu", True, WHITE)
            continue_rect = continue_text.get_rect(center=(WINDOW_WIDTH // 2, 380))
            self.screen.blit(continue_text, continue_rect)
    
    def run(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    
                    if self.state == "MENU":
                        start_button, quit_button = self.draw_menu()
                        
                        if start_button.collidepoint(mouse_pos):
                            self.state = "GAME"
                            self.generate_map()
                            self.winner = None
                            self.current_turn = 0
                            self.turn_phase = "ANNOUNCE_CAT"
                            self.last_turn_time = pygame.time.get_ticks()
                            self.pending_moves = []
                            self.current_character = None
                        
                        if quit_button.collidepoint(mouse_pos):
                            running = False
                    
                    elif self.state == "GAME":
                        if self.speed_1x_button.collidepoint(mouse_pos):
                            self.speed_multiplier = 1.0
                        elif self.speed_2x_button.collidepoint(mouse_pos):
                            self.speed_multiplier = 2.0
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and self.winner:
                        self.state = "MENU"
            
            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "GAME":
                if not self.winner:
                    self.process_turn()
                
                if self.cat:
                    self.cat.update_animation(self.speed_multiplier)
                for mouse in self.mice:
                    if mouse.alive:
                        mouse.update_animation(self.speed_multiplier)
                
                self.draw_game()
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()