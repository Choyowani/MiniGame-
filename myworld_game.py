import pygame
import random
import math

pygame.init()

# 화면 설정
WIDTH, HEIGHT = 600, 1000
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("그림 주문 액션")

# 색상
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (50, 50, 50)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

clock = pygame.time.Clock()
FPS = 60

# 캔버스 영역
CANVAS_HEIGHT = 250
canvas_rect = pygame.Rect(0, HEIGHT - CANVAS_HEIGHT, WIDTH, CANVAS_HEIGHT)

# 플레이어 잉크
MAX_INK = 100

# 폰트 설정
font = pygame.font.Font(None, 36)
large_font = pygame.font.Font(None, 80)

# 게임 상태 변수
MAX_PASSES = 3
enemies_passed_count = 0
game_state = "RUNNING"
score = 0
ink = MAX_INK

# 난이도 변수
INITIAL_ENEMY_COUNT = 8
ENEMY_SPAWN_INTERVAL = 2000
SPAWN_DECREMENT = 150
MIN_SPAWN_INTERVAL = 500
last_enemy_spawn_time = 0
NEXT_DIFFICULTY_SCORE = 500

# Restart 버튼 Rect
restart_button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 120, 200, 50)

# 이미지 로드
try:
    BACKGROUND_IMAGE = pygame.image.load('background.png').convert()
    BACKGROUND_IMAGE = pygame.transform.scale(BACKGROUND_IMAGE, (WIDTH, HEIGHT))
except:
    BACKGROUND_IMAGE = None

try:
    CANVAS_BG_IMAGE = pygame.image.load('canvas_bg.png').convert()
    CANVAS_BG_IMAGE = pygame.transform.scale(CANVAS_BG_IMAGE, (WIDTH, CANVAS_HEIGHT))
except:
    CANVAS_BG_IMAGE = None

try:
    sprite_sheet = pygame.image.load('enemy.png').convert_alpha()
    frame_width = sprite_sheet.get_width() // 8
    frame_height = sprite_sheet.get_height() // 5
    first_frame_rect = pygame.Rect(0, 0, frame_width, frame_height)
    ENEMY_IMAGE = sprite_sheet.subsurface(first_frame_rect).copy()
    ENEMY_IMAGE = pygame.transform.scale(ENEMY_IMAGE, (60, 60))
except:
    ENEMY_IMAGE = None


class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        if ENEMY_IMAGE:
            self.image = ENEMY_IMAGE
        else:
            self.image = pygame.Surface((40, 40))
            self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect.x = random.randint(0, WIDTH - self.rect.width)
        self.rect.y = random.randint(-150, -40)
        self.speed = random.uniform(1, 3)

    def update(self):
        self.rect.y += self.speed


class Spell(pygame.sprite.Sprite):
    def __init__(self, image, start_pos, max_hits=1):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(topleft=start_pos)
        self.mask = pygame.mask.from_surface(self.image)
        self.speed = -5
        self.max_hits = max_hits
        self.current_hits = 0

    def update(self):
        self.rect.y += self.speed
        if self.rect.bottom < 0:
            self.kill()



class Item(pygame.sprite.Sprite):
    def __init__(self, x, y, item_type):
        super().__init__()
        self.item_type = item_type

        self.image = pygame.Surface((25, 25), pygame.SRCALPHA)
        if item_type == "SLOW":
            pygame.draw.circle(self.image, (0, 200, 255), (12, 12), 12)
        else:
            pygame.draw.circle(self.image, (255, 200, 0), (12, 12), 12)

        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 2

    def update(self):
        self.rect.y += self.speed

        # 캔버스에 닿으면 발동
        if self.rect.bottom >= HEIGHT - CANVAS_HEIGHT:
            self.activate()
            self.kill()

    def activate(self):
        global enemy_group, score

        if self.item_type == "SLOW":
            # 모든 적 느려짐
            for enemy in enemy_group:
                enemy.speed *= 0.35

        else:  # BOMB
            removed = len(enemy_group)
            enemy_group.empty()

            # 초기 적 다시 생성
            for _ in range(INITIAL_ENEMY_COUNT):
                enemy_group.add(Enemy())

            score += removed * 10


enemy_group = pygame.sprite.Group()
spell_group = pygame.sprite.Group()
item_group = pygame.sprite.Group()  

# 초기 적 생성
for _ in range(INITIAL_ENEMY_COUNT):
    enemy_group.add(Enemy())

# 그림 그리기
drawing = False
last_pos = None
player_canvas = pygame.Surface((WIDTH, CANVAS_HEIGHT), pygame.SRCALPHA)
player_canvas.fill((0, 0, 0, 0))
path_points = []


running = True
while running:
    clock.tick(FPS)
    current_time = pygame.time.get_ticks()

    # 배경
    if BACKGROUND_IMAGE:
        screen.blit(BACKGROUND_IMAGE, (0, 0))
    else:
        screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # GAME OVER 입력 처리
        if game_state == "GAME_OVER":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if restart_button_rect.collidepoint(event.pos):

                    enemies_passed_count = 0
                    score = 0
                    ink = MAX_INK

                    ENEMY_SPAWN_INTERVAL = 2000
                    NEXT_DIFFICULTY_SCORE = 500
                    last_enemy_spawn_time = pygame.time.get_ticks()

                    enemy_group.empty()
                    spell_group.empty()
                    item_group.empty()

                    for _ in range(INITIAL_ENEMY_COUNT):
                        enemy_group.add(Enemy())

                    player_canvas.fill((0, 0, 0, 0))
                    game_state = "RUNNING"

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # RUNNING 입력 처리
        if game_state == "RUNNING":

            if event.type == pygame.MOUSEBUTTONDOWN and canvas_rect.collidepoint(event.pos):
                drawing = True
                canvas_y = event.pos[1] - (HEIGHT - CANVAS_HEIGHT)
                last_pos = (event.pos[0], canvas_y)
                path_points = [last_pos]

            if event.type == pygame.MOUSEBUTTONUP and drawing:
                drawing = False

                if ink > 0:
                    spell_image = player_canvas.copy()
                    try:
                        bbox = spell_image.get_bounding_rect()
                    except:
                        bbox = spell_image.get_rect()

                    if bbox.width > 1 and bbox.height > 1:
                        cropped_image = spell_image.subsurface(bbox).copy()

                        total_path_length = 0
                        if len(path_points) > 1:
                            for i in range(len(path_points) - 1):
                                p1 = path_points[i]
                                p2 = path_points[i+1]
                                total_path_length += math.hypot(p2[0]-p1[0], p2[1]-p1[1])

                        MAX_HIT = max(1, int(total_path_length / 100))
                        ink_needed = total_path_length / 25

                        if ink >= ink_needed:
                            start_pos = (bbox.x, HEIGHT - CANVAS_HEIGHT + bbox.y)
                            spell = Spell(cropped_image, start_pos, max_hits=MAX_HIT)
                            spell_group.add(spell)
                            ink -= ink_needed

                player_canvas.fill((0, 0, 0, 0))
                path_points = []

            if event.type == pygame.MOUSEMOTION and drawing:
                x, y = event.pos
                canvas_y = y - (HEIGHT - CANVAS_HEIGHT)
                if last_pos:
                    new_pos = (x, canvas_y)
                    pygame.draw.line(player_canvas, BLUE, last_pos, new_pos, 5)
                    path_points.append(new_pos)
                last_pos = (x, canvas_y)

    # RUNNING 상태
    if game_state == "RUNNING":

        ink = min(MAX_INK, ink + 0.07)

        # 적 스폰
        if current_time - last_enemy_spawn_time > ENEMY_SPAWN_INTERVAL:
            enemy_group.add(Enemy())
            last_enemy_spawn_time = current_time

        # 업데이트
        spell_group.update()
        enemy_group.update()
        item_group.update()   

        # 적 통과
        enemies_to_pass = []
        for enemy in enemy_group:
            if enemy.rect.top > HEIGHT - CANVAS_HEIGHT:
                enemies_to_pass.append(enemy)

        for enemy in enemies_to_pass:
            enemies_passed_count += 1
            enemy.kill()
            enemy_group.add(Enemy())

        if enemies_passed_count >= MAX_PASSES:
            game_state = "GAME_OVER"

        # 충돌 처리
        for spell in spell_group:
            hit_enemies = pygame.sprite.spritecollide(spell, enemy_group, False, pygame.sprite.collide_mask)

            if hit_enemies:
                enemies_to_remove = []
                for enemy in hit_enemies:
                    if spell.current_hits < spell.max_hits:
                        enemies_to_remove.append(enemy)
                        spell.current_hits += 1

                for enemy in enemies_to_remove:
                    enemy.kill()
                    enemy_group.add(Enemy())
                    score += 10
                    ink = min(MAX_INK, ink + 2)

                    # 아이템 드랍 (25% 확률)
                    if random.random() < 0.1:
                        item_type = "SLOW" if random.random() < 0.8 else "BOMB"
                        item_group.add(Item(enemy.rect.centerx, enemy.rect.centery, item_type))

            if spell.current_hits >= spell.max_hits:
                spell.kill()

        # 난이도 증가
        if score >= NEXT_DIFFICULTY_SCORE:
            if ENEMY_SPAWN_INTERVAL > MIN_SPAWN_INTERVAL:
                ENEMY_SPAWN_INTERVAL -= SPAWN_DECREMENT
                ENEMY_SPAWN_INTERVAL = max(MIN_SPAWN_INTERVAL, ENEMY_SPAWN_INTERVAL)
            NEXT_DIFFICULTY_SCORE += 500

        # 그리기
        enemy_group.draw(screen)
        spell_group.draw(screen)
        item_group.draw(screen)   

        if CANVAS_BG_IMAGE:
            screen.blit(CANVAS_BG_IMAGE, canvas_rect.topleft)
        else:
            pygame.draw.rect(screen, GRAY, canvas_rect)

        screen.blit(player_canvas, (0, HEIGHT - CANVAS_HEIGHT))
        pygame.draw.rect(screen, GRAY, canvas_rect, 2)

        pygame.draw.rect(screen, WHITE, (10, 10, MAX_INK * 3, 20), 2)
        pygame.draw.rect(screen, BLUE, (10, 10, ink * 3, 20))

        score_text = font.render(f"Score: {score}", True, WHITE)
        pass_text = font.render(f"Passes: {enemies_passed_count} / {MAX_PASSES}", True, RED)
        screen.blit(score_text, (WIDTH - score_text.get_width() - 10, 10))
        screen.blit(pass_text, (WIDTH - pass_text.get_width() - 10, 40))

    # GAME OVER 화면
    elif game_state == "GAME_OVER":

        game_over_text = large_font.render("GAME OVER", True, RED)
        score_final_text = font.render(f"Final Score: {score}", True, WHITE)
        quit_text = font.render("ESC to Quit", True, GRAY)

        screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width()//2, HEIGHT//2 - 80))
        screen.blit(score_final_text, (WIDTH // 2 - score_final_text.get_width()//2, HEIGHT//2))
        screen.blit(quit_text, (WIDTH // 2 - quit_text.get_width()//2, HEIGHT//2 + 40))

        pygame.draw.rect(screen, WHITE, restart_button_rect, border_radius=10)
        restart_text2 = font.render("RESTART", True, BLACK)
        screen.blit(
            restart_text2,
            (
                restart_button_rect.x + (restart_button_rect.width - restart_text2.get_width()) // 2,
                restart_button_rect.y + (restart_button_rect.height - restart_text2.get_height()) // 2
            )
        )

    pygame.display.flip()

pygame.quit()
