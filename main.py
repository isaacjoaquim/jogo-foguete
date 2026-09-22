import math
import random
import sys
import struct
import array
import pygame

# -----------------------------------------------------------------------------
# Configurações do Jogo
# -----------------------------------------------------------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 850
FPS = 60

TARGET_ALTITUDE = 12000.0  # Altitude da órbita espacial em metros
INITIAL_FUEL = 100.0       # Combustível total
FUEL_CONSUMPTION_RATE = 11.5  # Consumo por segundo de propulsão contínua
THRUST_POWER = 380.0       # Força de aceleração do motor (m/s²)
GRAVITY = 115.0            # Gravidade (m/s²)
DRAG_BASE_COEFF = 0.0012   # Coeficiente de arrasto atmosférico

# -----------------------------------------------------------------------------
# Gerador de Efeitos Sonoros Sintetizados (Sem dependência de arquivos externos)
# -----------------------------------------------------------------------------
class SoundManager:
    def __init__(self):
        self.enabled = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.enabled = True
            self.sample_rate = 22050
            
            # Gera os sons sintéticos
            self.snd_pickup = self._generate_pickup_sound()
            self.snd_warning = self._generate_beep_sound(frequency=650, duration=0.15)
            self.snd_win = self._generate_win_fanfare()
            self.snd_boom = self._generate_explosion_sound()
            self.snd_engine = self._generate_engine_loop()
            self.engine_channel = None
        except Exception as e:
            print(f"Aviso: Não foi possível inicializar áudio ({e}). O jogo continuará silencioso.")

    def _create_sound_from_samples(self, samples):
        # Converte lista de floats (-1.0 a 1.0) para buffer estéreo 16-bit
        buf = bytearray()
        for s in samples:
            val = int(max(-1.0, min(1.0, s)) * 32767)
            raw = struct.pack('<h', val)
            buf.extend(raw) # Canal esquerdo
            buf.extend(raw) # Canal direito
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _generate_engine_loop(self):
        num_samples = int(self.sample_rate * 0.4)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            # Ruído marrom + oscilador grave
            noise = (random.random() * 2 - 1) * 0.4
            sub_bass = math.sin(2 * math.pi * 55 * t) * 0.45
            rumble = math.sin(2 * math.pi * 110 * t + noise) * 0.25
            samples.append(noise + sub_bass + rumble)
        return self._create_sound_from_samples(samples)

    def _generate_pickup_sound(self):
        num_samples = int(self.sample_rate * 0.25)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            # Arpeggio rápido ascendente (523Hz -> 659Hz -> 784Hz -> 1046Hz)
            env = max(0.0, 1.0 - (t / 0.25))
            freq = 523 + (t / 0.25) * 600
            val = math.sin(2 * math.pi * freq * t) * 0.4 * env
            samples.append(val)
        return self._create_sound_from_samples(samples)

    def _generate_beep_sound(self, frequency=700, duration=0.15):
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = math.sin(math.pi * (t / duration))
            val = math.sin(2 * math.pi * frequency * t) * 0.3 * env
            samples.append(val)
        return self._create_sound_from_samples(samples)

    def _generate_explosion_sound(self):
        num_samples = int(self.sample_rate * 0.6)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = max(0.0, 1.0 - (t / 0.6) ** 0.5)
            noise = (random.random() * 2 - 1) * env * 0.6
            sub = math.sin(2 * math.pi * max(30, 120 - 150 * t) * t) * env * 0.4
            samples.append(noise + sub)
        return self._create_sound_from_samples(samples)

    def _generate_win_fanfare(self):
        num_samples = int(self.sample_rate * 1.2)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = min(1.0, max(0.0, 1.2 - t))
            # Acorde brilhante
            note1 = math.sin(2 * math.pi * 523.25 * t)
            note2 = math.sin(2 * math.pi * 659.25 * t)
            note3 = math.sin(2 * math.pi * 783.99 * t)
            note4 = math.sin(2 * math.pi * 1046.50 * t)
            val = ((note1 + note2 + note3 + note4) / 4.0) * 0.45 * env
            samples.append(val)
        return self._create_sound_from_samples(samples)

    def play_engine(self, active):
        if not self.enabled:
            return
        if active:
            if self.engine_channel is None or not self.engine_channel.get_busy():
                self.engine_channel = self.snd_engine.play(loops=-1)
        else:
            if self.engine_channel is not None:
                self.engine_channel.stop()
                self.engine_channel = None

    def play_pickup(self):
        if self.enabled:
            self.snd_pickup.play()

    def play_warning(self):
        if self.enabled:
            self.snd_warning.play()

    def play_win(self):
        if self.enabled:
            self.snd_win.play()

    def play_explosion(self):
        if self.enabled:
            self.snd_boom.play()

    def stop_all(self):
        if self.enabled:
            pygame.mixer.stop()


# -----------------------------------------------------------------------------
# Partículas e Efeitos Visuais
# -----------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=4.0, shrink=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.max_life = life
        self.life = life
        self.initial_size = size
        self.size = size
        self.shrink = shrink

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.shrink and self.max_life > 0:
            pct = max(0.0, self.life / self.max_life)
            self.size = self.initial_size * pct

    def draw(self, surface, camera_y):
        if self.life <= 0:
            return
        screen_y = self.y - camera_y
        if -20 <= screen_y <= SCREEN_HEIGHT + 20:
            alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
            p_surf = pygame.Surface((int(self.size * 2 + 2), int(self.size * 2 + 2)), pygame.SRCALPHA)
            color_with_alpha = (*self.color[:3], alpha)
            pygame.draw.circle(p_surf, color_with_alpha, (int(self.size + 1), int(self.size + 1)), int(max(1, self.size)))
            surface.blit(p_surf, (self.x - self.size - 1, screen_y - self.size - 1))


class Star:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.world_y = random.uniform(-TARGET_ALTITUDE * 1.5, SCREEN_HEIGHT)
        self.size = random.uniform(1.0, 2.5)
        self.speed_factor = random.uniform(0.1, 0.4)
        self.twinkle_speed = random.uniform(2.0, 6.0)
        self.twinkle_offset = random.uniform(0, math.pi * 2)

    def draw(self, surface, camera_y, time_sec, space_alpha):
        if space_alpha <= 0.05:
            return
        screen_y = (self.world_y - camera_y * self.speed_factor) % (SCREEN_HEIGHT + 100) - 50
        twinkle = (math.sin(time_sec * self.twinkle_speed + self.twinkle_offset) + 1.0) / 2.0
        alpha = int(space_alpha * (150 + 105 * twinkle))
        c = (255, 255, 255, alpha)
        s_surf = pygame.Surface((int(self.size * 2 + 2), int(self.size * 2 + 2)), pygame.SRCALPHA)
        pygame.draw.circle(s_surf, c, (int(self.size + 1), int(self.size + 1)), int(self.size))
        surface.blit(s_surf, (self.x, screen_y))


class Cloud:
    def __init__(self, altitude):
        self.x = random.randint(-100, SCREEN_WIDTH + 100)
        self.altitude = altitude  # Altitude em metros
        self.speed_x = random.uniform(-15.0, 15.0)
        self.scale = random.uniform(0.8, 1.8)
        self.puffs = [
            (random.uniform(-40, 40) * self.scale, random.uniform(-15, 15) * self.scale, random.uniform(25, 45) * self.scale)
            for _ in range(5)
        ]

    def update(self, dt):
        self.x += self.speed_x * dt
        if self.x < -200:
            self.x = SCREEN_WIDTH + 200
        elif self.x > SCREEN_WIDTH + 200:
            self.x = -200

    def draw(self, surface, rocket_alt, rocket_screen_y):
        # Converte altitude relativa para coordenada de tela
        screen_y = rocket_screen_y + (rocket_alt - self.altitude) * 2.0
        if -100 <= screen_y <= SCREEN_HEIGHT + 100:
            c_surf = pygame.Surface((int(250 * self.scale), int(120 * self.scale)), pygame.SRCALPHA)
            cx, cy = 125 * self.scale, 60 * self.scale
            for ox, oy, r in self.puffs:
                pygame.draw.circle(c_surf, (255, 255, 255, 75), (int(cx + ox), int(cy + oy)), int(r))
                pygame.draw.circle(c_surf, (240, 248, 255, 120), (int(cx + ox), int(cy + oy - 4)), int(r * 0.85))
            surface.blit(c_surf, (self.x - cx, screen_y - cy))


# -----------------------------------------------------------------------------
# Itens Coletáveis: Cápsula de Combustível
# -----------------------------------------------------------------------------
class FuelPickup:
    def __init__(self, altitude, x=None):
        self.altitude = altitude
        self.x = random.randint(80, SCREEN_WIDTH - 80) if x is None else x
        self.radius = 18
        self.collected = False
        self.pulse = random.uniform(0, math.pi * 2)

    def update(self, dt):
        self.pulse += dt * 4.0

    def draw(self, surface, rocket_alt, rocket_screen_y):
        if self.collected:
            return
        screen_y = rocket_screen_y + (rocket_alt - self.altitude) * 2.0
        if -50 <= screen_y <= SCREEN_HEIGHT + 50:
            pulse_scale = 1.0 + 0.12 * math.sin(self.pulse)
            r = int(self.radius * pulse_scale)
            
            # Brilho externo verde/ciano
            glow_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (0, 255, 200, 50), (r * 2, r * 2), r + 8)
            pygame.draw.circle(glow_surf, (0, 230, 120, 220), (r * 2, r * 2), r)
            pygame.draw.circle(glow_surf, (255, 255, 255, 240), (r * 2, r * 2), int(r * 0.55))
            
            # Ícone de raio / gota no centro
            points = [
                (r * 2 - 3, r * 2 - 8),
                (r * 2 + 5, r * 2 - 1),
                (r * 2, r * 2),
                (r * 2 + 4, r * 2 + 8),
                (r * 2 - 4, r * 2 + 1),
                (r * 2, r * 2 - 1),
            ]
            pygame.draw.polygon(glow_surf, (20, 80, 40), points)
            
            surface.blit(glow_surf, (self.x - r * 2, screen_y - r * 2))


# -----------------------------------------------------------------------------
# Foguete do Jogador
# -----------------------------------------------------------------------------
class Rocket:
    def __init__(self, x, screen_y):
        self.x = x
        self.screen_y = screen_y
        self.altitude = 0.0        # Metros
        self.velocity_y = 0.0      # m/s
        self.velocity_x = 0.0      # m/s horizontal
        self.fuel = INITIAL_FUEL
        self.tilt_angle = 0.0      # Graus de inclinação visual (-15 a 15)
        self.width = 32
        self.height = 70
        self.is_thrusting = False
        self.max_speed_reached = 0.0
        self.has_won = False
        self.has_crashed = False
        self.has_lifted_off = False
        self.crash_reason = ""

    def update(self, dt, keys, particles, sound_manager):
        if self.has_won or self.has_crashed:
            return

        # Controle de propulsão (ESPAÇO)
        thrust_active = (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.fuel > 0

        # Controle de direção lateral (A/D ou Setas)
        steer = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            steer -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            steer += 1

        # Aceleração horizontal
        self.velocity_x += steer * 180.0 * dt
        self.velocity_x *= math.exp(-2.5 * dt)  # Amortecimento horizontal
        self.x += self.velocity_x * dt
        self.x = max(30, min(SCREEN_WIDTH - 30, self.x))

        # Inclinação visual baseada no movimento
        target_tilt = -steer * 14.0
        self.tilt_angle += (target_tilt - self.tilt_angle) * 8.0 * dt

        # Física vertical
        # Densidade do ar diminui exponencialmente com a altitude!
        air_density_ratio = max(0.02, 1.0 - (self.altitude / TARGET_ALTITUDE))
        drag_force = DRAG_BASE_COEFF * air_density_ratio * (self.velocity_y ** 2) * (1 if self.velocity_y > 0 else -1)

        # Gravidade diminui ligeiramente no topo
        current_gravity = GRAVITY * max(0.65, 1.0 - (self.altitude / (TARGET_ALTITUDE * 2.0)))

        accel_y = -current_gravity - drag_force

        if thrust_active:
            accel_y += THRUST_POWER
            self.fuel -= FUEL_CONSUMPTION_RATE * dt
            if self.fuel <= 0:
                self.fuel = 0
                thrust_active = False

        self.is_thrusting = thrust_active
        sound_manager.play_engine(thrust_active)

        # Atualiza velocidade e altitude
        self.velocity_y += accel_y * dt
        self.altitude += self.velocity_y * dt

        # Marca se o foguete já decolou do solo
        if self.altitude > 2.0:
            self.has_lifted_off = True

        if self.velocity_y > self.max_speed_reached:
            self.max_speed_reached = self.velocity_y

        # Se o foguete tocar o chão
        if self.altitude <= 0:
            self.altitude = 0
            if self.has_lifted_off:
                # O foguete encostou no chão depois de ter saído dele -> EXPLOSÃO E GAME OVER
                self.has_crashed = True
                self.crash_reason = "O foguete colidiu e explodiu ao atingir o solo!"
                sound_manager.play_engine(False)
                sound_manager.play_explosion()
                self._spawn_crash_particles(particles)
            elif self.fuel <= 0 and not thrust_active:
                self.has_crashed = True
                self.crash_reason = "Combustível esgotado na base de lançamento!"
                sound_manager.play_engine(False)
            self.velocity_y = 0.0

        # Partículas de propulsão
        if thrust_active and not self.has_crashed:
            self._spawn_thruster_particles(particles)

        # Condição de Vitória: Atingir o Espaço
        if self.altitude >= TARGET_ALTITUDE and not self.has_won:
            self.has_won = True
            self.altitude = TARGET_ALTITUDE
            sound_manager.play_engine(False)
            sound_manager.play_win()
            self._spawn_win_confetti(particles)

    def _spawn_thruster_particles(self, particles):
        # Centro inferior do foguete
        rad = math.radians(self.tilt_angle)
        offset_y = 35
        bx = self.x - math.sin(rad) * offset_y
        by = self.screen_y + math.cos(rad) * offset_y

        for _ in range(5):
            angle = math.pi / 2 + math.radians(-self.tilt_angle) + random.uniform(-0.35, 0.35)
            spd = random.uniform(120, 280)
            pvx = math.cos(angle) * spd + self.velocity_x * 0.3
            pvy = math.sin(angle) * spd
            
            # Cores de chama: do amarelo/branco brilhante ao vermelho/fumaça
            r_val = random.random()
            if r_val > 0.6:
                color = (255, 255, 200) # Núcleo branco-amarelo
                sz = random.uniform(5.0, 9.0)
            elif r_val > 0.3:
                color = (255, 140, 20)  # Laranja
                sz = random.uniform(7.0, 12.0)
            else:
                color = (240, 50, 20)   # Vermelho
                sz = random.uniform(6.0, 10.0)

            particles.append(Particle(bx, by, pvx, pvy, color, life=random.uniform(0.2, 0.45), size=sz))

        # Fumaça adicional
        if random.random() < 0.4:
            smoke_color = (180, 180, 190)
            particles.append(Particle(bx + random.uniform(-6, 6), by, random.uniform(-20, 20), random.uniform(40, 90), smoke_color, life=0.6, size= random.uniform(10, 16)))

    def _spawn_crash_particles(self, particles):
        # Núcleo denso da explosão e estilhaços de fogo
        for _ in range(120):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(40, 480)
            c = random.choice([
                (255, 60, 20), (255, 140, 20), (255, 220, 40),
                (255, 255, 200), (90, 90, 100), (180, 180, 190)
            ])
            particles.append(Particle(
                self.x, self.screen_y + 20,
                math.cos(angle) * spd, math.sin(angle) * spd,
                c, life=random.uniform(0.6, 2.0),
                size=random.uniform(6, 18)
            ))

    def _spawn_win_confetti(self, particles):
        for _ in range(120):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(80, 400)
            c = random.choice([
                (255, 215, 0), (0, 255, 255), (255, 105, 180),
                (50, 205, 50), (147, 112, 219), (255, 255, 255)
            ])
            particles.append(Particle(self.x, self.screen_y, math.cos(angle) * spd, math.sin(angle) * spd, c, life=random.uniform(1.2, 2.5), size=random.uniform(4, 9), shrink=False))

    def draw(self, surface):
        if self.has_crashed and self.altitude <= 0:
            return

        # Cria uma superfície transparente para renderizar o foguete com rotação suave
        foguete_surf = pygame.Surface((100, 120), pygame.SRCALPHA)
        cx, cy = 50, 60

        # Cores
        hull_white = (245, 247, 250)
        hull_shadow = (200, 208, 220)
        accent_red = (235, 55, 55)
        glass_blue = (70, 185, 240)
        metal_gray = (90, 95, 105)

        # 1. Aletas laterais
        # Aleta esquerda
        pygame.draw.polygon(foguete_surf, accent_red, [
            (cx - 12, cy + 12),
            (cx - 28, cy + 34),
            (cx - 12, cy + 30)
        ])
        # Aleta direita
        pygame.draw.polygon(foguete_surf, (200, 40, 40), [
            (cx + 12, cy + 12),
            (cx + 28, cy + 34),
            (cx + 12, cy + 30)
        ])

        # 2. Bocal de escape inferior
        pygame.draw.polygon(foguete_surf, metal_gray, [
            (cx - 8, cy + 28),
            (cx + 8, cy + 28),
            (cx + 11, cy + 36),
            (cx - 11, cy + 36)
        ])

        # 3. Corpo principal (Fuselagem)
        # Sombra lateral esquerda / volume 3D
        body_points = [
            (cx, cy - 35),        # Ponta
            (cx + 13, cy - 10),   # Ombro direito
            (cx + 13, cy + 28),   # Base direita
            (cx - 13, cy + 28),   # Base esquerda
            (cx - 13, cy - 10),   # Ombro esquerdo
        ]
        pygame.draw.polygon(foguete_surf, hull_white, body_points)
        
        # Sombra 3D no lado direito da fuselagem
        shadow_points = [
            (cx, cy - 35),
            (cx + 13, cy - 10),
            (cx + 13, cy + 28),
            (cx, cy + 28)
        ]
        pygame.draw.polygon(foguete_surf, hull_shadow, shadow_points)

        # Ponta cônica vermelha (Nose cone)
        nose_points = [
            (cx, cy - 35),
            (cx + 11, cy - 12),
            (cx - 11, cy - 12)
        ]
        pygame.draw.polygon(foguete_surf, accent_red, nose_points)

        # Faixa decorativa vermelha na cintura
        pygame.draw.rect(foguete_surf, accent_red, (cx - 13, cy + 8, 26, 6))

        # 4. Janela / Escotilha circular com reflexo
        pygame.draw.circle(foguete_surf, metal_gray, (cx, cy - 4), 9)
        pygame.draw.circle(foguete_surf, glass_blue, (cx, cy - 4), 7)
        # Reflexo branco na escotilha
        pygame.draw.circle(foguete_surf, (255, 255, 255, 200), (cx - 2, cy - 6), 2)

        # 5. Efeito de brilho Mach / Onda de choque se estiver em alta velocidade
        if self.velocity_y > 220 and not self.has_won:
            shock_alpha = min(160, int((self.velocity_y - 220) * 0.8))
            cone_surf = pygame.Surface((100, 120), pygame.SRCALPHA)
            shock_pts = [(cx, cy - 42), (cx + 38, cy + 30), (cx - 38, cy + 30)]
            pygame.draw.lines(cone_surf, (180, 230, 255, shock_alpha), False, [(cx - 32, cy + 25), (cx, cy - 40), (cx + 32, cy + 25)], 3)
            foguete_surf.blit(cone_surf, (0, 0))

        # Rotaciona o foguete
        rotated_surf = pygame.transform.rotate(foguete_surf, self.tilt_angle)
        rect = rotated_surf.get_rect(center=(int(self.x), int(self.screen_y)))
        surface.blit(rotated_surf, rect.topleft)


# -----------------------------------------------------------------------------
# Classe Principal do Jogo
# -----------------------------------------------------------------------------
class RocketGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Rumo ao Espaço - Rocket Odyssey")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        
        # Fontes do sistema
        self.font_title = pygame.font.SysFont("Segoe UI, Arial, Helvetica", 40, bold=True)
        self.font_sub = pygame.font.SysFont("Segoe UI, Arial, Helvetica", 22, bold=True)
        self.font_hud = pygame.font.SysFont("Segoe UI, Arial, Helvetica", 18, bold=True)
        self.font_small = pygame.font.SysFont("Segoe UI, Arial, Helvetica", 15)
        self.font_indicator = pygame.font.SysFont("Segoe UI, Arial, Helvetica", 13, bold=True)

        self.sounds = SoundManager()
        self.state = "MENU"  # "MENU", "PLAYING", "GAMEOVER", "VICTORY"
        self.stars = [Star() for _ in range(110)]
        self.anim_time = 0.0
        self.reset_game()

    def reset_game(self):
        self.rocket = Rocket(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 170)
        self.particles = []
        self.clouds = [
            Cloud(altitude=random.uniform(300, 3500))
            for _ in range(12)
        ]
        
        # Gera cápsulas de combustível ao longo do trajeto
        self.fuel_pickups = []
        current_alt = 700.0
        while current_alt < TARGET_ALTITUDE - 600.0:
            self.fuel_pickups.append(FuelPickup(altitude=current_alt))
            current_alt += random.uniform(750.0, 1200.0)

        self.game_time = 0.0
        self.low_fuel_beep_timer = 0.0
        self.sounds.play_engine(False)

    def get_sky_gradient(self, altitude_pct):
        """Calcula o gradiente do céu baseado na altitude (0.0 = Terra, 1.0 = Espaço Profundo)"""
        # Cores dos estágios:
        # 1. Chão/Troposfera: Azul claro / Azul celeste
        # 2. Estratosfera: Azul Cobalto
        # 3. Mesosfera: Roxo / Azul Noturno
        # 4. Termosfera/Espaço: Preto azulado profundo com estrelas
        palette = [
            (0.00, ((135, 206, 250), (225, 245, 255))), # Troposfera baixa
            (0.20, ((50, 130, 220), (120, 190, 245))),  # Média troposfera
            (0.45, ((20, 45, 110), (45, 95, 180))),     # Estratosfera
            (0.70, ((10, 15, 50), (25, 30, 80))),       # Mesosfera
            (1.00, ((3, 5, 15), (8, 10, 25)))           # Espaço Sideral
        ]

        # Interpolação linear entre as faixas
        for i in range(len(palette) - 1):
            p1, (top1, bot1) = palette[i]
            p2, (top2, bot2) = palette[i + 1]
            if p1 <= altitude_pct <= p2:
                factor = (altitude_pct - p1) / (p2 - p1)
                top = [int(top1[c] + (top2[c] - top1[c]) * factor) for c in range(3)]
                bot = [int(bot1[c] + (bot2[c] - bot1[c]) * factor) for c in range(3)]
                return top, bot

        return (3, 5, 15), (8, 10, 25)

    def draw_background(self, altitude):
        pct = min(1.0, max(0.0, altitude / TARGET_ALTITUDE))
        top_color, bot_color = self.get_sky_gradient(pct)

        # Gradiente vertical suave pré-computado
        bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 4):
            factor = y / SCREEN_HEIGHT
            r = int(top_color[0] + (bot_color[0] - top_color[0]) * factor)
            g = int(top_color[1] + (bot_color[1] - top_color[1]) * factor)
            b = int(top_color[2] + (bot_color[2] - top_color[2]) * factor)
            pygame.draw.rect(bg_surface, (r, g, b), (0, y, SCREEN_WIDTH, 4))

        self.screen.blit(bg_surface, (0, 0))

        # Estrelas com opacidade crescente conforme subimos
        space_alpha = min(1.0, max(0.0, (pct - 0.25) / 0.75))
        for star in self.stars:
            star.draw(self.screen, -altitude * 1.5, self.anim_time, space_alpha)

        # Planeta Terra ao fundo se estivermos no espaço
        if pct > 0.65:
            earth_alpha = int(255 * ((pct - 0.65) / 0.35))
            earth_surf = pygame.Surface((SCREEN_WIDTH, 300), pygame.SRCALPHA)
            # Arco curvado do planeta
            pygame.draw.ellipse(earth_surf, (20, 80, 160, min(240, earth_alpha)), (-200, 120, SCREEN_WIDTH + 400, 350))
            pygame.draw.ellipse(earth_surf, (70, 160, 240, min(140, earth_alpha)), (-200, 115, SCREEN_WIDTH + 400, 350), 6)
            pygame.draw.ellipse(earth_surf, (255, 255, 255, min(80, earth_alpha)), (-180, 112, SCREEN_WIDTH + 360, 350), 3)
            self.screen.blit(earth_surf, (0, SCREEN_HEIGHT - 220))

        # Nuvens
        if pct < 0.6:
            for cloud in self.clouds:
                cloud.draw(self.screen, altitude, self.rocket.screen_y)

        # Plataforma de lançamento terrestre no chão (altitude < 500m)
        if altitude < 400:
            ground_screen_y = self.rocket.screen_y + altitude * 2.0 + 35
            # Solo verde/concreto
            pygame.draw.rect(self.screen, (45, 110, 45), (0, ground_screen_y + 15, SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.draw.rect(self.screen, (90, 95, 105), (SCREEN_WIDTH // 2 - 140, ground_screen_y, 280, 20))
            # Torre de lançamento metálica
            tower_x = SCREEN_WIDTH // 2 - 80
            for ty in range(int(ground_screen_y - 120), int(ground_screen_y), 15):
                pygame.draw.line(self.screen, (160, 50, 40), (tower_x, ty), (tower_x + 25, ty + 15), 3)
                pygame.draw.line(self.screen, (160, 50, 40), (tower_x + 25, ty), (tower_x, ty + 15), 3)
            pygame.draw.line(self.screen, (180, 60, 50), (tower_x, ground_screen_y - 120), (tower_x, ground_screen_y), 4)
            pygame.draw.line(self.screen, (180, 60, 50), (tower_x + 25, ground_screen_y - 120), (tower_x + 25, ground_screen_y), 4)

    def draw_hud(self):
        # Painel Superior Translúcido
        hud_bar = pygame.Surface((SCREEN_WIDTH, 110), pygame.SRCALPHA)
        hud_bar.fill((10, 15, 25, 200))
        pygame.draw.line(hud_bar, (50, 70, 100), (0, 109), (SCREEN_WIDTH, 109), 2)
        self.screen.blit(hud_bar, (0, 0))

        # 1. Barra de Combustível (Fuel Gauge)
        fuel_pct = max(0.0, self.rocket.fuel / INITIAL_FUEL)
        fuel_w = 220
        fuel_h = 22
        fx = 25
        fy = 35

        # Borda e fundo
        pygame.draw.rect(self.screen, (30, 40, 50), (fx, fy, fuel_w, fuel_h), border_radius=6)
        
        # Cor dinâmica do combustível (Verde -> Amarelo -> Vermelho Piscante)
        if fuel_pct > 0.45:
            fuel_color = (40, 220, 100)
        elif fuel_pct > 0.20:
            fuel_color = (255, 190, 30)
        else:
            # Alerta crítico piscante
            flash = int(128 + 127 * math.sin(self.anim_time * 12.0))
            fuel_color = (255, flash, flash)

        fill_w = int((fuel_w - 4) * fuel_pct)
        if fill_w > 0:
            pygame.draw.rect(self.screen, fuel_color, (fx + 2, fy + 2, fill_w, fuel_h - 4), border_radius=4)
        pygame.draw.rect(self.screen, (120, 140, 170), (fx, fy, fuel_w, fuel_h), 2, border_radius=6)

        # Texto do Combustível
        lbl_fuel = self.font_hud.render(f"COMBUSTÍVEL: {self.rocket.fuel:4.1f}%", True, (240, 245, 255))
        self.screen.blit(lbl_fuel, (fx, fy - 22))

        # 2. Velocímetro
        vx = 290
        vy = 35
        speed_kmh = self.rocket.velocity_y * 3.6
        lbl_spd_title = self.font_hud.render("VELOCIDADE", True, (240, 245, 255))
        lbl_spd_val = self.font_sub.render(f"{speed_kmh:6.1f} km/h", True, (0, 220, 255) if self.rocket.velocity_y >= 0 else (255, 90, 90))
        self.screen.blit(lbl_spd_title, (vx, fy - 22))
        self.screen.blit(lbl_spd_val, (vx, fy - 1))

        # 3. Altitude e Barra de Progresso até o Espaço
        ax = 530
        alt_w = 240
        alt_pct = min(1.0, max(0.0, self.rocket.altitude / TARGET_ALTITUDE))
        
        lbl_alt_title = self.font_hud.render(f"ALTITUDE: {int(self.rocket.altitude)} m", True, (240, 245, 255))
        self.screen.blit(lbl_alt_title, (ax, fy - 22))

        # Barra de altitude até o espaço (12km)
        pygame.draw.rect(self.screen, (30, 40, 50), (ax, fy, alt_w, fuel_h), border_radius=6)
        alt_fill_w = int((alt_w - 4) * alt_pct)
        if alt_fill_w > 0:
            pygame.draw.rect(self.screen, (140, 70, 255), (ax + 2, fy + 2, alt_fill_w, fuel_h - 4), border_radius=4)

        # Marcadores de cápsulas de combustível na barra de altitude
        for pickup in self.fuel_pickups:
            if not pickup.collected:
                p_ratio = pickup.altitude / TARGET_ALTITUDE
                if 0.0 <= p_ratio <= 1.0:
                    px_pos = ax + 2 + int((alt_w - 4) * p_ratio)
                    pin_y = fy + fuel_h // 2
                    is_near = 0 < (pickup.altitude - self.rocket.altitude) < 600
                    pin_col = (0, 255, 220) if is_near else (60, 220, 130)
                    pin_sz = 5 if is_near else 3
                    pts = [
                        (px_pos, pin_y - pin_sz),
                        (px_pos + pin_sz, pin_y),
                        (px_pos, pin_y + pin_sz),
                        (px_pos - pin_sz, pin_y)
                    ]
                    pygame.draw.polygon(self.screen, pin_col, pts)
                    if is_near:
                        pygame.draw.polygon(self.screen, (255, 255, 255), pts, 1)

        pygame.draw.rect(self.screen, (120, 140, 170), (ax, fy, alt_w, fuel_h), 2, border_radius=6)

        # Marcador de meta
        lbl_goal = self.font_small.render(f"ESPAÇO: {int(TARGET_ALTITUDE)}m ({int(alt_pct * 100)}%)", True, (200, 215, 240))
        self.screen.blit(lbl_goal, (ax, fy + 26))

        # 4. Indicador de Camada Atmosférica Atual
        if self.rocket.altitude < 2500:
            layer_name = "Camada: Troposfera (Alta Resistência)"
            layer_col = (135, 206, 250)
        elif self.rocket.altitude < 6000:
            layer_name = "Camada: Estratosfera (Média Resistência)"
            layer_col = (70, 160, 240)
        elif self.rocket.altitude < 9500:
            layer_name = "Camada: Mesosfera (Baixa Resistência)"
            layer_col = (180, 120, 255)
        elif self.rocket.altitude < TARGET_ALTITUDE:
            layer_name = "Camada: Termosfera (Quase no Espaço!)"
            layer_col = (255, 140, 255)
        else:
            layer_name = "ÓRBITA ESPACIAL ALCANÇADA! 🚀"
            layer_col = (255, 215, 0)

        lbl_layer = self.font_small.render(layer_name, True, layer_col)
        self.screen.blit(lbl_layer, (25, 75))

        lbl_time = self.font_small.render(f"⏱️ Tempo: {self.game_time:.1f}s", True, (200, 220, 255))
        self.screen.blit(lbl_time, (ax, 75))

        # Dica rápida de controle no rodapé
        if self.rocket.altitude < 600 and self.state == "PLAYING":
            tip_surf = self.font_sub.render("🔥 SEGURE A TECLA [ ESPAÇO ] PARA ACELERAR O FOGUETE 🔥", True, (255, 230, 100))
            tip_rect = tip_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40))
            self.screen.blit(tip_surf, tip_rect)

    def draw_fuel_indicators(self):
        """Desenha indicadores direcionais e feixe laser de onde o combustível irá aparecer."""
        if self.state != "PLAYING":
            return

        for pickup in self.fuel_pickups:
            if pickup.collected:
                continue

            diff_alt = pickup.altitude - self.rocket.altitude
            screen_y = self.rocket.screen_y + (self.rocket.altitude - pickup.altitude) * 2.0

            # 1. Indicador para combustível que está acima fora da tela (ou próximo de entrar)
            if diff_alt > 0 and screen_y < 120 and diff_alt <= 750:
                badge_w = 96
                badge_h = 28
                badge_x = max(badge_w // 2 + 10, min(SCREEN_WIDTH - badge_w // 2 - 10, int(pickup.x)))
                badge_y = 125

                proximity = max(0.0, min(1.0, 1.0 - (diff_alt / 750.0)))
                pulse = (math.sin(self.anim_time * 8.0) + 1.0) / 2.0

                # Feixe vertical guia holográfico mostrando a coluna exata onde a cápsula cairá
                beam_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                beam_alpha = int(40 + 70 * proximity + 25 * pulse)
                beam_w = int(2 + 2 * proximity)
                pygame.draw.line(beam_surf, (0, 255, 180, beam_alpha), (int(pickup.x), 115), (int(pickup.x), SCREEN_HEIGHT - 100), beam_w)

                # Pontos luminosos descendo no feixe
                beam_step = 30
                for by in range(120, SCREEN_HEIGHT - 100, beam_step):
                    dot_y = (by + int(self.anim_time * 70)) % (SCREEN_HEIGHT - 220) + 120
                    pygame.draw.circle(beam_surf, (0, 255, 210, int(beam_alpha * 1.4)), (int(pickup.x), dot_y), 2)
                self.screen.blit(beam_surf, (0, 0))

                # Onda de radar ao redor do badge quando muito próximo (< 380m)
                if diff_alt < 380:
                    ripple_surf = pygame.Surface((120, 60), pygame.SRCALPHA)
                    ripple_r = int(12 + (self.anim_time * 35) % 20)
                    ripple_alpha = max(0, int(180 * (1.0 - (ripple_r - 12) / 20.0)))
                    pygame.draw.ellipse(ripple_surf, (0, 255, 180, ripple_alpha), (60 - ripple_r * 2, 30 - ripple_r, ripple_r * 4, ripple_r * 2), 2)
                    self.screen.blit(ripple_surf, (badge_x - 60, badge_y - 30))

                # Superfície do Badge (Pill)
                badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
                pygame.draw.rect(badge_surf, (10, 26, 22, 225), (0, 0, badge_w, badge_h), border_radius=14)
                border_col = (
                    int(0 + 40 * pulse),
                    int(230 + 25 * pulse),
                    int(170 + 40 * pulse)
                )
                pygame.draw.rect(badge_surf, border_col, (0, 0, badge_w, badge_h), 2, border_radius=14)

                # Seta animada para cima ▲
                arrow_y_off = int(math.sin(self.anim_time * 10.0) * 2.5)
                arrow_pts = [
                    (14, 8 + arrow_y_off),
                    (20, 16 + arrow_y_off),
                    (8, 16 + arrow_y_off)
                ]
                pygame.draw.polygon(badge_surf, (0, 255, 200), arrow_pts)

                # Mini ícone de cápsula de combustível
                pygame.draw.circle(badge_surf, (0, 230, 130), (32, 14), 5)
                pygame.draw.circle(badge_surf, (255, 255, 255), (32, 14), 2)

                # Distância em metros
                dist_txt = f"{int(diff_alt)}m"
                lbl_dist = self.font_indicator.render(dist_txt, True, (240, 255, 245))
                badge_surf.blit(lbl_dist, (42, 6))

                self.screen.blit(badge_surf, (badge_x - badge_w // 2, badge_y))

            # 2. Indicador para combustível deixado para trás durante descida/queda
            elif diff_alt < 0 and screen_y > SCREEN_HEIGHT + 10 and abs(diff_alt) <= 450:
                badge_w = 96
                badge_h = 28
                badge_x = max(badge_w // 2 + 10, min(SCREEN_WIDTH - badge_w // 2 - 10, int(pickup.x)))
                badge_y = SCREEN_HEIGHT - 45

                badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
                pygame.draw.rect(badge_surf, (28, 20, 10, 225), (0, 0, badge_w, badge_h), border_radius=14)
                pygame.draw.rect(badge_surf, (255, 180, 40), (0, 0, badge_w, badge_h), 2, border_radius=14)

                # Seta animada para baixo ▼
                arrow_y_off = int(math.sin(self.anim_time * 10.0) * 2.5)
                arrow_pts = [
                    (14, 18 + arrow_y_off),
                    (20, 10 + arrow_y_off),
                    (8, 10 + arrow_y_off)
                ]
                pygame.draw.polygon(badge_surf, (255, 200, 40), arrow_pts)
                pygame.draw.circle(badge_surf, (255, 180, 40), (32, 14), 5)

                dist_txt = f"{int(abs(diff_alt))}m"
                lbl_dist = self.font_indicator.render(dist_txt, True, (255, 245, 220))
                badge_surf.blit(lbl_dist, (42, 6))

                self.screen.blit(badge_surf, (badge_x - badge_w // 2, badge_y))

    def draw_menu(self):
        # Fundo do menu
        self.draw_background(0)

        # Caixa translúcida de boas-vindas
        box = pygame.Surface((620, 480), pygame.SRCALPHA)
        box.fill((12, 18, 32, 230))
        pygame.draw.rect(box, (70, 130, 200), (0, 0, 620, 480), 2, border_radius=16)
        bx = (SCREEN_WIDTH - 620) // 2
        by = (SCREEN_HEIGHT - 480) // 2 - 20
        self.screen.blit(box, (bx, by))

        # Título
        title_surf = self.font_title.render("🚀 RUMO AO ESPAÇO", True, (255, 215, 60))
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, by + 50))
        self.screen.blit(title_surf, title_rect)

        sub_surf = self.font_sub.render("Simulador de Lançamento de Foguete", True, (180, 220, 255))
        sub_rect = sub_surf.get_rect(center=(SCREEN_WIDTH // 2, by + 95))
        self.screen.blit(sub_surf, sub_rect)

        # Instruções
        instructions = [
            ("Objetivo:", "Chegue a 12.000 metros de altitude para entrar em órbita."),
            ("Controle Principal:", "Segure [ ESPAÇO ] para ligar os motores e ganhar altitude."),
            ("Combustível:", "O propulsor consome combustível limitado. Não gaste tudo de uma vez!"),
            ("Itens Coletáveis:", "Siga o radar verde no topo e o feixe guia para coletar combustível."),
            ("Direção:", "Use [ A / D ] ou [ Setas ] para manobrar lateralmente."),
            ("Perigo de Queda:", "Se o foguete cair e tocar o chão após decolar, ele explodirá!")
        ]

        start_y = by + 145
        for header, desc in instructions:
            h_surf = self.font_hud.render(header, True, (0, 255, 200))
            self.screen.blit(h_surf, (bx + 40, start_y))
            d_surf = self.font_small.render(desc, True, (220, 230, 245))
            self.screen.blit(d_surf, (bx + 40, start_y + 22))
            start_y += 45

        # Botão pulsar para iniciar
        pulse = (math.sin(pygame.time.get_ticks() * 0.006) + 1.0) / 2.0
        btn_color = (int(255 * (0.8 + 0.2 * pulse)), int(180 * (0.8 + 0.2 * pulse)), 40)
        start_prompt = self.font_sub.render("▶ PRESSIONE [ ESPAÇO ] PARA DECOLAR ◀", True, btn_color)
        prompt_rect = start_prompt.get_rect(center=(SCREEN_WIDTH // 2, by + 440))
        self.screen.blit(start_prompt, prompt_rect)

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((20, 5, 5, 210))
        self.screen.blit(overlay, (0, 0))

        # Painel central
        panel = pygame.Surface((560, 360), pygame.SRCALPHA)
        panel.fill((30, 15, 18, 240))
        pygame.draw.rect(panel, (240, 70, 70), (0, 0, 560, 360), 3, border_radius=16)
        px = (SCREEN_WIDTH - 560) // 2
        py = (SCREEN_HEIGHT - 360) // 2
        self.screen.blit(panel, (px, py))

        # Título de Falha
        title = self.font_title.render("💥 MISSÃO FALHOU", True, (255, 75, 75))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, py + 50)))

        reason = self.rocket.crash_reason if self.rocket.crash_reason else "O combustível acabou antes de alcançar o espaço!"
        r_surf = self.font_hud.render(reason, True, (255, 190, 190))
        self.screen.blit(r_surf, r_surf.get_rect(center=(SCREEN_WIDTH // 2, py + 105)))

        # Estatísticas
        max_alt = int(self.rocket.altitude if self.rocket.altitude > 0 else self.rocket.max_speed_reached * 12)
        stat1 = self.font_hud.render(f"Altitude Máxima: {max_alt} m / {int(TARGET_ALTITUDE)} m", True, (230, 235, 245))
        stat2 = self.font_hud.render(f"Velocidade Máxima: {self.rocket.max_speed_reached * 3.6:.1f} km/h", True, (230, 235, 245))
        self.screen.blit(stat1, (px + 60, py + 160))
        self.screen.blit(stat2, (px + 60, py + 195))

        dica = self.font_small.render("Dica: Pegue as cápsulas verdes brilhantes no céu para recuperar combustível!", True, (120, 240, 180))
        self.screen.blit(dica, dica.get_rect(center=(SCREEN_WIDTH // 2, py + 250)))

        # Reiniciar
        retry = self.font_sub.render("Pressione [ R ] ou [ ESPAÇO ] para Tentar Novamente", True, (255, 220, 80))
        self.screen.blit(retry, retry.get_rect(center=(SCREEN_WIDTH // 2, py + 310)))

    def draw_victory(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 15, 30, 190))
        self.screen.blit(overlay, (0, 0))

        # Painel central
        panel = pygame.Surface((580, 400), pygame.SRCALPHA)
        panel.fill((12, 28, 52, 240))
        pygame.draw.rect(panel, (255, 215, 0), (0, 0, 580, 400), 3, border_radius=16)
        px = (SCREEN_WIDTH - 580) // 2
        py = (SCREEN_HEIGHT - 400) // 2
        self.screen.blit(panel, (px, py))

        title = self.font_title.render("🎉 MISSÃO CUMPRIDA! 🎉", True, (255, 225, 40))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, py + 50)))

        sub = self.font_sub.render("Você alcançou a órbita espacial com sucesso!", True, (140, 230, 255))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, py + 95)))

        # Estatísticas da missão
        s1 = self.font_hud.render(f"⏱️ Tempo de Voo: {self.game_time:.1f} segundos", True, (235, 245, 255))
        s2 = self.font_hud.render(f"⛽ Combustível Restante: {self.rocket.fuel:.1f}%", True, (80, 255, 160))
        s3 = self.font_hud.render(f"⚡ Velocidade Recorde: {self.rocket.max_speed_reached * 3.6:.1f} km/h", True, (255, 180, 50))
        s4 = self.font_hud.render(f"🌌 Altitude Final: {int(self.rocket.altitude)} metros", True, (200, 160, 255))

        self.screen.blit(s1, (px + 60, py + 145))
        self.screen.blit(s2, (px + 60, py + 180))
        self.screen.blit(s3, (px + 60, py + 215))
        self.screen.blit(s4, (px + 60, py + 250))

        retry = self.font_sub.render("Pressione [ R ] ou [ ESPAÇO ] para Jogar Novamente", True, (255, 220, 80))
        self.screen.blit(retry, retry.get_rect(center=(SCREEN_WIDTH // 2, py + 345)))

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # Previne saltos caso ocorra lag
            self.anim_time += dt

            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif self.state == "MENU":
                        if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                            self.state = "PLAYING"
                    elif self.state in ["GAMEOVER", "VICTORY"]:
                        if event.key == pygame.K_r or event.key == pygame.K_SPACE:
                            self.reset_game()
                            self.state = "PLAYING"

            keys = pygame.key.get_pressed()

            # Atualiza partículas em qualquer estado (efeito contínuo de vitória/derrota)
            for p in self.particles:
                p.update(dt)
            self.particles = [p for p in self.particles if p.life > 0]

            # Lógica dos estados
            if self.state == "PLAYING":
                self.game_time += dt

                # Atualiza nuvens
                for cloud in self.clouds:
                    cloud.update(dt)

                # Atualiza itens coletáveis
                for pickup in self.fuel_pickups:
                    pickup.update(dt)
                    if not pickup.collected:
                        # Distância até o foguete
                        screen_y = self.rocket.screen_y + (self.rocket.altitude - pickup.altitude) * 2.0
                        dx = self.rocket.x - pickup.x
                        dy = self.rocket.y_pos = self.rocket.screen_y - screen_y
                        dist = math.hypot(dx, dy)
                        if dist < pickup.radius + 25:
                            pickup.collected = True
                            self.rocket.fuel = min(INITIAL_FUEL, self.rocket.fuel + 30.0)
                            self.sounds.play_pickup()
                            # Partículas de coleta
                            for _ in range(25):
                                ang = random.uniform(0, math.pi * 2)
                                spd = random.uniform(40, 180)
                                self.particles.append(Particle(pickup.x, screen_y, math.cos(ang) * spd, math.sin(ang) * spd, (0, 255, 180), life=0.5, size=5.0))

                # Atualiza foguete
                self.rocket.update(dt, keys, self.particles, self.sounds)

                # Alerta sonoro de combustível baixo
                if 0 < self.rocket.fuel <= 20.0 and self.rocket.is_thrusting:
                    self.low_fuel_beep_timer -= dt
                    if self.low_fuel_beep_timer <= 0:
                        self.sounds.play_warning()
                        self.low_fuel_beep_timer = 0.45

                # Checa transição para Game Over ou Vitória
                if self.rocket.has_won:
                    self.state = "VICTORY"
                elif self.rocket.has_crashed:
                    self.state = "GAMEOVER"

            # Desenho da Cena
            self.draw_background(self.rocket.altitude if self.state != "MENU" else 0)

            # Desenha cápsulas de combustível
            if self.state in ["PLAYING", "VICTORY", "GAMEOVER"]:
                for pickup in self.fuel_pickups:
                    pickup.draw(self.screen, self.rocket.altitude, self.rocket.screen_y)

            # Desenha partículas
            for p in self.particles:
                p.draw(self.screen, 0)

            # Desenha foguete, indicadores e HUD
            if self.state in ["PLAYING", "VICTORY", "GAMEOVER"]:
                self.rocket.draw(self.screen)
                self.draw_fuel_indicators()
                self.draw_hud()

            # Telas de Estado
            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "GAMEOVER":
                self.draw_game_over()
            elif self.state == "VICTORY":
                # Partículas contínuas de celebração
                if random.random() < 0.25:
                    self.rocket._spawn_win_confetti(self.particles)
                self.draw_victory()

            pygame.display.flip()

        self.sounds.stop_all()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = RocketGame()
    game.run()
