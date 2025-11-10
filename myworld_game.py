import pygame
import random
import math

pygame.init()

# 화면 설정
WIDTH, HEIGHT = 800, 1000
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
ink = MAX_INK

# 폰트 설정
font = pygame.font.Font(None, 36)
large_font = pygame.font.Font(None, 80) # 게임 오버용 큰 폰트

# ⚔️ 게임 상태 변수
MAX_PASSES = 3 # 최대 허용 적 통과 횟수
enemies_passed_count = 0
game_state = "RUNNING"
score = 0

# ⏱️ 난이도 변수 추가
INITIAL_ENEMY_COUNT = 8 # 시작 시 적의 수
ENEMY_SPAWN_INTERVAL = 2000 # 2초마다 적을 생성 (밀리초)
SPAWN_DECREMENT = 150 # 난이도 상승 시 줄어드는 시간 (밀리초)
MIN_SPAWN_INTERVAL = 500 # 최소 생성 간격
last_enemy_spawn_time = 0

NEXT_DIFFICULTY_SCORE = 500 # 다음 난이도 상승 목표 점수

# 🖼️ 이미지 로드
try:
    # 배경 이미지 (전체 화면)
    BACKGROUND_IMAGE = pygame.image.load('background.png').convert()
    BACKGROUND_IMAGE = pygame.transform.scale(BACKGROUND_IMAGE, (WIDTH, HEIGHT)) # 화면 크기에 맞게 조절
except pygame.error as e:
    print(f"Error loading background.png: {e}")
    BACKGROUND_IMAGE = None # 이미지가 없으면 None으로 설정

try:
    # 캔버스 배경 이미지
    CANVAS_BG_IMAGE = pygame.image.load('canvas_bg.png').convert()
    CANVAS_BG_IMAGE = pygame.transform.scale(CANVAS_BG_IMAGE, (WIDTH, CANVAS_HEIGHT)) # 캔버스 크기에 맞게 조절
except pygame.error as e:
    print(f"Error loading canvas_bg.png: {e}")
    CANVAS_BG_IMAGE = None # 이미지가 없으면 None으로 설정

ENEMY_IMAGE = None
try:
    # 스프라이트 시트 이미지 로드 (파일 이름을 실제 이미지 파일명으로 변경하세요!)
    sprite_sheet = pygame.image.load('enemy.png').convert_alpha() # 투명도 유지

    # 개별 프레임의 크기 계산
    # 보내주신 이미지의 크기가 800x400이고, 가로 8개, 세로 5개 프레임이 있다고 가정
    frame_width = sprite_sheet.get_width() // 8
    frame_height = sprite_sheet.get_height() // 5

    # 스프라이트 시트에서 첫 번째 프레임 (0,0) 위치의 해골 이미지를 잘라냅니다.
    # pygame.Rect(x, y, width, height)
    first_frame_rect = pygame.Rect(0, 0, frame_width, frame_height)
    ENEMY_IMAGE = sprite_sheet.subsurface(first_frame_rect).copy()

    # 적군 개체의 원하는 크기 (40x40)에 맞게 잘라낸 이미지를 다시 조절합니다.
    ENEMY_IMAGE = pygame.transform.scale(ENEMY_IMAGE, (60, 60)) 

except pygame.error as e:
    print(f"Error loading or processing skeleton_sprite_sheet.png: {e}")
    # 이미지 처리 실패 시 기본 빨간 사각형으로 대체
    ENEMY_IMAGE = None


class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # 🖼️ 적군 이미지 사용
        if ENEMY_IMAGE:
            self.image = ENEMY_IMAGE
        else:
            self.image = pygame.Surface((40, 40))
            self.image.fill(RED) # 이미지가 없으면 빨간 사각형
            
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image) 
        self.rect.x = random.randint(0, WIDTH - self.rect.width) # 이미지 너비에 따라 조정
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
        self.speed = -5  # 위로 발사
        self.max_hits = max_hits 
        self.current_hits = 0 

    def update(self):
        self.rect.y += self.speed
        if self.rect.bottom < 0:
            self.kill()

# 그룹
enemy_group = pygame.sprite.Group()
spell_group = pygame.sprite.Group()

# 적 초기 생성
for _ in range(INITIAL_ENEMY_COUNT):
    enemy_group.add(Enemy())

# 그림 그리기 변수
drawing = False
last_pos = None
player_canvas = pygame.Surface((WIDTH, CANVAS_HEIGHT), pygame.SRCALPHA)
player_canvas.fill((0,0,0,0))
path_points = [] 


running = True
while running:
    clock.tick(FPS)
    
    # 🖼️ 배경 그리기
    if BACKGROUND_IMAGE:
        screen.blit(BACKGROUND_IMAGE, (0, 0))
    else:
        screen.fill(BLACK) # 이미지가 없으면 검은색으로 채움
    
    # ⏱️ 현재 시간 갱신
    current_time = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if game_state == "RUNNING":
            # 그림 그리기 시작
            if event.type == pygame.MOUSEBUTTONDOWN and canvas_rect.collidepoint(event.pos):
                drawing = True
                canvas_y = event.pos[1] - (HEIGHT - CANVAS_HEIGHT)
                last_pos = (event.pos[0], canvas_y) 
                path_points = [last_pos] 
                
            # 그림 그리기 종료 (발사)
            if event.type == pygame.MOUSEBUTTONUP and drawing:
                drawing = False
                
                if ink > 0:
                    spell_image = player_canvas.copy()
                    
                    try:
                        bbox = spell_image.get_bounding_rect()
                    except AttributeError:
                        bbox = spell_image.get_rect()

                    if bbox and bbox.width > 1 and bbox.height > 1:
                        cropped_image = spell_image.subsurface(bbox).copy()
                        
                        # 1. 경로 길이 계산
                        total_path_length = 0
                        if len(path_points) > 1:
                            for i in range(len(path_points) - 1):
                                p1 = path_points[i]
                                p2 = path_points[i+1]
                                total_path_length += math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                        
                        # 2. 최대 충돌 횟수 (MAX_HIT) 설정
                        MAX_HIT = max(1, int(total_path_length / 100))
                        
                        # 3. ✒️ 잉크 소모량
                        ink_needed = total_path_length / 25
                        
                        if ink >= ink_needed:
                            start_pos = (bbox.x, HEIGHT - CANVAS_HEIGHT + bbox.y)
                            
                            spell = Spell(cropped_image, start_pos, max_hits=MAX_HIT)
                            spell_group.add(spell)
                            ink -= ink_needed
                        else:
                            print(f"잉크 부족! 필요한 잉크: {ink_needed:.1f}")

                player_canvas.fill((0,0,0,0))
                path_points = [] 
                
            # 그림 그리는 중
            if event.type == pygame.MOUSEMOTION and drawing:
                x, y = event.pos
                canvas_y = y - (HEIGHT - CANVAS_HEIGHT)
                if last_pos is not None:
                    new_pos = (x, canvas_y)
                    pygame.draw.line(player_canvas, BLUE, last_pos, new_pos, 5) 
                    path_points.append(new_pos) 
                last_pos = (x, canvas_y)
        
        elif game_state == "GAME_OVER":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False


    if game_state == "RUNNING":
        # 잉크 회복
        ink = min(MAX_INK, ink + 0.07)

        # 🕒 적 생성 로직 (점수 기반)
        if current_time - last_enemy_spawn_time > ENEMY_SPAWN_INTERVAL:
            enemy_group.add(Enemy())
            last_enemy_spawn_time = current_time

        # 업데이트
        spell_group.update()
        enemy_group.update()
        
        # ⚔️ 적군 통과 감지 및 게임 오버 체크
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


        # 💥 충돌 체크
        for spell in spell_group:
            hit_enemies = pygame.sprite.spritecollide(spell, enemy_group, False, pygame.sprite.collide_mask)
            
            if hit_enemies:
                enemies_to_remove = []
                
                for enemy in hit_enemies:
                    if spell.current_hits < spell.max_hits and enemy not in enemies_to_remove:
                        enemies_to_remove.append(enemy)
                        spell.current_hits += 1
                
                if enemies_to_remove:
                    for enemy in enemies_to_remove:
                        enemy.kill()
                        enemy_group.add(Enemy()) 
                        
                    # 잉크 회복량 (이전 요청대로 5로 유지)
                    ink = min(MAX_INK, ink + 2 * len(enemies_to_remove))
                    score += 10 * len(enemies_to_remove) 

            if spell.current_hits >= spell.max_hits:
                spell.kill()
                
        # 📈 점수 기반 난이도 상승 체크
        if score >= NEXT_DIFFICULTY_SCORE:
            if ENEMY_SPAWN_INTERVAL > MIN_SPAWN_INTERVAL:
                ENEMY_SPAWN_INTERVAL -= SPAWN_DECREMENT
                ENEMY_SPAWN_INTERVAL = max(MIN_SPAWN_INTERVAL, ENEMY_SPAWN_INTERVAL)
                print(f"난이도 상승!")
            
            # 다음 난이도 목표 설정
            NEXT_DIFFICULTY_SCORE += 500


        # 화면 그리기
        enemy_group.draw(screen)
        spell_group.draw(screen)
        
        # 🖼️ 캔버스 배경 그리기
        if CANVAS_BG_IMAGE:
            screen.blit(CANVAS_BG_IMAGE, canvas_rect.topleft)
        else:
            pygame.draw.rect(screen, GRAY, canvas_rect, 0) # 이미지가 없으면 회색으로 채움

        # 플레이어가 그린 그림은 캔버스 배경 위에 그려져야 함
        screen.blit(player_canvas, (0, HEIGHT - CANVAS_HEIGHT))
        pygame.draw.rect(screen, GRAY, canvas_rect, 2) # 캔버스 테두리

        # 잉크 표시
        INK_BAR_X, INK_BAR_Y = 10, 10
        INK_BAR_W, INK_BAR_H = MAX_INK * 3, 20
        pygame.draw.rect(screen, WHITE, (INK_BAR_X, INK_BAR_Y, INK_BAR_W, INK_BAR_H), 2) 
        pygame.draw.rect(screen, BLUE, (INK_BAR_X, INK_BAR_Y, ink * 3, INK_BAR_H))
        
        # 점수 및 통과 횟수 표시
        score_text = font.render(f"Score: {score}", True, WHITE)
        pass_text = font.render(f"Passes: {enemies_passed_count} / {MAX_PASSES}", True, RED)
        
        screen.blit(score_text, (WIDTH - score_text.get_width() - 10, 10))
        screen.blit(pass_text, (WIDTH - pass_text.get_width() - 10, 40))

    elif game_state == "GAME_OVER":
        # 💥 게임 오버 화면
        game_over_text = large_font.render("GAME OVER", True, RED)
        score_final_text = font.render(f"Final Score: {score}", True, WHITE)
        restart_text = font.render("Press ESC to Quit", True, GRAY)
        
        screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 2 - 50))
        screen.blit(score_final_text, (WIDTH // 2 - score_final_text.get_width() // 2, HEIGHT // 2 + 30))
        screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 70))


    pygame.display.flip()

pygame.quit()