import pygame
import numpy as np

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

WIDTH, HEIGHT = 300, 150
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Hold Button to Play Sine Wave with Fade-In")

font = pygame.font.SysFont(None, 36)
button_rect = pygame.Rect(100, 50, 100, 50)

sample_rate = 44100
frequency = 440
fade_in_duration = 0.5  # seconds
total_duration = 5.0    # seconds total buffer length

# Generate time array
t = np.linspace(0, total_duration, int(sample_rate * total_duration), False)

# Generate sine wave
wave = 0.5 * np.sin(2 * np.pi * frequency * t)

# Create fade-in envelope
fade_in_samples = int(sample_rate * fade_in_duration)
fade_in_envelope = np.linspace(0, 1, fade_in_samples)

# Apply fade-in to the start of the wave
wave[:fade_in_samples] *= fade_in_envelope

# Convert to 16-bit signed integers for pygame
audio = np.int16(wave * 32767)

# Make pygame sound object
sound = pygame.sndarray.make_sound(audio)

channel = pygame.mixer.Channel(0)

playing = False
running = True
clock = pygame.time.Clock()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if button_rect.collidepoint(event.pos) and not playing:
                channel.play(sound, loops=-1)
                playing = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if playing:
                channel.stop()
                playing = False

    # Also handle if mouse is dragged off button while pressed:
    if pygame.mouse.get_pressed()[0]:
        if button_rect.collidepoint(pygame.mouse.get_pos()):
            if not playing:
                channel.play(sound, loops=-1)
                playing = True
        else:
            if playing:
                channel.stop()
                playing = False
    else:
        if playing:
            channel.stop()
            playing = False

    screen.fill((30, 30, 30))
    color = (0, 200, 0) if playing else (100, 100, 100)
    pygame.draw.rect(screen, color, button_rect)
    text = font.render("Hold", True, (255, 255, 255))
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
