import math
import random
import sys
import struct
import pygame


# =============================================================================
# CONFIGURAÇÕES E MODOS DE JOGO
# =============================================================================
FPS = 60
DT = 1.0 / 60.0  # Δt = 1/60 s fixo (requisito)

# Constantes físicas fundamentais
GRAVITY = 9.8                               # g = 9,8 m/s²
ROCKET_DRY_MASS = 100_000.0                # Massa do foguete: 100 ton = 100.000 kg
FUEL_TOTAL_MASS = 100_000.0                # Massa do combustível: 100 ton = 100.000 kg
MAX_ANGLE = 30.0                            # ±30° com a vertical
INITIAL_ALTITUDE = 800.0                    # Começa já no ar (requisito)

# Parâmetros padrão legados (requisitos estritos da atividade)
THRUST_FORCE = 2_000_000.0                 # Força: 2 × 10⁶ N
FUEL_PER_FRAME = 0.001 * FUEL_TOTAL_MASS   # 0,1% do combustível total/frame = 100 kg

# -----------------------------------------------------------------------------
# Dicionário de Modos de Jogo
# -----------------------------------------------------------------------------
GAME_MODES = {
    "ACADEMICO": {
        "id": "ACADEMICO",
        "title": "Modo 1: Acadêmico",
        "subtitle": "Requisitos Estritos da Atividade",
        "thrust": 2_000_000.0,              # Força original da atividade: 2.0 MN
        "fuel_per_frame": 0.001 * FUEL_TOTAL_MASS,  # 100 kg por frame
        "rotation_speed": 0.0,              # Salto instantâneo para ±30° (original)
        "tag": "F = 2.0 MN  |  TWR = 1.02  |  Ângulo Fixo ±30°",
        "badge_color": (255, 150, 50),
        "desc_short": "Fiel ao enunciado da atividade. Aceleração inicial de apenas 0,2 m/s². Cai ao inclinar 30°.",
    },
    "AEROESPACIAL": {
        "id": "AEROESPACIAL",
        "title": "Modo 2: Aeroespacial",
        "subtitle": "Opção 1 — Realista & Jogável",
        "thrust": 2_800_000.0,              # Empuxo de engenharia aeroespacial: 2.8 MN (TWR 1.43, estilo Falcon 9)
        "fuel_per_frame": 0.001 * FUEL_TOTAL_MASS,  # 100 kg por frame
        "rotation_speed": 55.0,             # Rotação suave contínua (55°/s) com vetorização (gimbal)
        "tag": "F = 2.8 MN  |  TWR = 1.43  |  Gimbal Suave (55°/s)",
        "badge_color": (40, 225, 160),
        "desc_short": "Padrão de foguetes reais (Falcon 9). Decolagem potente (4,2 m/s²) e curvas com sustentação.",
    }
}



# =============================================================================
# Gerenciador de Sons Sintetizados (sem arquivos externos)
# =============================================================================
class SoundManager:
    def __init__(self):
        self.enabled = False
        self.muted = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            self.enabled = True
            self.sample_rate = 22050
            self.snd_boom = self._generate_explosion()
            self.snd_engine = self._generate_engine_loop()
            self.snd_engine.set_volume(0.12)   # Volume baixo e confortável
            self.snd_boom.set_volume(0.25)
            self.engine_channel = None
        except Exception as e:
            print(f"Aviso: áudio desabilitado ({e})")

    def _make_sound(self, samples):
        buf = bytearray()
        for s in samples:
            val = int(max(-1.0, min(1.0, s)) * 32767)
            raw = struct.pack('<h', val)
            buf.extend(raw)
            buf.extend(raw)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _generate_engine_loop(self):
        """Gera um som de motor grave, suave e contínuo, sem chiados agudos ou estalos."""
        n = int(self.sample_rate * 1.0)
        # Ruído browniano suave (filtra frequências agudas)
        val = 0.0
        raw = []
        for _ in range(n):
            val = (val + (random.random() * 2.0 - 1.0) * 0.06) * 0.95
            raw.append(val)

        # Média móvel para suavizar transições
        win = 16
        acc = sum(raw[:win])
        smooth = []
        for i in range(n):
            acc += raw[(i + win) % n] - raw[i]
            smooth.append(acc / win)

        samples = []
        for i in range(n):
            t = i / self.sample_rate
            # Graves suaves harmônicos (45 Hz e 90 Hz)
            sub = math.sin(2 * math.pi * 45 * t) * 0.35
            hum = math.sin(2 * math.pi * 90 * t) * 0.15
            rumble = smooth[i] * 0.4
            
            # Envelope suave nas pontas para evitar cliques no loop
            edge = min(1.0, i / 300.0, (n - 1 - i) / 300.0)
            samples.append((sub + hum + rumble) * edge * 0.3)
        return self._make_sound(samples)

    def _generate_explosion(self):
        n = int(self.sample_rate * 0.7)
        samples = []
        for i in range(n):
            t = i / self.sample_rate
            env = max(0.0, 1.0 - (t / 0.7) ** 0.5)
            noise = (random.random() * 2 - 1) * env * 0.3
            sub = math.sin(2 * math.pi * max(25, 90 - 120 * t) * t) * env * 0.35
            samples.append((noise + sub) * 0.4)
        return self._make_sound(samples)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.stop_all()
        return self.muted

    def play_engine(self, active):
        if not self.enabled or self.muted:
            if self.engine_channel is not None:
                self.engine_channel.stop()
                self.engine_channel = None
            return
        if active:
            if self.engine_channel is None or not self.engine_channel.get_busy():
                self.engine_channel = self.snd_engine.play(loops=-1)
        else:
            if self.engine_channel is not None:
                self.engine_channel.stop()
                self.engine_channel = None

    def play_explosion(self):
        if self.enabled and not self.muted:
            self.snd_boom.play()

    def stop_all(self):
        if self.enabled:
            pygame.mixer.stop()
            self.engine_channel = None


# =============================================================================
# Partícula — coordenadas do mundo (metros)
# =============================================================================
class Particle:
    def __init__(self, wx, wy, vx, vy, color, life, size=4.0, shrink=True):
        self.wx = wx
        self.wy = wy
        self.vx = vx
        self.vy = vy
        self.color = color
        self.max_life = life
        self.life = life
        self.initial_size = size
        self.size = size
        self.shrink = shrink

    def update(self, dt):
        self.wx += self.vx * dt
        self.wy += self.vy * dt
        self.life -= dt
        if self.shrink and self.max_life > 0:
            self.size = self.initial_size * max(0.0, self.life / self.max_life)

    def draw(self, surface, cam_x, cam_y, sw, sh):
        if self.life <= 0:
            return
        sx = (self.wx - cam_x) + sw / 2
        sy = sh / 2 - (self.wy - cam_y)
        if -20 <= sx <= sw + 20 and -20 <= sy <= sh + 20:
            alpha = max(0, min(255, int(255 * self.life / self.max_life)))
            s = int(max(1, self.size))
            p_surf = pygame.Surface((s * 2 + 2, s * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (*self.color[:3], alpha), (s + 1, s + 1), s)
            surface.blit(p_surf, (sx - s - 1, sy - s - 1))


# =============================================================================
# Estrela — paralaxe de tela
# =============================================================================
class Star:
    def __init__(self, sw, sh):
        self.x = random.randint(0, sw)
        self.base_y = random.uniform(-2000, sh)
        self.size = random.uniform(1.0, 2.5)
        self.speed_factor = random.uniform(0.1, 0.4)
        self.twinkle_speed = random.uniform(2.0, 6.0)
        self.twinkle_offset = random.uniform(0, math.pi * 2)

    def draw(self, surface, scroll, time_sec, space_alpha, sh):
        if space_alpha <= 0.05:
            return
        screen_y = (self.base_y - scroll * self.speed_factor) % (sh + 100) - 50
        twinkle = (math.sin(time_sec * self.twinkle_speed + self.twinkle_offset) + 1) / 2
        alpha = int(space_alpha * (150 + 105 * twinkle))
        s_surf = pygame.Surface((int(self.size * 2 + 2), int(self.size * 2 + 2)), pygame.SRCALPHA)
        pygame.draw.circle(s_surf, (255, 255, 255, alpha),
                           (int(self.size + 1), int(self.size + 1)), int(self.size))
        surface.blit(s_surf, (self.x, screen_y))


# =============================================================================
# Nuvem — coordenadas do mundo
# =============================================================================
class Cloud:
    def __init__(self, alt):
        self.wx = random.uniform(-800, 800)
        self.altitude = alt
        self.speed_x = random.uniform(-15, 15)
        self.scale = random.uniform(0.8, 1.8)
        self.puffs = [
            (random.uniform(-40, 40) * self.scale,
             random.uniform(-15, 15) * self.scale,
             random.uniform(25, 45) * self.scale)
            for _ in range(5)
        ]

    def update(self, dt):
        self.wx += self.speed_x * dt

    def draw(self, surface, cam_x, cam_y, sw, sh):
        sx = (self.wx - cam_x) + sw / 2
        sy = sh / 2 - (self.altitude - cam_y)
        if -250 <= sx <= sw + 250 and -100 <= sy <= sh + 100:
            w = int(250 * self.scale)
            h = int(120 * self.scale)
            c_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            cx_c, cy_c = w // 2, h // 2
            for ox, oy, r in self.puffs:
                pygame.draw.circle(c_surf, (255, 255, 255, 75),
                                   (int(cx_c + ox), int(cy_c + oy)), int(r))
                pygame.draw.circle(c_surf, (240, 248, 255, 120),
                                   (int(cx_c + ox), int(cy_c + oy - 4)), int(r * 0.85))
            surface.blit(c_surf, (sx - cx_c, sy - cy_c))


# =============================================================================
# Foguete — Física correta conforme todos os requisitos
#
# Equações implementadas:
#   massa_total = massa_foguete + massa_combustível
#   a = F/m - g  (segunda lei de Newton)
#   Fx = F · sin(θ) / m       (componente horizontal)
#   Fy = F · cos(θ) / m - g   (componente vertical)
#   v += a · Δt
#   pos += v · Δt
# =============================================================================
class Rocket:
    def __init__(self, mode="ACADEMICO"):
        self.mode = mode
        cfg = GAME_MODES.get(mode, GAME_MODES["ACADEMICO"])
        self.thrust_force = cfg["thrust"]
        self.fuel_per_frame = cfg["fuel_per_frame"]
        self.rotation_speed = cfg["rotation_speed"]

        self.x = 0.0                        # posição horizontal (m)
        self.y = INITIAL_ALTITUDE           # altitude (m) — começa no ar
        self.vx = 0.0                       # velocidade horizontal (m/s)
        self.vy = 0.0                       # velocidade vertical (m/s)
        self.fuel_mass = FUEL_TOTAL_MASS    # massa de combustível restante (kg)
        self.angle = 0.0                    # ângulo do nariz em graus (+ = direita)
        self.is_thrusting = False
        self.alive = True

    @property
    def total_mass(self):
        """Massa total = massa seca do foguete + massa do combustível restante."""
        return ROCKET_DRY_MASS + self.fuel_mass

    @property
    def twr(self):
        """Razão Empuxo / Peso (TWR) atual com o motor ligado."""
        weight = self.total_mass * GRAVITY
        return (self.thrust_force / weight) if weight > 0 else 0.0

    def update(self, keys, particles, sound_manager):
        if not self.alive:
            return

        # -----------------------------------------------------------------
        # 1. Controle de ângulo (Setas ou A/D)
        # -----------------------------------------------------------------
        left_pressed = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right_pressed = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        if left_pressed and not right_pressed:
            target_angle = -MAX_ANGLE      # nariz para a esquerda (-30°)
        elif right_pressed and not left_pressed:
            target_angle = MAX_ANGLE       # nariz para a direita (+30°)
        else:
            target_angle = 0.0             # alinhado para cima (0°)

        if self.rotation_speed <= 0.0:
            # Modo 1 (Acadêmico): salto instantâneo conforme código original
            self.angle = target_angle
        else:
            # Modo 2 (Aeroespacial): rotação gradual realista (gimbal contínuo)
            max_step = self.rotation_speed * DT
            diff = target_angle - self.angle
            if abs(diff) <= max_step:
                self.angle = target_angle
            else:
                self.angle += math.copysign(max_step, diff)

        # -----------------------------------------------------------------
        # 2. Acelerações — gravidade puxando para baixo
        # -----------------------------------------------------------------
        ax = 0.0
        ay = -GRAVITY   # g = 9,8 m/s² puxando para baixo

        # -----------------------------------------------------------------
        # 3. Propulsão (barra de espaço)
        # -----------------------------------------------------------------
        thrust_active = keys[pygame.K_SPACE] and self.fuel_mass > 0

        if thrust_active:
            # Consome combustível (a massa diminui)
            self.fuel_mass = max(0.0, self.fuel_mass - self.fuel_per_frame)

            # Decompõe a força na direção do nariz
            angle_rad = math.radians(self.angle)
            mass = self.total_mass   # massa atual

            # F = m·a  →  a = F/m
            ax += self.thrust_force * math.sin(angle_rad) / mass   # componente horizontal
            ay += self.thrust_force * math.cos(angle_rad) / mass   # componente vertical

            # Gera partículas de exaustão
            self._spawn_exhaust(particles)

        self.is_thrusting = thrust_active
        sound_manager.play_engine(thrust_active)

        # -----------------------------------------------------------------
        # 4. Integração numérica com Δt = 1/60 s
        # -----------------------------------------------------------------
        self.vx += ax * DT
        self.vy += ay * DT
        self.x += self.vx * DT
        self.y += self.vy * DT

        # -----------------------------------------------------------------
        # 5. Colisão com o solo → game over
        # -----------------------------------------------------------------
        if self.y <= 0:
            self.y = 0.0
            self.alive = False
            sound_manager.play_engine(False)
            self._spawn_crash(particles)

    def _spawn_exhaust(self, particles):
        """Partículas de chama saindo do bocal (oposto ao nariz)."""
        angle_rad = math.radians(self.angle)
        offset = 35.0  # metros do centro ao bocal

        # Posição do bocal no mundo (oposto à direção do nariz)
        ex = self.x - math.sin(angle_rad) * offset
        ey = self.y - math.cos(angle_rad) * offset

        for _ in range(5):
            spread = random.uniform(-0.35, 0.35)
            a = angle_rad + spread
            spd = random.uniform(80, 200)

            # Velocidade da exaustão: oposta ao nariz + velocidade do foguete
            pvx = self.vx - math.sin(a) * spd + random.uniform(-10, 10)
            pvy = self.vy - math.cos(a) * spd + random.uniform(-10, 10)

            r = random.random()
            if r > 0.6:
                color, sz = (255, 255, 200), random.uniform(5, 9)
            elif r > 0.3:
                color, sz = (255, 140, 20), random.uniform(7, 12)
            else:
                color, sz = (240, 50, 20), random.uniform(6, 10)

            particles.append(Particle(
                ex + random.uniform(-3, 3), ey + random.uniform(-3, 3),
                pvx, pvy, color, life=random.uniform(0.2, 0.45), size=sz
            ))

        # Fumaça
        if random.random() < 0.4:
            particles.append(Particle(
                ex + random.uniform(-5, 5), ey + random.uniform(-3, 3),
                self.vx + random.uniform(-15, 15),
                self.vy - random.uniform(40, 90),
                (180, 180, 190), life=0.6, size=random.uniform(10, 16)
            ))

    def _spawn_crash(self, particles):
        """Partículas de explosão ao atingir o solo."""
        for _ in range(120):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(20, 250)
            c = random.choice([
                (255, 60, 20), (255, 140, 20), (255, 220, 40),
                (255, 255, 200), (90, 90, 100), (180, 180, 190)
            ])
            particles.append(Particle(
                self.x + random.uniform(-5, 5),
                random.uniform(0, 15),
                math.cos(ang) * spd,
                abs(math.sin(ang)) * spd,
                c, life=random.uniform(0.6, 2.0), size=random.uniform(6, 18)
            ))

    def draw(self, surface, screen_cx, screen_cy):
        """Desenha o foguete rotacionado em torno do centro de massa."""
        if not self.alive:
            return

        # Centro de massa muda conforme o combustível é gasto.
        # Com tanque cheio: CM está ~15px abaixo do centro geométrico.
        # Com tanque vazio: CM está no centro geométrico do foguete seco.
        fuel_frac = self.fuel_mass / FUEL_TOTAL_MASS if FUEL_TOTAL_MASS > 0 else 0
        cm_offset = fuel_frac * 15.0  # pixels abaixo do centro geométrico

        # Canvas grande o suficiente para rotação sem corte
        canvas_size = 180
        canvas = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)

        # O centro de massa fica no centro do canvas.
        # O centro geométrico do foguete fica cm_offset acima do CM.
        cx = canvas_size // 2
        cy = int(canvas_size / 2 - cm_offset)

        # --- Cores ---
        hull_white = (245, 247, 250)
        hull_shadow = (200, 208, 220)
        accent_red = (235, 55, 55)
        dark_red = (200, 40, 40)
        glass_blue = (70, 185, 240)
        metal_gray = (90, 95, 105)

        # 1. Aletas laterais
        pygame.draw.polygon(canvas, accent_red, [
            (cx - 12, cy + 12), (cx - 28, cy + 34), (cx - 12, cy + 30)])
        pygame.draw.polygon(canvas, dark_red, [
            (cx + 12, cy + 12), (cx + 28, cy + 34), (cx + 12, cy + 30)])

        # 2. Bocal de escape
        pygame.draw.polygon(canvas, metal_gray, [
            (cx - 8, cy + 28), (cx + 8, cy + 28),
            (cx + 11, cy + 36), (cx - 11, cy + 36)])

        # 3. Corpo principal (fuselagem)
        body = [(cx, cy - 35), (cx + 13, cy - 10), (cx + 13, cy + 28),
                (cx - 13, cy + 28), (cx - 13, cy - 10)]
        pygame.draw.polygon(canvas, hull_white, body)
        shadow = [(cx, cy - 35), (cx + 13, cy - 10),
                  (cx + 13, cy + 28), (cx, cy + 28)]
        pygame.draw.polygon(canvas, hull_shadow, shadow)

        # 4. Coifa vermelha (nose cone)
        pygame.draw.polygon(canvas, accent_red, [
            (cx, cy - 35), (cx + 11, cy - 12), (cx - 11, cy - 12)])

        # 5. Faixa decorativa
        pygame.draw.rect(canvas, accent_red, (cx - 13, cy + 8, 26, 6))

        # 6. Janela / escotilha
        pygame.draw.circle(canvas, metal_gray, (cx, cy - 4), 9)
        pygame.draw.circle(canvas, glass_blue, (cx, cy - 4), 7)
        pygame.draw.circle(canvas, (255, 255, 255, 200), (cx - 2, cy - 6), 2)

        # 7. Indicador visual de combustível no corpo
        fuel_bar_h = int(30 * fuel_frac)
        if fuel_bar_h > 0:
            pygame.draw.rect(canvas, (0, 200, 100, 80),
                             (cx - 10, cy + 28 - fuel_bar_h, 20, fuel_bar_h))

        # 8. Onda de choque em alta velocidade
        speed = math.hypot(self.vx, self.vy)
        if speed > 100:
            shock_alpha = min(160, int((speed - 100) * 1.2))
            shock_surf = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
            pygame.draw.lines(shock_surf, (180, 230, 255, shock_alpha), False,
                              [(cx - 32, cy + 25), (cx, cy - 40), (cx + 32, cy + 25)], 3)
            canvas.blit(shock_surf, (0, 0))

        # Rotação: pygame roda CCW para ângulo positivo.
        # Ângulo físico positivo = nariz para a DIREITA = rotação CW = ângulo negativo.
        rotated = pygame.transform.rotate(canvas, -self.angle)
        rect = rotated.get_rect(center=(int(screen_cx), int(screen_cy)))
        surface.blit(rotated, rect)


# =============================================================================
# Jogo Principal
# =============================================================================
class RocketGame:
    def __init__(self):
        pygame.init()

        # Tela cheia (requisito)
        info = pygame.display.Info()
        self.screen_w = info.current_w
        self.screen_h = info.current_h
        self.screen = pygame.display.set_mode(
            (self.screen_w, self.screen_h), pygame.FULLSCREEN)
        pygame.display.set_caption("Foguete — Simulador Físico")

        self.clock = pygame.time.Clock()

        # Fontes
        self.font_title = pygame.font.SysFont("Segoe UI, Arial", 38, bold=True)
        self.font_sub = pygame.font.SysFont("Segoe UI, Arial", 22, bold=True)
        self.font_hud = pygame.font.SysFont("Segoe UI, Arial", 18, bold=True)
        self.font_small = pygame.font.SysFont("Segoe UI, Arial", 15)
        self.font_score = pygame.font.SysFont("Segoe UI, Arial", 48, bold=True)

        self.sounds = SoundManager()
        self.selected_mode = "AEROESPACIAL"   # Modo 2 (Realista/Jogável) selecionado por padrão; fácil de alternar
        self.state = "MENU"                   # "MENU", "PLAYING", "GAMEOVER", "EXPLANATION"
        self.previous_state = "MENU"
        self.stars = [Star(self.screen_w, self.screen_h) for _ in range(110)]
        self.anim_time = 0.0
        self.btn_rects = {}
        self.reset_game()

    # -----------------------------------------------------------------
    def reset_game(self):
        self.rocket = Rocket(self.selected_mode)
        self.particles = []
        self.clouds = [Cloud(alt=random.uniform(50, 700)) for _ in range(15)]
        self.score = 0.0
        self.max_altitude = INITIAL_ALTITUDE
        self.max_speed = 0.0
        self.low_fuel_timer = 0.0
        self.sounds.play_engine(False)

    # -----------------------------------------------------------------
    # Utilitários de renderização
    # -----------------------------------------------------------------
    @staticmethod
    def lerp_color(c1, c2, t):
        t = max(0.0, min(1.0, t))
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

    def draw_background(self, altitude):
        pct = min(1.0, max(0.0, altitude / 3000.0))

        stops = [
            (0.00, (135, 206, 250), (225, 245, 255)),
            (0.30, (50, 130, 220), (120, 190, 245)),
            (0.60, (20, 45, 110), (45, 95, 180)),
            (1.00, (10, 15, 50), (25, 30, 80)),
        ]

        top_c, bot_c = stops[-1][1], stops[-1][2]
        for i in range(len(stops) - 1):
            if stops[i][0] <= pct <= stops[i + 1][0]:
                f = (pct - stops[i][0]) / (stops[i + 1][0] - stops[i][0])
                top_c = self.lerp_color(stops[i][1], stops[i + 1][1], f)
                bot_c = self.lerp_color(stops[i][2], stops[i + 1][2], f)
                break

        for y in range(0, self.screen_h, 4):
            f = y / self.screen_h
            r = int(top_c[0] + (bot_c[0] - top_c[0]) * f)
            g = int(top_c[1] + (bot_c[1] - top_c[1]) * f)
            b = int(top_c[2] + (bot_c[2] - top_c[2]) * f)
            pygame.draw.rect(self.screen, (r, g, b), (0, y, self.screen_w, 4))

        space_alpha = min(1.0, max(0.0, (pct - 0.3) / 0.7))
        for star in self.stars:
            star.draw(self.screen, -altitude * 1.5, self.anim_time, space_alpha,
                      self.screen_h)

    def draw_ground(self, cam_x, cam_y):
        """Desenha o solo (y=0 no mundo) e a plataforma de lançamento."""
        ground_sy = int(self.screen_h / 2 + cam_y)

        if ground_sy < self.screen_h + 5:
            gy = max(0, ground_sy)
            gh = self.screen_h - gy
            if gh > 0:
                # Solo verde
                pygame.draw.rect(self.screen, (45, 110, 45),
                                 (0, gy, self.screen_w, gh))
                pygame.draw.rect(self.screen, (60, 135, 55),
                                 (0, gy, self.screen_w, 4))

                # Plataforma de concreto (posição x=0 no mundo)
                pad_sx = int(self.screen_w / 2 - cam_x)
                pad_w = 280
                if -pad_w < pad_sx < self.screen_w + pad_w:
                    pygame.draw.rect(self.screen, (90, 95, 105),
                                     (pad_sx - pad_w // 2, gy - 5, pad_w, 12))

                    # Torre de lançamento
                    tx = pad_sx - 80
                    top_y = max(0, gy - 120)
                    for ty in range(top_y, gy, 15):
                        pygame.draw.line(self.screen, (160, 50, 40),
                                         (tx, ty), (tx + 25, ty + 15), 3)
                        pygame.draw.line(self.screen, (160, 50, 40),
                                         (tx + 25, ty), (tx, ty + 15), 3)
                    pygame.draw.line(self.screen, (180, 60, 50),
                                     (tx, top_y), (tx, gy), 4)
                    pygame.draw.line(self.screen, (180, 60, 50),
                                     (tx + 25, top_y), (tx + 25, gy), 4)

    # -----------------------------------------------------------------
    # HUD — Informações na tela durante o jogo
    # -----------------------------------------------------------------
    def draw_hud(self):
        hud_h = 140
        hud = pygame.Surface((self.screen_w, hud_h), pygame.SRCALPHA)
        hud.fill((10, 15, 25, 215))
        pygame.draw.line(hud, (50, 75, 110),
                         (0, hud_h - 1), (self.screen_w, hud_h - 1), 2)
        self.screen.blit(hud, (0, 0))

        # ---- Score (tempo no ar) ----
        score_txt = f"SCORE: {self.score:.2f}s"
        lbl_score = self.font_score.render(score_txt, True, (255, 215, 60))
        self.screen.blit(lbl_score, (30, 4))

        # ---- Barra de combustível ----
        fuel_pct = self.rocket.fuel_mass / FUEL_TOTAL_MASS
        bar_w, bar_h = 240, 20
        bx, by = 30, 64

        pygame.draw.rect(self.screen, (30, 40, 50),
                         (bx, by, bar_w, bar_h), border_radius=6)

        if fuel_pct > 0.45:
            fc = (40, 220, 100)
        elif fuel_pct > 0.20:
            fc = (255, 190, 30)
        else:
            flash = int(128 + 127 * math.sin(self.anim_time * 12))
            fc = (255, flash, flash)

        fw = int((bar_w - 4) * fuel_pct)
        if fw > 0:
            pygame.draw.rect(self.screen, fc,
                             (bx + 2, by + 2, fw, bar_h - 4), border_radius=4)
        pygame.draw.rect(self.screen, (120, 140, 170),
                         (bx, by, bar_w, bar_h), 2, border_radius=6)

        lbl_fuel = self.font_hud.render(
            f"COMBUSTÍVEL: {fuel_pct * 100:.1f}% ({self.rocket.fuel_mass:.0f} kg)",
            True, (240, 245, 255))
        self.screen.blit(lbl_fuel, (bx + bar_w + 12, by + 1))

        # Status do Áudio e Atalho de Explicação
        audio_txt = "[M] ÁUDIO: MUDO" if self.sounds.muted else "[M] ÁUDIO: ATIVO"
        audio_color = (255, 120, 120) if self.sounds.muted else (130, 220, 160)
        lbl_audio = self.font_small.render(audio_txt, True, audio_color)
        self.screen.blit(lbl_audio, (30, 92))

        lbl_help_hud = self.font_small.render(
            "[E] VER EXPLICAÇÃO FÍSICA DOS MODOS", True, (0, 230, 255))
        self.screen.blit(lbl_help_hud, (30, 114))

        # ---- Altitude e Velocidade ----
        col2 = self.screen_w // 2 - 130
        lbl_alt = self.font_hud.render(
            f"ALTITUDE: {self.rocket.y:.1f} m", True, (200, 220, 255))
        self.screen.blit(lbl_alt, (col2, 64))

        spd = math.hypot(self.rocket.vx, self.rocket.vy)
        lbl_vel = self.font_hud.render(
            f"VEL: {spd:.1f} m/s   Vy={self.rocket.vy:+.1f}   Vx={self.rocket.vx:+.1f}",
            True, (200, 220, 255))
        self.screen.blit(lbl_vel, (col2, 88))

        # Aceleração vertical líquida real
        angle_rad = math.radians(self.rocket.angle)
        if self.rocket.is_thrusting and self.rocket.total_mass > 0:
            accel_vert = (self.rocket.thrust_force * math.cos(angle_rad) / self.rocket.total_mass) - GRAVITY
        else:
            accel_vert = -GRAVITY

        acc_color = (0, 235, 170) if accel_vert >= 0 else (255, 95, 95)
        lbl_accel = self.font_hud.render(
            f"ACEL. VERTICAL: {accel_vert:+.2f} m/s²", True, acc_color)
        self.screen.blit(lbl_accel, (col2, 112))

        # ---- Modo Ativo, Massa, Motor e TWR ----
        col3 = self.screen_w - 440
        mode_cfg = GAME_MODES[self.rocket.mode]
        badge_box = pygame.Rect(col3, 8, 420, 26)
        pygame.draw.rect(self.screen, (25, 35, 50), badge_box, border_radius=6)
        pygame.draw.rect(self.screen, mode_cfg["badge_color"], badge_box, 2, border_radius=6)
        
        lbl_mode = self.font_hud.render(
            f"{mode_cfg['title'].upper()} (TWR {self.rocket.twr:.2f})", True, mode_cfg["badge_color"])
        self.screen.blit(lbl_mode, (col3 + 10, 11))

        mass = self.rocket.total_mass
        lbl_mass = self.font_hud.render(
            f"MASSA: {mass:.0f} kg ({mass / 1000:.1f}t)   |   NARIZ: {self.rocket.angle:+.1f}°",
            True, (200, 220, 255))
        self.screen.blit(lbl_mass, (col3, 40))

        thrust_status = "LIGADO" if self.rocket.is_thrusting else "DESLIGADO"
        thrust_color = (0, 255, 160) if self.rocket.is_thrusting else (180, 180, 200)
        lbl_thrust = self.font_hud.render(
            f"MOTOR: {thrust_status}  (F = {self.rocket.thrust_force / 1e6:.1f} MN)", True, thrust_color)
        self.screen.blit(lbl_thrust, (col3, 64))

        # Constantes físicas resumidas
        lbl_g = self.font_small.render(
            f"g = {GRAVITY} m/s²   |   Δt = 1/{FPS}s   |   Consumo: 100 kg/frame",
            True, (140, 165, 195))
        self.screen.blit(lbl_g, (col3, 90))

        lbl_switch = self.font_small.render(
            "[1] Modo Acadêmico   |   [2] Modo Aeroespacial", True, (240, 200, 90))
        self.screen.blit(lbl_switch, (col3, 112))

        # ---- Dica inicial de controles ----
        if self.score < 5.0:
            tip = self.font_sub.render(
                "ESPAÇO: Acelerar   |   ← → / A D: Manobrar   |   E: Explicação Física",
                True, (255, 230, 100))
            r = tip.get_rect(center=(self.screen_w // 2, self.screen_h - 40))
            self.screen.blit(tip, r)

    # -----------------------------------------------------------------
    # Tela de Menu com Seleção Interativa de Modos
    # -----------------------------------------------------------------
    def draw_menu(self):
        self.draw_background(0)

        pw = min(880, self.screen_w - 40)
        ph = min(660, self.screen_h - 40)
        box = pygame.Surface((pw, ph), pygame.SRCALPHA)
        box.fill((12, 18, 32, 235))
        pygame.draw.rect(box, (70, 130, 200), (0, 0, pw, ph), 2, border_radius=16)
        bx = (self.screen_w - pw) // 2
        by = (self.screen_h - ph) // 2
        self.screen.blit(box, (bx, by))

        # Título
        t = self.font_title.render("FOGUETE — Simulador Físico", True, (255, 215, 60))
        self.screen.blit(t, t.get_rect(center=(self.screen_w // 2, by + 40)))

        sub = self.font_sub.render("SELECIONE O MODO DE SIMULAÇÃO:", True, (220, 235, 255))
        self.screen.blit(sub, sub.get_rect(center=(self.screen_w // 2, by + 80)))

        # Cards dos Modos
        card_w = (pw - 60) // 2
        card_h = 240
        card_y = by + 110

        # --- Card 1: Modo Acadêmico ---
        c1_x = bx + 22
        is_m1 = (self.selected_mode == "ACADEMICO")
        c1_bg = (35, 25, 20, 240) if is_m1 else (20, 25, 35, 180)
        c1_border = (255, 160, 40) if is_m1 else (65, 80, 105)
        c1_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        c1_surf.fill(c1_bg)
        pygame.draw.rect(c1_surf, c1_border, (0, 0, card_w, card_h), 3 if is_m1 else 1, border_radius=12)
        self.screen.blit(c1_surf, (c1_x, card_y))
        self.btn_rects["mode_1"] = pygame.Rect(c1_x, card_y, card_w, card_h)

        status_m1 = "[ ATIVO ]" if is_m1 else "[ TECLA 1 ]"
        t1 = self.font_hud.render(f"MODO 1: ACADÊMICO {status_m1}", True, (255, 175, 60) if is_m1 else (190, 190, 200))
        self.screen.blit(t1, (c1_x + 16, card_y + 14))

        sub1 = self.font_small.render("Requisitos Estritos da Atividade", True, (200, 210, 225))
        self.screen.blit(sub1, (c1_x + 16, card_y + 38))

        specs_m1 = [
            "• Empuxo: 2,0 × 10⁶ N (Fiel ao enunciado)",
            "• Razão Empuxo/Peso (TWR): 1,02",
            "• Aceleração inicial: 0,20 m/s² (muito baixa)",
            "• Rotação: Salto instantâneo para ±30°",
            "• Comportamento: Mal sobe no início e",
            "  despenca ao virar (sustentação < peso).",
        ]
        for idx, sp in enumerate(specs_m1):
            lbl_sp = self.font_small.render(sp, True, (230, 220, 210) if idx < 4 else (255, 130, 120))
            self.screen.blit(lbl_sp, (c1_x + 16, card_y + 65 + idx * 24))

        # --- Card 2: Modo Aeroespacial ---
        c2_x = bx + pw - card_w - 22
        is_m2 = (self.selected_mode == "AEROESPACIAL")
        c2_bg = (18, 38, 30, 240) if is_m2 else (20, 25, 35, 180)
        c2_border = (40, 230, 160) if is_m2 else (65, 80, 105)
        c2_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        c2_surf.fill(c2_bg)
        pygame.draw.rect(c2_surf, c2_border, (0, 0, card_w, card_h), 3 if is_m2 else 1, border_radius=12)
        self.screen.blit(c2_surf, (c2_x, card_y))
        self.btn_rects["mode_2"] = pygame.Rect(c2_x, card_y, card_w, card_h)

        status_m2 = "[ ATIVO ]" if is_m2 else "[ TECLA 2 ]"
        t2 = self.font_hud.render(f"MODO 2: AEROESPACIAL {status_m2}", True, (50, 240, 170) if is_m2 else (190, 190, 200))
        self.screen.blit(t2, (c2_x + 16, card_y + 14))

        sub2 = self.font_small.render("Opção 1 — Realista & Jogável", True, (200, 210, 225))
        self.screen.blit(sub2, (c2_x + 16, card_y + 38))

        specs_m2 = [
            "• Empuxo: 2,8 × 10⁶ N (Padrão Falcon 9 / Saturn V)",
            "• Razão Empuxo/Peso (TWR): 1,43",
            "• Aceleração inicial: 4,20 m/s² (potente e ágil)",
            "• Rotação: Gimbal suave contínuo (55°/s)",
            "• Comportamento: Decolagem potente e",
            "  manobras firmes com sustentação positiva.",
        ]
        for idx, sp in enumerate(specs_m2):
            lbl_sp = self.font_small.render(sp, True, (210, 240, 230) if idx < 4 else (120, 255, 180))
            self.screen.blit(lbl_sp, (c2_x + 16, card_y + 65 + idx * 24))

        # Dica de alternância
        hint_mode = self.font_small.render(
            "Pressione [ 1 ] ou [ 2 ] (ou clique nos cards acima) para selecionar o modo",
            True, (200, 220, 255))
        self.screen.blit(hint_mode, hint_mode.get_rect(center=(self.screen_w // 2, card_y + card_h + 20)))

        # Botão de Explicação Física Completa
        btn_exp_w, btn_exp_h = 580, 44
        btn_exp_x = (self.screen_w - btn_exp_w) // 2
        btn_exp_y = card_y + card_h + 45
        self.btn_rects["explanation"] = pygame.Rect(btn_exp_x, btn_exp_y, btn_exp_w, btn_exp_h)

        pygame.draw.rect(self.screen, (25, 45, 75), self.btn_rects["explanation"], border_radius=8)
        pygame.draw.rect(self.screen, (0, 210, 255), self.btn_rects["explanation"], 2, border_radius=8)
        exp_txt = self.font_hud.render(
            "🔬 [ E ] LER EXPLICAÇÃO FÍSICA DETALHADA DOS MODOS", True, (0, 230, 255))
        self.screen.blit(exp_txt, exp_txt.get_rect(center=self.btn_rects["explanation"].center))

        # Controles Básicos
        ctrl_txt = self.font_small.render(
            "Controles: [ ESPAÇO ] Motor   |   [ ← → ] ou [ A / D ] Manobrar   |   [ M ] Áudio   |   [ ESC ] Sair",
            True, (170, 190, 220))
        self.screen.blit(ctrl_txt, ctrl_txt.get_rect(center=(self.screen_w // 2, by + ph - 65)))

        # Botão pulsante para começar
        pulse = (math.sin(self.anim_time * 6) + 1) / 2
        bc = (int(255 * (0.8 + 0.2 * pulse)), int(180 * (0.8 + 0.2 * pulse)), 40)
        s = self.font_sub.render(
            f"PRESSIONE [ ESPAÇO ] PARA DECOLAR NO {self.selected_mode}", True, bc)
        self.screen.blit(s, s.get_rect(center=(self.screen_w // 2, by + ph - 25)))

    # -----------------------------------------------------------------
    # Tela de Explicação Física Completa (Diferença & Por que existem)
    # -----------------------------------------------------------------
    def draw_explanation(self):
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((10, 15, 25, 240))
        self.screen.blit(overlay, (0, 0))

        pw = min(1140, self.screen_w - 40)
        ph = min(720, self.screen_h - 40)
        box = pygame.Surface((pw, ph), pygame.SRCALPHA)
        box.fill((14, 20, 35, 248))
        pygame.draw.rect(box, (0, 200, 255), (0, 0, pw, ph), 2, border_radius=16)
        bx = (self.screen_w - pw) // 2
        by = (self.screen_h - ph) // 2
        self.screen.blit(box, (bx, by))

        # Cabeçalho
        t = self.font_title.render("🔬 ANÁLISE FÍSICA: POR QUE EXISTEM DOIS MODOS?", True, (255, 215, 60))
        self.screen.blit(t, t.get_rect(center=(self.screen_w // 2, by + 35)))

        sub = self.font_sub.render(
            "Entenda a matemática newtoniana, os requisitos da atividade e a engenharia aeroespacial real",
            True, (180, 220, 255))
        self.screen.blit(sub, sub.get_rect(center=(self.screen_w // 2, by + 68)))

        # Colunas Comparativas
        col_w = (pw - 60) // 2
        col_h = 390
        col_y = by + 98

        # --- Coluna 1: Modo Acadêmico ---
        col1_x = bx + 20
        c1_box = pygame.Surface((col_w, col_h), pygame.SRCALPHA)
        c1_box.fill((30, 22, 20, 210))
        pygame.draw.rect(c1_box, (245, 140, 40), (0, 0, col_w, col_h), 2, border_radius=10)
        self.screen.blit(c1_box, (col1_x, col_y))

        m1_title = self.font_hud.render("MODO 1: ACADÊMICO (Requisitos da Atividade)", True, (255, 165, 50))
        self.screen.blit(m1_title, (col1_x + 16, col_y + 14))

        m1_lines = [
            ("POR QUE ELE EXISTE?", (255, 200, 100)),
            ("• Criado para seguir estritamente o enunciado da atividade escolar/universitária.", (220, 230, 245)),
            ("• Mantém os dados nominais da tabela: F = 2,0 MN, m = 200t, g = 9,8 m/s².", (220, 230, 245)),
            ("", (0, 0, 0)),
            ("POR QUE O FOGUETE MAL SOBE? (A FÍSICA):", (255, 110, 110)),
            ("• Massa total inicial: m = 100t (foguete) + 100t (combustível) = 200.000 kg", (220, 230, 245)),
            ("• Força peso: P = m · g = 200.000 × 9,8 = 1.960.000 N", (220, 230, 245)),
            ("• Empuxo gerado: F = 2.000.000 N", (220, 230, 245)),
            ("• Força líquida vertical útil: 2.000.000 - 1.960.000 = míseros 40.000 N!", (255, 180, 180)),
            ("• TWR = 1,02 (o motor tem apenas 2% de folga sobre o próprio peso)", (255, 180, 180)),
            ("• Aceleração inicial: a = 40.000 / 200.000 = 0,20 m/s² (quase imperceptível!)", (255, 130, 130)),
            ("", (0, 0, 0)),
            ("O PROBLEMA DA INCLINAÇÃO (±30°):", (255, 110, 110)),
            ("• Ao virar 30°: Fy = F · cos(30°) = 2.000.000 × 0,866 = 1.732.000 N", (220, 230, 245)),
            ("• Como 1.732.000 N < 1.960.000 N (Peso), a aceleração vertical fica NEGATIVA (-1,14 m/s²)!", (255, 110, 110)),
            ("• Consequência: O foguete cai em direção ao solo ao tentar virar!", (255, 90, 90)),
        ]
        curr_y = col_y + 40
        for text, color in m1_lines:
            if text == "":
                curr_y += 6
                continue
            lbl = self.font_small.render(text, True, color)
            self.screen.blit(lbl, (col1_x + 16, curr_y))
            curr_y += 20

        # --- Coluna 2: Modo Aeroespacial ---
        col2_x = bx + pw - col_w - 20
        c2_box = pygame.Surface((col_w, col_h), pygame.SRCALPHA)
        c2_box.fill((16, 32, 28, 210))
        pygame.draw.rect(c2_box, (40, 230, 160), (0, 0, col_w, col_h), 2, border_radius=10)
        self.screen.blit(c2_box, (col2_x, col_y))

        m2_title = self.font_hud.render("MODO 2: AEROESPACIAL (Opção 1 — Realista & Jogável)", True, (50, 240, 170))
        self.screen.blit(m2_title, (col2_x + 16, col_y + 14))

        m2_lines = [
            ("POR QUE ELE EXISTE?", (120, 255, 200)),
            ("• Foguetes reais (Falcon 9, Saturn V) nunca decolam com TWR de 1,02.", (220, 240, 235)),
            ("• Engenheiros dimensionam o empuxo entre 1,2 e 1,5 vezes o peso inicial", (220, 240, 235)),
            ("  para permitir aceleração rápida e manobrabilidade estável.", (220, 240, 235)),
            ("", (0, 0, 0)),
            ("COMO A FÍSICA FOI CALIBRADA:", (120, 255, 200)),
            ("• Empuxo calibrado: F = 2.800.000 N (TWR = 1,43 — padrão aeroespacial real)", (220, 240, 235)),
            ("• Força líquida vertical inicial: 2.800.000 - 1.960.000 = 840.000 N!", (140, 255, 200)),
            ("• Aceleração inicial: a = 840.000 / 200.000 = 4,20 m/s² (decolagem potente)", (140, 255, 200)),
            ("• As leis da física (F = m·a, gravidade e queima) continuam 100% autênticas!", (220, 240, 235)),
            ("", (0, 0, 0)),
            ("SUSTENTAÇÃO EM CURVAS E GIMBAL SUAVE:", (120, 255, 200)),
            ("• A 30°: Fy = 2.800.000 × cos(30°) = 2.424.870 N > 1.960.000 N (Peso)", (220, 240, 235)),
            ("• Aceleração vertical se mantém POSITIVA (+2,32 m/s²). O foguete sobe em curvas!", (140, 255, 200)),
            ("• Rotação gradual (55°/s): simula os atuadores de vetorização (gimbal) do motor,", (220, 240, 235)),
            ("  eliminando os trancos instantâneos e permitindo pilotagem precisa.", (140, 255, 200)),
        ]
        curr_y = col_y + 40
        for text, color in m2_lines:
            if text == "":
                curr_y += 6
                continue
            lbl = self.font_small.render(text, True, color)
            self.screen.blit(lbl, (col2_x + 16, curr_y))
            curr_y += 20

        # Conclusão / Resumo no rodapé interno
        syn_box = pygame.Rect(bx + 20, col_y + col_h + 12, pw - 40, 68)
        pygame.draw.rect(self.screen, (22, 32, 50), syn_box, border_radius=8)
        pygame.draw.rect(self.screen, (0, 180, 220), syn_box, 1, border_radius=8)

        syn_t1 = self.font_small.render(
            "RESUMO: A física teórica (2ª Lei de Newton com massa variável e gravidade real) é 100% idêntica nos dois modos.",
            True, (255, 220, 120))
        self.screen.blit(syn_t1, (syn_box.x + 16, syn_box.y + 12))

        syn_t2 = self.font_small.render(
            "O Modo 1 testa a matemática estrita da atividade escolar; o Modo 2 aplica o dimensionamento de engenharia real para tornar o jogo jogável.",
            True, (220, 235, 250))
        self.screen.blit(syn_t2, (syn_box.x + 16, syn_box.y + 36))

        # Atalhos de saída
        nav = self.font_hud.render(
            "[ 1 ] Selecionar Acadêmico   |   [ 2 ] Selecionar Aeroespacial   |   [ ESPAÇO / E / ESC ] Fechar e Jogar",
            True, (0, 255, 200))
        self.screen.blit(nav, nav.get_rect(center=(self.screen_w // 2, by + ph - 22)))

    # -----------------------------------------------------------------
    # Tela de Game Over
    # -----------------------------------------------------------------
    def draw_game_over(self):
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((20, 5, 5, 220))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 680, 460
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((30, 15, 18, 245))
        pygame.draw.rect(panel, (240, 70, 70),
                         (0, 0, pw, ph), 3, border_radius=16)
        px = (self.screen_w - pw) // 2
        py = (self.screen_h - ph) // 2
        self.screen.blit(panel, (px, py))

        t = self.font_title.render("GAME OVER — FOGUETE DESTRUÍDO", True, (255, 75, 75))
        self.screen.blit(t, t.get_rect(center=(self.screen_w // 2, py + 40)))

        score_s = self.font_score.render(
            f"SCORE: {self.score:.2f} s", True, (255, 215, 60))
        self.screen.blit(score_s, score_s.get_rect(center=(self.screen_w // 2, py + 95)))

        mode_cfg = GAME_MODES[self.rocket.mode]
        lbl_mod = self.font_hud.render(
            f"Modo Jogado: {mode_cfg['title']} ({mode_cfg['subtitle']})", True, mode_cfg["badge_color"])
        self.screen.blit(lbl_mod, lbl_mod.get_rect(center=(self.screen_w // 2, py + 140)))

        stats = [
            f"Altitude Máxima: {self.max_altitude:.1f} m",
            f"Velocidade Máxima: {self.max_speed:.1f} m/s ({self.max_speed * 3.6:.1f} km/h)",
            f"Combustível Restante: {self.rocket.fuel_mass:.0f} kg ({self.rocket.fuel_mass / FUEL_TOTAL_MASS * 100:.1f}%)",
        ]
        for i, txt in enumerate(stats):
            s = self.font_hud.render(txt, True, (230, 235, 245))
            self.screen.blit(s, (px + 60, py + 175 + i * 32))

        # Dica física caso tenha caído no modo acadêmico
        if self.rocket.mode == "ACADEMICO":
            tip_fail = self.font_small.render(
                "* No Modo Acadêmico (TWR 1,02), qualquer inclinação de 30° faz o foguete perder sustentação e cair.",
                True, (255, 170, 130))
            self.screen.blit(tip_fail, (px + 30, py + 290))

        # Atalhos
        r1 = self.font_sub.render(
            "[ R ] ou [ ESPAÇO ]: Jogar Novamente", True, (255, 220, 80))
        self.screen.blit(r1, r1.get_rect(center=(self.screen_w // 2, py + 340)))

        r2 = self.font_small.render(
            "[ 1 ] Modo Acadêmico   |   [ 2 ] Modo Aeroespacial   |   [ E ] Ver Explicação Física   |   [ ESC ] Sair",
            True, (200, 230, 255))
        self.screen.blit(r2, r2.get_rect(center=(self.screen_w // 2, py + 390)))

    # -----------------------------------------------------------------
    # Loop Principal
    # -----------------------------------------------------------------
    def run(self):
        running = True

        while running:
            self.clock.tick(FPS)       # Limita a 60 FPS
            self.anim_time += DT       # Usa Δt fixo = 1/60

            # --- Eventos ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mpos = event.pos
                    if self.state == "MENU":
                        if "mode_1" in self.btn_rects and self.btn_rects["mode_1"].collidepoint(mpos):
                            self.selected_mode = "ACADEMICO"
                        elif "mode_2" in self.btn_rects and self.btn_rects["mode_2"].collidepoint(mpos):
                            self.selected_mode = "AEROESPACIAL"
                        elif "explanation" in self.btn_rects and self.btn_rects["explanation"].collidepoint(mpos):
                            self.previous_state = self.state
                            self.state = "EXPLANATION"

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "EXPLANATION":
                            self.state = self.previous_state
                        else:
                            running = False

                    elif event.key == pygame.K_m:
                        self.sounds.toggle_mute()

                    # Atalho para alternar para a tela de explicação física
                    elif event.key in (pygame.K_e, pygame.K_h):
                        if self.state == "EXPLANATION":
                            self.state = self.previous_state
                        else:
                            self.previous_state = self.state
                            self.state = "EXPLANATION"

                    # Teclas para selecionar os Modos
                    elif event.key in (pygame.K_1, pygame.K_KP1):
                        self.selected_mode = "ACADEMICO"
                        if self.state in ("PLAYING", "GAMEOVER"):
                            self.reset_game()
                            self.state = "PLAYING"

                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        self.selected_mode = "AEROESPACIAL"
                        if self.state in ("PLAYING", "GAMEOVER"):
                            self.reset_game()
                            self.state = "PLAYING"

                    elif event.key == pygame.K_TAB:
                        self.selected_mode = "AEROESPACIAL" if self.selected_mode == "ACADEMICO" else "ACADEMICO"
                        if self.state in ("PLAYING", "GAMEOVER"):
                            self.reset_game()
                            self.state = "PLAYING"

                    # Navegação por estados
                    elif self.state == "MENU":
                        if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                            self.reset_game()
                            self.state = "PLAYING"

                    elif self.state == "GAMEOVER":
                        if event.key in (pygame.K_r, pygame.K_SPACE):
                            self.reset_game()
                            self.state = "PLAYING"

                    elif self.state == "EXPLANATION":
                        if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                            if self.previous_state == "PLAYING":
                                self.reset_game()
                            self.state = self.previous_state if self.previous_state != "GAMEOVER" else "PLAYING"

            keys = pygame.key.get_pressed()

            # --- Atualiza partículas (em qualquer estado) ---
            for p in self.particles:
                p.update(DT)
            self.particles = [p for p in self.particles if p.life > 0]

            # --- Lógica do estado PLAYING ---
            if self.state == "PLAYING":
                self.score += DT

                for cloud in self.clouds:
                    cloud.update(DT)

                # Atualiza o foguete (física principal com o modo selecionado)
                self.rocket.update(keys, self.particles, self.sounds)

                # Estatísticas
                if self.rocket.y > self.max_altitude:
                    self.max_altitude = self.rocket.y
                spd = math.hypot(self.rocket.vx, self.rocket.vy)
                if spd > self.max_speed:
                    self.max_speed = spd

                # Game over?
                if not self.rocket.alive:
                    self.state = "GAMEOVER"
                    self.sounds.play_explosion()

            # --- Câmera segue o foguete ---
            cam_x = self.rocket.x
            cam_y = self.rocket.y

            # --- Renderização ---
            alt = self.rocket.y if self.state != "MENU" else 0
            self.draw_background(alt)

            if self.state not in ("MENU",):
                # Solo
                self.draw_ground(cam_x, cam_y)

                # Nuvens
                for cloud in self.clouds:
                    cloud.draw(self.screen, cam_x, cam_y,
                               self.screen_w, self.screen_h)

                # Partículas
                for p in self.particles:
                    p.draw(self.screen, cam_x, cam_y,
                           self.screen_w, self.screen_h)

                # Foguete (no centro da tela — câmera segue)
                rcx = self.screen_w // 2
                rcy = self.screen_h // 2
                self.rocket.draw(self.screen, rcx, rcy)

                # HUD
                self.draw_hud()

            # --- Telas especiais ---
            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "GAMEOVER":
                self.draw_game_over()
            elif self.state == "EXPLANATION":
                self.draw_explanation()

            pygame.display.flip()

        self.sounds.stop_all()
        pygame.quit()
        sys.exit()


# =============================================================================
if __name__ == "__main__":
    game = RocketGame()
    game.run()
