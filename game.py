import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import cv2
import mediapipe as mp
from mediapipe.python.solutions import drawing_utils  # Fixed import for 0.10.x
import pygame
import sys

# ----------------- MediaPipe Setup -----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = drawing_utils  # Use the correct drawing utils

# ----------------- Pygame Setup -----------------
pygame.init()
WIDTH, HEIGHT = 1200, 600
GAME_WIDTH, CAM_WIDTH = 800, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Hand-Controlled Brick Breaker")

# Colors
WHITE, BLACK, RED, GREEN, BLUE = (255,255,255), (0,0,0), (255,0,0), (0,255,0), (0,0,255)
BUTTON_COLOR, BUTTON_HOVER_COLOR = (50,150,250), (100,200,255)

# Paddle
paddle_width, paddle_height = 150, 20
paddle_x = GAME_WIDTH//2 - paddle_width//2
paddle_y = HEIGHT - 30
paddle_color = BLUE

# Ball
ball_radius = 10
ball_x, ball_y = GAME_WIDTH//2, HEIGHT//2
ball_speed_x, ball_speed_y = 4, -4
ball_color = RED
ball_speed_increment = 0.5

# Bricks
brick_width = GAME_WIDTH // 10
brick_height = 30

# Levels
current_level = 1
max_levels = 5

# Frame rate
clock = pygame.time.Clock()

# Webcam
cap = cv2.VideoCapture(0)

# Game state
is_game_running = False

# ----------------- Helper Functions -----------------
def create_bricks(rows):
    return [[1]*10 for _ in range(rows)]

def map_coordinates(x, y, cap_w, cap_h, screen_w, screen_h):
    mapped_x = int(x / cap_w * screen_w)
    mapped_y = int(y / cap_h * screen_h)
    return mapped_x, mapped_y

def draw_bricks(bricks):
    for row in range(len(bricks)):
        for col in range(len(bricks[row])):
            if bricks[row][col]:
                brick_x = col*brick_width
                brick_y = row*brick_height
                pygame.draw.rect(screen, GREEN, (brick_x, brick_y, brick_width, brick_height))
                pygame.draw.rect(screen, BLACK, (brick_x, brick_y, brick_width, brick_height), 2)

def reset_ball_and_paddle():
    global ball_x, ball_y, ball_speed_x, ball_speed_y, paddle_x
    ball_x, ball_y = GAME_WIDTH//2, HEIGHT//2
    ball_speed_x, ball_speed_y = 4, -4
    paddle_x = GAME_WIDTH//2 - paddle_width//2

def draw_score(score):
    font = pygame.font.SysFont("Arial", 45)
    text = font.render(f"Score: {score}", True, BLACK)
    screen.blit(text, (GAME_WIDTH+8, 15))

def draw_menu():
    screen.fill(WHITE)
    font = pygame.font.SysFont("Arial", 48)
    start_text = font.render("START GAME", True, WHITE)
    exit_text = font.render("EXIT", True, WHITE)

    start_rect = pygame.Rect(WIDTH//2-150, HEIGHT//2-50, 300, 70)
    exit_rect = pygame.Rect(WIDTH//2-150, HEIGHT//2+50, 300, 70)
    mouse_pos = pygame.mouse.get_pos()

    start_color = BUTTON_HOVER_COLOR if start_rect.collidepoint(mouse_pos) else BUTTON_COLOR
    exit_color = BUTTON_HOVER_COLOR if exit_rect.collidepoint(mouse_pos) else BUTTON_COLOR

    pygame.draw.rect(screen, start_color, start_rect, border_radius=10)
    pygame.draw.rect(screen, exit_color, exit_rect, border_radius=10)
    screen.blit(start_text, (start_rect.x+50, start_rect.y+10))
    screen.blit(exit_text, (exit_rect.x+115, exit_rect.y+10))
    pygame.display.flip()
    return start_rect, exit_rect

# ----------------- Main Game Loop -----------------
def game_loop():
    global ball_x, ball_y, ball_speed_x, ball_speed_y, paddle_x, current_level

    score = 0
    last_score_increment = -1  # Prevent multiple increments

    while current_level <= max_levels:
        bricks = create_bricks(current_level+2)
        reset_ball_and_paddle()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    cleanup()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            # --- Webcam Frame & Hand Detection ---
            ret, frame = cap.read()
            if not ret: break
            frame = cv2.flip(frame,1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb_frame)

            if result.multi_hand_landmarks:
                hand_landmarks = result.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                index_tip = hand_landmarks.landmark[8]
                h, w, _ = frame.shape
                finger_x, finger_y = int(index_tip.x*w), int(index_tip.y*h)
                mapped_x, _ = map_coordinates(finger_x, finger_y, w, h, GAME_WIDTH, HEIGHT)
                # Smooth paddle movement
                paddle_x += (mapped_x - paddle_x) * 0.2
            # Keep paddle within bounds
            paddle_x = max(0, min(GAME_WIDTH-paddle_width, paddle_x))

            # --- Draw webcam feed ---
            resized_frame = cv2.resize(frame, (CAM_WIDTH, HEIGHT))
            frame_surface = pygame.surfarray.make_surface(cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB))
            frame_surface = pygame.transform.rotate(frame_surface, -90)
            screen.blit(frame_surface, (GAME_WIDTH,0))

            # --- Clear Game Section ---
            pygame.draw.rect(screen, WHITE, (0,0,GAME_WIDTH,HEIGHT))

            # --- Draw Paddle ---
            pygame.draw.rect(screen, paddle_color, (paddle_x, paddle_y, paddle_width, paddle_height))

            # --- Move Ball ---
            ball_x += ball_speed_x
            ball_y += ball_speed_y

            # Wall collisions
            if ball_x-ball_radius <0 or ball_x+ball_radius>GAME_WIDTH: ball_speed_x*=-1
            if ball_y-ball_radius<0: ball_speed_y*=-1

            # Paddle collision
            if paddle_y < ball_y+ball_radius < paddle_y+paddle_height and paddle_x < ball_x < paddle_x+paddle_width:
                ball_speed_y*=-1
                score += 1

            # Brick collision
            brick_hit = False
            for row in range(len(bricks)):
                for col in range(len(bricks[row])):
                    if bricks[row][col]:
                        bx = col*brick_width
                        by = row*brick_height
                        if bx<ball_x<bx+brick_width and by<ball_y-ball_radius<by+brick_height:
                            bricks[row][col]=0
                            ball_speed_y*=-1
                            brick_hit=True
                            score+=5
                            break
                if brick_hit: break

            # Draw ball
            pygame.draw.circle(screen, ball_color, (ball_x, ball_y), ball_radius)

            # Draw bricks
            draw_bricks(bricks)

            # Draw score
            draw_score(score)

            # Increase ball speed safely
            if score >=10 and score//10 > last_score_increment:
                ball_speed_x += ball_speed_increment
                ball_speed_y += ball_speed_increment
                last_score_increment = score//10

            # Level up
            if all(brick==0 for row in bricks for brick in row):
                current_level += 1
                if current_level<=max_levels:
                    ball_speed_x += ball_speed_increment
                    ball_speed_y += ball_speed_increment
                break

            # Game over
            if ball_y > HEIGHT:
                return

            pygame.display.flip()
            clock.tick(60)

# ----------------- Cleanup -----------------
def cleanup():
    hands.close()
    cap.release()
    pygame.quit()
    sys.exit()

# ----------------- Main Program -----------------
while True:
    start_button, exit_button = draw_menu()
    while not is_game_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cleanup()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx,my = event.pos
                if start_button.collidepoint(mx,my):
                    is_game_running = True
                elif exit_button.collidepoint(mx,my):
                    cleanup()
    game_loop()
    is_game_running=False
    current_level=1
