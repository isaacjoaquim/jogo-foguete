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
ROCKET_DRY_MASS = 100_000.0                # Massa do foguete: 100 ton = 100.000 kg (requisito estrito da atividade)
FUEL_TOTAL_MASS = 100_000.0                # Capacidade máxima do tanque: 100 ton (requisito estrito da atividade)
INITIAL_FUEL_MASS = 100_000.0              # Combustível inicial: 100 ton (tanque CHEIO conforme solicitado)
MAX_ANGLE = 30.0                            # ±30° com a vertical
INITIAL_ALTITUDE = 800.0                    # Começa já no ar (requisito)
TARGET_ALTITUDE = 10_000.0                  # Altitude para vitória (chegada à órbita espacial: 10.000 m / 10 km)
SPEED_OF_SOUND = 340.0                      # Velocidade do som no ar ao nível do mar (Mach 1.0 = 340 m/s)

# (Parâmetros de empuxo e consumo definidos dentro de cada modo em GAME_MODES)

# -----------------------------------------------------------------------------
# Dicionário de Modos de Jogo
# -----------------------------------------------------------------------------
GAME_MODES = {
    "ACADEMICO": {
        "title": "Modo 1: Acadêmico",
        "subtitle": "Requisitos Estritos da Atividade",
        "thrust": 2_000_000.0,              # Força original da atividade: 2.0 MN
        "fuel_per_frame": 0.001 * FUEL_TOTAL_MASS,  # 100 kg por frame
        "rotation_speed": 0.0,              # Salto instantâneo para ±30° (original)
        "badge_color": (255, 150, 50),
    },
    "AEROESPACIAL": {
        "title": "Modo 2: Aeroespacial",
        "subtitle": "Opção 1 — Realista & Super Veloz",
        "thrust": 3_500_000.0,              # Empuxo de alta potência: 3.5 MN para altíssima velocidade
        "fuel_per_frame": 0.001 * FUEL_TOTAL_MASS,  # 100 kg por frame
        "rotation_speed": 55.0,             # Rotação suave contínua (55°/s) com vetorização (gimbal)
        "badge_color": (40, 225, 160),
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
            # Se o mixer já foi inicializado pelo pre_init+pygame.init(), não re-inicializa
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            self.enabled = True
            self.sample_rate = 22050
            self.snd_boom = self._generate_explosion()
            self.snd_boom_sonic = self._generate_sonic_boom()
            self.snd_engine = self._generate_engine_loop()
            self.snd_refuel = self._generate_refuel()
            self.snd_victory = self._generate_victory()
            self.snd_blip = self._generate_ui_blip()
            self.snd_engine.set_volume(0.12)   # Volume base inicial
            self.snd_boom.set_volume(0.25)
            self.snd_boom_sonic.set_volume(0.35)
            self.snd_refuel.set_volume(0.32)
            self.snd_victory.set_volume(0.35)
            self.snd_blip.set_volume(0.22)
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

    def _generate_sonic_boom(self):
        """Gera um estrondo sônico duplo característico (onda N de Mach) ao romper a barreira do som."""
        n = int(self.sample_rate * 0.85)
        samples = []
        for i in range(n):
            t = i / self.sample_rate
            p1 = math.exp(-max(0.0, t - 0.01) * 26.0) * math.sin(2 * math.pi * 50 * t)
            p2 = (math.exp(-max(0.0, t - 0.09) * 22.0) * math.sin(2 * math.pi * 45 * (t - 0.09))) if t >= 0.09 else 0.0
            env = max(0.0, 1.0 - (t / 0.85) ** 0.5)
            noise = (random.random() * 2 - 1) * math.exp(-t * 18.0) * 0.25
            samples.append(max(-1.0, min(1.0, (p1 + p2 * 0.85 + noise) * env * 0.45)))
        return self._make_sound(samples)

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

    def _generate_refuel(self):
        """Gera um som brilhante e harmônico de recarga de combustível."""
        n = int(self.sample_rate * 0.45)
        samples = []
        freqs = [523.25, 659.25, 783.99, 1046.50]
        for i in range(n):
            t = i / self.sample_rate
            seg = min(3, int(t / 0.10))
            f = freqs[seg]
            t_seg = t % 0.10
            note_env = math.exp(-t_seg * 12.0)
            overall_env = max(0.0, 1.0 - (t / 0.45) ** 1.5)
            tone = math.sin(2 * math.pi * f * t) * 0.6 + math.sin(2 * math.pi * f * 2 * t) * 0.2
            samples.append(tone * note_env * overall_env * 0.35)
        return self._make_sound(samples)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.stop_all()
        return self.muted

    def play_sonic_boom(self):
        """Toca o estrondo sônico ao ultrapassar Mach 1.0."""
        if self.enabled and not self.muted:
            self.snd_boom_sonic.play()

    def play_engine(self, active, altitude=0.0):
        """Atualiza o som do motor com atenuação física no vácuo aeroespacial (Melhoria 5)."""
        if not self.enabled or self.muted:
            if self.engine_channel is not None:
                self.engine_channel.stop()
                self.engine_channel = None
            return
        if active:
            # Conforme o foguete sobe e a atmosfera se rarefaz, o som não se propaga no vácuo;
            # o volume é atenuado suavemente para uma vibração abafada na fuselagem.
            alt_ratio = min(1.0, max(0.0, altitude / TARGET_ALTITUDE))
            vol = 0.13 * (1.0 - 0.73 * (alt_ratio ** 1.25))

            if self.engine_channel is None or not self.engine_channel.get_busy():
                self.engine_channel = self.snd_engine.play(loops=-1)
            if self.engine_channel is not None:
                self.engine_channel.set_volume(max(0.035, vol))
        else:
            if self.engine_channel is not None:
                self.engine_channel.stop()
                self.engine_channel = None

    def _generate_victory(self):
        """Gera um som triunfante de fanfarra para a vitória."""
        n = int(self.sample_rate * 1.6)
        samples = []
        melody = [
            (0.00, 0.18, 523.25),   # Dó
            (0.18, 0.36, 659.25),   # Mi
            (0.36, 0.54, 783.99),   # Sol
            (0.54, 0.85, 1046.50),  # Dó agudo
            (0.85, 1.60, [1046.50, 1318.51]), # Acorde triunfante final (Dó + Mi)
        ]
        for i in range(n):
            t = i / self.sample_rate
            val = 0.0
            for start, end, note in melody:
                if start <= t < end:
                    dt_note = t - start
                    dur = end - start
                    env = max(0.0, 1.0 - (dt_note / dur)) * min(1.0, dt_note * 60.0)
                    if isinstance(note, list):
                        for f in note:
                            val += (math.sin(2 * math.pi * f * t) * 0.4 + math.sin(4 * math.pi * f * t) * 0.15) * env
                    else:
                        val += (math.sin(2 * math.pi * note * t) * 0.5 + math.sin(4 * math.pi * note * t) * 0.2) * env
                    break
            samples.append(max(-1.0, min(1.0, val * 0.4)))
        return self._make_sound(samples)

    def play_explosion(self):
        if self.enabled and not self.muted:
            self.snd_boom.play()

    def play_refuel(self):
        if self.enabled and not self.muted:
            self.snd_refuel.play()

    def play_victory(self):
        if self.enabled and not self.muted:
            self.snd_victory.play()

    def _generate_ui_blip(self):
        """Gera um som sutil e agradável de clique/navegação de interface."""
        n = int(self.sample_rate * 0.05)
        samples = []
        freq = 720.0
        for i in range(n):
            t = i / self.sample_rate
            env = math.exp(-t * 90.0)
            samples.append(math.sin(2 * math.pi * freq * t) * env * 0.25)
        return self._make_sound(samples)

    def play_ui_blip(self):
        if self.enabled and not self.muted:
            try:
                self.snd_blip.play()
            except Exception:
                pass

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
# Cápsula de Combustível — Objeto coletável no ar/espaço ("No Meio do Caminho")
# =============================================================================
class FuelCanister:
    def __init__(self, x, y, amount=20_000.0):
        self.x = x
        self.y = y                         # Posição fixa no ar (parado)
        self.amount = amount                # Quantidade de combustível recarregado (kg)
        self.collected = False
        self.radius = 32.0                 # Raio de colisão ampliado para facilitar a coleta
        self.pulse = random.uniform(0, math.pi * 2)

    def update(self, dt):
        if self.collected:
            return
        self.pulse += dt * 3.0              # Apenas animação de pulso luminoso (posição perfeitamente estática)

    def draw(self, surface, cam_x, cam_y, sw, sh):
        if self.collected:
            return
        sx = (self.x - cam_x) + sw / 2
        sy = sh / 2 - (self.y - cam_y)

        # Desenha se estiver dentro dos limites da tela (com margem de brilho)
        if -90 <= sx <= sw + 90 and -90 <= sy <= sh + 90:
            pulse_factor = (math.sin(self.pulse * 2.0) + 1.0) * 0.5
            glow_r = int(32 + pulse_factor * 8)

            # 1. Halo / Aura brilhante pulsante
            glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (0, 240, 160, int(30 + pulse_factor * 35)),
                               (glow_r + 2, glow_r + 2), glow_r)
            pygame.draw.circle(glow_surf, (80, 255, 210, int(60 + pulse_factor * 40)),
                               (glow_r + 2, glow_r + 2), int(glow_r * 0.6))
            surface.blit(glow_surf, (sx - glow_r - 2, sy - glow_r - 2))

            # 2. Cápsula / Pod metálico de combustível sci-fi
            pod_w, pod_h = 32, 44
            pod_surf = pygame.Surface((pod_w + 10, pod_h + 16), pygame.SRCALPHA)
            pcx = (pod_w + 10) // 2
            pcy = (pod_h + 16) // 2

            # Micro-chama de sustentação / propulsor antigravitacional na base
            flame_h = int(6 + pulse_factor * 6)
            pygame.draw.polygon(pod_surf, (0, 220, 255, 230), [
                (pcx - 5, pcy + 17), (pcx + 5, pcy + 17), (pcx, pcy + 17 + flame_h)
            ])
            pygame.draw.polygon(pod_surf, (255, 255, 255, 240), [
                (pcx - 2, pcy + 17), (pcx + 2, pcy + 17), (pcx, pcy + 17 + flame_h // 2)
            ])

            # Aletas estabilizadoras laterais
            pygame.draw.polygon(pod_surf, (255, 120, 40), [
                (pcx - 12, pcy + 8), (pcx - 18, pcy + 16), (pcx - 12, pcy + 16)
            ])
            pygame.draw.polygon(pod_surf, (255, 120, 40), [
                (pcx + 12, pcy + 8), (pcx + 18, pcy + 16), (pcx + 12, pcy + 16)
            ])

            # Corpo principal (blindagem cinza-titânio)
            body_rect = pygame.Rect(pcx - 12, pcy - 16, 24, 32)
            pygame.draw.rect(pod_surf, (220, 230, 245), body_rect, border_radius=6)
            pygame.draw.rect(pod_surf, (60, 75, 95), body_rect, 2, border_radius=6)

            # Anéis de reforço superior e inferior
            pygame.draw.rect(pod_surf, (45, 55, 75), (pcx - 13, pcy - 15, 26, 5), border_radius=2)
            pygame.draw.rect(pod_surf, (45, 55, 75), (pcx - 13, pcy + 11, 26, 5), border_radius=2)

            # Válvula / conector no topo
            pygame.draw.rect(pod_surf, (255, 190, 40), (pcx - 5, pcy - 20, 10, 5), border_radius=2)

            # Núcleo de combustível verde-esmeralda brilhante (visor transparente)
            core_rect = pygame.Rect(pcx - 8, pcy - 8, 16, 17)
            pygame.draw.rect(pod_surf, (0, 235, 130), core_rect, border_radius=3)
            # Reflexo de vidro no visor
            pygame.draw.line(pod_surf, (220, 255, 240, 220), (pcx - 6, pcy - 6), (pcx - 6, pcy + 6), 2)

            # Ícone estilizado no centro do núcleo
            pygame.draw.line(pod_surf, (255, 255, 255), (pcx, pcy - 4), (pcx, pcy + 4), 2)
            pygame.draw.line(pod_surf, (255, 255, 255), (pcx - 4, pcy), (pcx + 4, pcy), 2)

            surface.blit(pod_surf, (sx - pcx, sy - pcy))


# =============================================================================
# Texto Flutuante de Notificação (+25.000 kg, etc.)
# =============================================================================
class FloatingText:
    def __init__(self, wx, wy, text, color=(0, 255, 170), duration=1.6):
        self.wx = wx
        self.wy = wy
        self.text = text
        self.color = color
        self.duration = duration
        self.life = duration

    def update(self, dt):
        self.wy += 30.0 * dt   # Sobe suavemente
        self.life -= dt

    def draw(self, surface, font, cam_x, cam_y, sw, sh):
        if self.life <= 0:
            return
        sx = (self.wx - cam_x) + sw / 2
        sy = sh / 2 - (self.wy - cam_y)

        if -150 <= sx <= sw + 150 and -50 <= sy <= sh + 50:
            alpha = max(0, min(255, int(255 * (self.life / self.duration))))
            txt_surf = font.render(self.text, True, self.color)
            shadow_surf = font.render(self.text, True, (0, 0, 0))

            surf_w, surf_h = txt_surf.get_width() + 6, txt_surf.get_height() + 6
            combined = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
            combined.blit(shadow_surf, (3, 3))
            combined.blit(txt_surf, (1, 1))
            combined.set_alpha(alpha)

            surface.blit(combined, (sx - surf_w // 2, sy - surf_h // 2))


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
        self.fuel_mass = INITIAL_FUEL_MASS    # Começa com tanque CHEIO (100 ton)
        self.angle = 0.0                    # ângulo do nariz em graus (+ = direita)
        self.is_thrusting = False
        self.alive = True
        self.mach_broken = False            # Rastreador de quebra da barreira do som (Mach 1.0)

    def refuel(self, amount):
        """Recarrega combustível respeitando a capacidade máxima do tanque."""
        old = self.fuel_mass
        self.fuel_mass = min(FUEL_TOTAL_MASS, self.fuel_mass + amount)
        return self.fuel_mass - old

    @property
    def total_mass(self):
        """Massa total = massa seca do foguete (100t) + massa do combustível restante."""
        return ROCKET_DRY_MASS + self.fuel_mass

    @property
    def twr(self):
        """Razão Empuxo / Peso (TWR) atual com o motor ligado."""
        weight = self.total_mass * GRAVITY
        return (self.thrust_force / weight) if weight > 0 else 0.0

    def update(self, keys, particles, sound_manager, floating_texts=None):
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

            # Gera partículas de exaustão com expansão no vácuo (Melhoria 3)
            self._spawn_exhaust(particles)

        self.is_thrusting = thrust_active

        # Atualiza som com atenuação acústica no vácuo espacial (Melhoria 5)
        sound_manager.play_engine(thrust_active, self.y)

        # -----------------------------------------------------------------
        # 4. Integração numérica com Δt = 1/60 s
        # -----------------------------------------------------------------
        self.vx += ax * DT
        self.vy += ay * DT
        self.x += self.vx * DT
        self.y += self.vy * DT

        # -----------------------------------------------------------------
        # 5. Detecção de Barreira do Som (Mach 1.0 = 340 m/s - Melhoria 2)
        # -----------------------------------------------------------------
        spd = math.hypot(self.vx, self.vy)
        mach = spd / SPEED_OF_SOUND
        if mach >= 1.0 and not self.mach_broken:
            self.mach_broken = True
            sound_manager.play_sonic_boom()

            # Anel expansivo de condensação de vapor sônico
            for _ in range(45):
                ang = random.uniform(0, math.pi * 2)
                p_spd = random.uniform(70, 220)
                particles.append(Particle(
                    self.x + math.cos(ang) * 16,
                    self.y + math.sin(ang) * 16,
                    self.vx + math.cos(ang) * p_spd,
                    self.vy + math.sin(ang) * p_spd,
                    (215, 245, 255), life=random.uniform(0.4, 0.85), size=random.uniform(6, 14)
                ))

            if floating_texts is not None:
                floating_texts.append(FloatingText(
                    self.x, self.y + 40, "💥 ESTRONDO SÔNICO! (MACH 1.0)",
                    color=(255, 220, 70), duration=2.2
                ))
        elif mach < 0.85:
            self.mach_broken = False

        # -----------------------------------------------------------------
        # 6. Colisão com o solo → game over
        # -----------------------------------------------------------------
        if self.y <= 0:
            self.y = 0.0
            self.alive = False
            sound_manager.play_engine(False)
            self._spawn_crash(particles)

    def _spawn_exhaust(self, particles):
        """Partículas de chama saindo do bocal (oposto ao nariz).
        Melhoria 3: Expansão da pluma com a altitude (física de bocais no vácuo).
        - No nível do mar / baixa altitude: atmosfera densa comprime o jato (estreito e focado).
        - Em alta altitude / vácuo: gases se expandem em leque aberto (under-expanded plume)
          com emissão óptica variando de chama laranja para plasma azul, ciano e violeta.
        """
        angle_rad = math.radians(self.angle)
        offset = 35.0  # metros do centro ao bocal

        # Posição do bocal no mundo (oposto à direção do nariz)
        ex = self.x - math.sin(angle_rad) * offset
        ey = self.y - math.cos(angle_rad) * offset

        # Fator de rarefação atmosférica / vácuo (0.0 no solo -> 1.0 em 4000m)
        alt_factor = min(1.0, max(0.0, self.y / TARGET_ALTITUDE))

        # Leque de expansão: de ±0.18 rad (solo comprimido) até ±0.80 rad (vácuo amplo)
        spread_max = 0.18 + 0.62 * alt_factor
        particle_count = 5 if alt_factor < 0.55 else 7

        for _ in range(particle_count):
            spread = random.uniform(-spread_max, spread_max)
            a = angle_rad + spread
            spd = random.uniform(80, 220)

            # Velocidade da exaustão: oposta ao nariz + velocidade do foguete
            pvx = self.vx - math.sin(a) * spd + random.uniform(-10, 10)
            pvy = self.vy - math.cos(a) * spd + random.uniform(-10, 10)

            r = random.random()
            if alt_factor < 0.35:
                # Atmosfera densa: fogo clássico (amarelo brilhante, laranja e rubro)
                if r > 0.6:
                    color, sz = (255, 255, 210), random.uniform(5, 9)
                elif r > 0.3:
                    color, sz = (255, 140, 20), random.uniform(7, 12)
                else:
                    color, sz = (240, 50, 20), random.uniform(6, 10)
            elif alt_factor < 0.70:
                # Transição atmosférica: branco luminoso, azul celeste e âmbar
                if r > 0.65:
                    color, sz = (255, 255, 255), random.uniform(6, 11)
                elif r > 0.35:
                    color, sz = (80, 225, 255), random.uniform(7, 13)
                elif r > 0.15:
                    color, sz = (255, 175, 50), random.uniform(6, 11)
                else:
                    color, sz = (195, 120, 255), random.uniform(5, 10)
            else:
                # Vácuo espacial: plasma azul-ciano, violeta e branco estelar
                if r > 0.6:
                    color, sz = (255, 255, 255), random.uniform(7, 13)
                elif r > 0.3:
                    color, sz = (50, 235, 255), random.uniform(9, 16)
                elif r > 0.12:
                    color, sz = (175, 130, 255), random.uniform(8, 15)
                else:
                    color, sz = (255, 205, 90), random.uniform(6, 10)

            particles.append(Particle(
                ex + random.uniform(-3, 3), ey + random.uniform(-3, 3),
                pvx, pvy, color, life=random.uniform(0.2, 0.48), size=sz
            ))

        # Fumaça visível só onde há ar suficiente; dissipa rapidamente no vácuo
        smoke_chance = 0.40 * (1.0 - alt_factor)
        if random.random() < smoke_chance:
            particles.append(Particle(
                ex + random.uniform(-5, 5), ey + random.uniform(-3, 3),
                self.vx + random.uniform(-15, 15),
                self.vy - random.uniform(40, 90),
                (180, 180, 190), life=0.55 * (1.0 - alt_factor * 0.5), size=random.uniform(10, 16)
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

        # 8. Efeitos Supersônicos (Melhoria 2):
        #    Cone de Condensação Prandtl-Glauert e Ondas de Choque Mach
        speed = math.hypot(self.vx, self.vy)
        mach = speed / SPEED_OF_SOUND

        # 8A. Cone de condensação de Prandtl-Glauert (regime transônico: Mach 0.78 a 1.35)
        if 0.78 <= mach <= 1.35:
            pg_intensity = max(0.0, 1.0 - abs(mach - 1.0) / 0.35)
            pg_alpha = int(195 * pg_intensity)
            if pg_alpha > 5:
                pg_surf = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
                # Discoide / envelope de vapor de água condensada na cintura da fuselagem
                pygame.draw.ellipse(pg_surf, (220, 245, 255, pg_alpha),
                                    (cx - 36, cy - 8, 72, 24))
                pygame.draw.ellipse(pg_surf, (255, 255, 255, int(pg_alpha * 0.75)),
                                    (cx - 26, cy - 14, 52, 16))
                canvas.blit(pg_surf, (0, 0))

        # 8B. Ondas de Choque Supersônicas e Diamantes de Choque Mach (Mach > 1.0)
        if mach > 1.0:
            shock_alpha = min(210, int(90 + (mach - 1.0) * 85))
            sin_mu = min(1.0, 1.0 / mach)
            cos_mu = math.sqrt(max(0.0, 1.0 - sin_mu * sin_mu))
            wing_len = 54.0

            shock_surf = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)

            # Linhas oblíquas de choque de Mach saindo do nariz
            nose_x, nose_y = cx, cy - 35
            p_left = (nose_x - wing_len * sin_mu, nose_y + wing_len * cos_mu)
            p_right = (nose_x + wing_len * sin_mu, nose_y + wing_len * cos_mu)
            pygame.draw.line(shock_surf, (170, 235, 255, shock_alpha), (nose_x, nose_y), p_left, 2)
            pygame.draw.line(shock_surf, (170, 235, 255, shock_alpha), (nose_x, nose_y), p_right, 2)

            # Diamantes de Choque Mach no bocal de escape (quando o motor está acelerando)
            if self.is_thrusting:
                for i in range(1, 4):
                    d_y = cy + 36 + i * 13
                    pygame.draw.polygon(shock_surf, (100, 240, 255, min(220, shock_alpha + 15)), [
                        (cx, d_y - 4), (cx + 5, d_y), (cx, d_y + 4), (cx - 5, d_y)
                    ])
                    pygame.draw.circle(shock_surf, (255, 255, 255, 220), (cx, d_y), 2)

            canvas.blit(shock_surf, (0, 0))
        elif speed > 90:
            # Em velocidades subsônicas médias: onda de arrasto suave
            drag_alpha = min(120, int((speed - 90) * 0.8))
            drag_surf = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
            pygame.draw.lines(drag_surf, (180, 230, 255, drag_alpha), False,
                              [(cx - 28, cy + 20), (cx, cy - 38), (cx + 28, cy + 20)], 2)
            canvas.blit(drag_surf, (0, 0))

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
        # Pré-configura o mixer ANTES do pygame.init() para garantir
        # que as configurações de áudio sejam respeitadas (evita reinit silencioso)
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
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
        self.menu_focus = "mode_2"            # Foco do menu: "mode_1", "mode_2", "explanation", "start"
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
        self.sounds.play_engine(False)

        # Rastreamento de estatísticas extras
        self.thrust_time = 0.0
        self.max_mach = 0.0
        self.freefall_count = 0
        self.in_freefall = False

        # Sistema de Combustível no Meio do Caminho
        self.fuel_canisters = []
        self.floating_texts = []
        self.fuel_canisters_collected = 0
        self.total_fuel_recharged = 0.0

        # Geração inicial de combustível com espaçamento progressivo:
        # As cápsulas ficam cada vez mais distantes progressivamente ao longo da subida.
        cur_y = 1150.0
        self.canister_idx = 0
        while cur_y <= TARGET_ALTITUDE + 200.0:
            spread = 20.0 + min(25.0, (cur_y / TARGET_ALTITUDE) * 25.0)
            spawn_x = random.uniform(-spread, spread)
            self.fuel_canisters.append(FuelCanister(spawn_x, cur_y, amount=20_000.0))
            step = self.get_progressive_canister_spacing(cur_y, self.canister_idx)
            cur_y += step
            self.canister_idx += 1
        self.highest_fuel_y = cur_y

        # Vento lateral aleatório
        self.wind_force = 0.0        # Força atual de vento (N), positivo = Leste
        self.wind_target = 0.0       # Alvo suave para transição
        self.wind_timer = 0.0        # Cronômetro para mudar vento
        self.wind_interval = random.uniform(5.0, 12.0)  # Intervalo de mudança (s)

    def get_progressive_canister_spacing(self, current_y, canister_idx):
        """
        Calcula o espaçamento até o próximo combustível, aumentando progressivamente.
        À medida que o foguete sobe e ganha velocidade, as cápsulas ficam cada vez
        mais distantes umas das outras.
        """
        alt_progress = max(0.0, (current_y - 1000.0) / 9000.0)
        if self.selected_mode == "ACADEMICO":
            # Começa em ~230-260m (suporte inicial para o foguete pesado TWR 1.02)
            # e afasta progressivamente a cada cápsula (+65m) e com altitude (+280m)
            base_dist = 230.0 + (canister_idx * 65.0) + (alt_progress * 280.0)
        else:
            # Modo Aeroespacial: começa em ~380m e afasta progressivamente (+80m por cápsula)
            base_dist = 380.0 + (canister_idx * 80.0) + (alt_progress * 300.0)
        jitter = random.uniform(-0.04, 0.04) * base_dist
        return base_dist + jitter

    # -----------------------------------------------------------------
    # Utilitários de renderização
    # -----------------------------------------------------------------
    @staticmethod
    def lerp_color(c1, c2, t):
        t = max(0.0, min(1.0, t))
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

    def draw_background(self, altitude):
        pct = min(1.0, max(0.0, altitude / (TARGET_ALTITUDE * 0.75)))

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

    def draw_fuel_radar(self, cam_x, cam_y):
        """Desenha indicadores sutis nas bordas da tela apontando para cápsulas de combustível próximas."""
        sw = self.screen_w
        sh = self.screen_h
        cx = sw / 2.0
        cy = sh / 2.0

        pad_x = 50.0
        pad_top = 155.0
        pad_bot = 45.0

        for can in self.fuel_canisters:
            if can.collected:
                continue

            sx = (can.x - cam_x) + cx
            sy = cy - (can.y - cam_y)

            # Se já estiver confortavelmente visível na tela, pula o radar
            if pad_x <= sx <= sw - pad_x and pad_top <= sy <= sh - pad_bot:
                continue

            dx = can.x - cam_x
            dy = can.y - cam_y
            dist = math.hypot(dx, dy)

            # Raio de detecção do sensor (2.400m)
            if dist > 2400.0:
                continue

            screen_dx = sx - cx
            screen_dy = sy - cy

            if abs(screen_dx) < 1e-3 and abs(screen_dy) < 1e-3:
                continue

            max_x = (sw / 2.0) - pad_x
            max_y_up = (sh / 2.0) - pad_top
            max_y_down = (sh / 2.0) - pad_bot

            scale_x = abs(max_x / screen_dx) if abs(screen_dx) > 1e-3 else 999999.0
            scale_y = (max_y_up / -screen_dy if screen_dy < 0 else max_y_down / screen_dy) if abs(screen_dy) > 1e-3 else 999999.0

            scale = min(scale_x, scale_y)
            indicator_x = cx + screen_dx * scale
            indicator_y = cy + screen_dy * scale

            ang = math.atan2(screen_dy, screen_dx)

            # Triângulo indicador na direção do combustível
            tip_x = indicator_x + math.cos(ang) * 14
            tip_y = indicator_y + math.sin(ang) * 14
            left_x = indicator_x + math.cos(ang + 2.5) * 11
            left_y = indicator_y + math.sin(ang + 2.5) * 11
            right_x = indicator_x + math.cos(ang - 2.5) * 11
            right_y = indicator_y + math.sin(ang - 2.5) * 11

            poly = [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)]
            pygame.draw.polygon(self.screen, (0, 245, 170), poly)
            pygame.draw.polygon(self.screen, (255, 255, 255), poly, 1)

            # Etiqueta com distância (ex: "⛽ 350m")
            txt = f"⛽ {int(dist)}m"
            lbl = self.font_small.render(txt, True, (215, 255, 235))

            tx = indicator_x - math.cos(ang) * 32
            ty = indicator_y - math.sin(ang) * 32
            txt_rect = lbl.get_rect(center=(int(tx), int(ty)))

            bg_rect = txt_rect.inflate(10, 4)
            s_bg = pygame.Surface((bg_rect.w, bg_rect.h), pygame.SRCALPHA)
            s_bg.fill((12, 24, 20, 215))
            pygame.draw.rect(s_bg, (0, 220, 150, 180), (0, 0, bg_rect.w, bg_rect.h), 1, border_radius=4)
            self.screen.blit(s_bg, bg_rect)
            self.screen.blit(lbl, txt_rect)

    # -----------------------------------------------------------------
    # Alerta Visual de Queda Livre
    # -----------------------------------------------------------------
    def draw_freefall_alert(self):
        """Mostra alerta visual pulsante quando o foguete está em queda livre perigosa (Vy < -20 m/s)."""
        if not self.in_freefall or not self.rocket.alive:
            return

        pulse = (math.sin(self.anim_time * 10) + 1) / 2

        # Borda vermelha pulsante ao redor da tela inteira
        border_alpha = int(70 + 110 * pulse)
        border_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (255, 30, 30, border_alpha),
                         (0, 0, self.screen_w, self.screen_h), 22)
        self.screen.blit(border_surf, (0, 0))

        # Banner central de alerta com texto pulsante
        banner_w, banner_h = 560, 60
        bx = (self.screen_w - banner_w) // 2
        by = self.screen_h // 2 + 68

        bg_alpha = int(190 + 65 * pulse)
        banner_surf = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        banner_surf.fill((150, 0, 0, bg_alpha))
        pygame.draw.rect(banner_surf, (255, 70, 70, 255), (0, 0, banner_w, banner_h), 2, border_radius=10)
        self.screen.blit(banner_surf, (bx, by))

        alert_col = (255, int(190 + 65 * pulse), 50)
        alert_txt = self.font_sub.render(
            f"⚠️  QUEDA LIVRE!   Vy = {self.rocket.vy:+.1f} m/s  ⚠️", True, alert_col)
        self.screen.blit(alert_txt, alert_txt.get_rect(center=(self.screen_w // 2, by + banner_h // 2)))

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

        # Indicador de cápsulas de combustível coletadas no ar
        cans_col = (0, 240, 170) if self.fuel_canisters_collected > 0 else (160, 180, 200)
        lbl_cans = self.font_hud.render(
            f"⛽ RECARGAS: {self.fuel_canisters_collected} (+{int(self.total_fuel_recharged):,} kg)",
            True, cans_col)
        self.screen.blit(lbl_cans, (bx + bar_w + 12, by + 23))

        # Status do Áudio e Atalho de Explicação
        audio_txt = "[M] ÁUDIO: MUDO" if self.sounds.muted else "[M] ÁUDIO: ATIVO"
        audio_color = (255, 120, 120) if self.sounds.muted else (130, 220, 160)
        lbl_audio = self.font_small.render(audio_txt, True, audio_color)
        self.screen.blit(lbl_audio, (30, 92))

        lbl_help_hud = self.font_small.render(
            "[E] VER EXPLICAÇÃO FÍSICA DOS MODOS", True, (0, 230, 255))
        self.screen.blit(lbl_help_hud, (30, 114))

        # ---- Altitude, Meta de Vitória e Velocidade ----
        col2 = self.screen_w // 2 - 130
        lbl_alt = self.font_hud.render(
            f"ALTITUDE: {self.rocket.y:.1f} m  |  META: {TARGET_ALTITUDE:.0f} m",
            True, (200, 230, 255))
        self.screen.blit(lbl_alt, (col2, 60))

        # Barra de progresso para alcançar a órbita / vitória
        progress_pct = max(0.0, min(1.0, (self.rocket.y - INITIAL_ALTITUDE) / (TARGET_ALTITUDE - INITIAL_ALTITUDE)))
        bar_w_meta = 240
        pygame.draw.rect(self.screen, (30, 40, 55), (col2, 80, bar_w_meta, 5), border_radius=3)
        pygame.draw.rect(self.screen, (0, 235, 220), (col2, 80, int(bar_w_meta * progress_pct), 5), border_radius=3)
        pygame.draw.rect(self.screen, (70, 110, 160), (col2, 80, bar_w_meta, 5), 1, border_radius=3)

        spd = math.hypot(self.rocket.vx, self.rocket.vy)
        mach = spd / SPEED_OF_SOUND
        if mach >= 1.0:
            mach_str = f"Mach {mach:.2f} (SUPERSÔNICO)"
            mach_col = (255, 120, 60)
        elif mach >= 0.8:
            mach_str = f"Mach {mach:.2f} (TRANSÔNICO)"
            mach_col = (255, 215, 60)
        else:
            mach_str = f"Mach {mach:.2f}"
            mach_col = (195, 225, 255)

        lbl_vel = self.font_hud.render(
            f"VEL: {spd:.1f} m/s ({mach_str})   Vy={self.rocket.vy:+.1f}   Vx={self.rocket.vx:+.1f}",
            True, mach_col if mach >= 0.8 else (200, 220, 255))
        self.screen.blit(lbl_vel, (col2, 90))

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

        # Indicador de estado acústico aeroespacial (Melhoria 5)
        alt_pct = min(1.0, max(0.0, self.rocket.y / TARGET_ALTITUDE))
        if alt_pct > 0.70:
            atmos_txt = "ACÚSTICA: VÁCUO (Som Abafado na Fuselagem)"
            atmos_col = (130, 205, 255)
        elif alt_pct > 0.35:
            atmos_txt = f"ACÚSTICA: Rarefação Atmosférica ({int((1.0 - alt_pct) * 100)}%)"
            atmos_col = (170, 235, 220)
        else:
            atmos_txt = "ACÚSTICA: Atmosfera Densa (Som Pleno)"
            atmos_col = (160, 210, 190)
        lbl_atmos = self.font_small.render(atmos_txt, True, atmos_col)
        self.screen.blit(lbl_atmos, (col2 + 250, 114))

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

        # Indicador de vento lateral
        wind_kn = self.wind_force / 1000.0
        if abs(self.wind_force) < 4_000.0:
            wind_str = "VENTO: — CALMO"
            wind_col = (150, 200, 155)
        elif self.wind_force > 0:
            strength = "FORTE" if self.wind_force > 28_000 else "MODERADO"
            wind_str = f"VENTO: → {wind_kn:.1f} kN (Leste, {strength})"
            wind_col = (255, 195, 70) if self.wind_force > 28_000 else (190, 235, 170)
        else:
            strength = "FORTE" if self.wind_force < -28_000 else "MODERADO"
            wind_str = f"VENTO: ← {abs(wind_kn):.1f} kN (Oeste, {strength})"
            wind_col = (255, 195, 70) if self.wind_force < -28_000 else (190, 235, 170)
        lbl_wind = self.font_small.render(wind_str, True, wind_col)
        self.screen.blit(lbl_wind, (col3, 90))

        lbl_g = self.font_small.render(
            f"g = {GRAVITY} m/s²   |   Δt = 1/{FPS}s",
            True, (120, 145, 180))
        self.screen.blit(lbl_g, (col3, 108))

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

        pulse = (math.sin(self.anim_time * 6) + 1) / 2

        # Título
        t = self.font_title.render("FOGUETE — Simulador Físico", True, (255, 215, 60))
        self.screen.blit(t, t.get_rect(center=(self.screen_w // 2, by + 36)))

        sub = self.font_sub.render("SELECIONE O MODO DE SIMULAÇÃO:", True, (220, 235, 255))
        self.screen.blit(sub, sub.get_rect(center=(self.screen_w // 2, by + 74)))

        # Cards dos Modos
        card_w = (pw - 60) // 2
        card_h = 240
        card_y = by + 102

        # --- Card 1: Modo Acadêmico ---
        c1_x = bx + 22
        is_m1 = (self.selected_mode == "ACADEMICO")
        is_foc_m1 = (self.menu_focus == "mode_1")
        c1_bg = (38, 26, 20, 245) if is_m1 else (20, 25, 35, 180)
        c1_border = (255, 175, 55) if is_m1 else (65, 80, 105)
        c1_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        c1_surf.fill(c1_bg)
        pygame.draw.rect(c1_surf, c1_border, (0, 0, card_w, card_h), 3 if is_m1 else 1, border_radius=12)
        self.screen.blit(c1_surf, (c1_x, card_y))
        self.btn_rects["mode_1"] = pygame.Rect(c1_x, card_y, card_w, card_h)

        # Glow pulsante quando Card 1 está em foco nas setas
        if is_foc_m1:
            glow_surf1 = pygame.Surface((card_w + 14, card_h + 14), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf1, (255, 195, 60, int(80 + 90 * pulse)),
                             (0, 0, card_w + 14, card_h + 14), 3, border_radius=15)
            self.screen.blit(glow_surf1, (c1_x - 7, card_y - 7))

        status_m1 = "◄ SELECIONADO ►" if is_m1 else "[ TECLA 1 ]"
        t1 = self.font_hud.render(f"MODO 1: ACADÊMICO", True, (255, 180, 65) if is_m1 else (190, 190, 200))
        self.screen.blit(t1, (c1_x + 16, card_y + 14))

        status_tag1 = self.font_small.render(
            status_m1, True, (255, 215, 80) if is_foc_m1 else ((255, 160, 50) if is_m1 else (140, 150, 170)))
        self.screen.blit(status_tag1, (c1_x + card_w - status_tag1.get_width() - 16, card_y + 16))

        sub1 = self.font_small.render("Requisitos Estritos da Atividade  [ ← SETA ESQ ]", True, (200, 215, 230) if is_m1 else (150, 160, 175))
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
        is_foc_m2 = (self.menu_focus == "mode_2")
        c2_bg = (18, 40, 32, 245) if is_m2 else (20, 25, 35, 180)
        c2_border = (45, 235, 165) if is_m2 else (65, 80, 105)
        c2_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        c2_surf.fill(c2_bg)
        pygame.draw.rect(c2_surf, c2_border, (0, 0, card_w, card_h), 3 if is_m2 else 1, border_radius=12)
        self.screen.blit(c2_surf, (c2_x, card_y))
        self.btn_rects["mode_2"] = pygame.Rect(c2_x, card_y, card_w, card_h)

        # Glow pulsante quando Card 2 está em foco nas setas
        if is_foc_m2:
            glow_surf2 = pygame.Surface((card_w + 14, card_h + 14), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf2, (60, 255, 180, int(80 + 90 * pulse)),
                             (0, 0, card_w + 14, card_h + 14), 3, border_radius=15)
            self.screen.blit(glow_surf2, (c2_x - 7, card_y - 7))

        status_m2 = "◄ SELECIONADO ►" if is_m2 else "[ TECLA 2 ]"
        t2 = self.font_hud.render(f"MODO 2: AEROESPACIAL", True, (55, 245, 175) if is_m2 else (190, 190, 200))
        self.screen.blit(t2, (c2_x + 16, card_y + 14))

        status_tag2 = self.font_small.render(
            status_m2, True, (100, 255, 200) if is_foc_m2 else ((45, 230, 160) if is_m2 else (140, 150, 170)))
        self.screen.blit(status_tag2, (c2_x + card_w - status_tag2.get_width() - 16, card_y + 16))

        sub2 = self.font_small.render("Opção 1 — Realista & Jogável  [ SETA DIR → ]", True, (200, 240, 230) if is_m2 else (150, 160, 175))
        self.screen.blit(sub2, (c2_x + 16, card_y + 38))

        specs_m2 = [
            "• Empuxo: 3,5 × 10⁶ N (Alta Potência)",
            "• Razão Empuxo/Peso (TWR): 1,79",
            "• Aceleração inicial: 7,70 m/s² (atinge 25,2 m/s²)",
            "• Rotação: Gimbal suave contínuo (55°/s)",
            "• Comportamento: Decolagem fulminante e",
            "  velocidades supersônicas (Mach 1+).",
        ]
        for idx, sp in enumerate(specs_m2):
            lbl_sp = self.font_small.render(sp, True, (210, 240, 230) if idx < 4 else (120, 255, 180))
            self.screen.blit(lbl_sp, (c2_x + 16, card_y + 65 + idx * 24))

        # Dica de navegação por setas do teclado
        hint_mode = self.font_hud.render(
            "🎮 Navegue com as SETAS [ ← → ↑ ↓ ]   •   Pressione [ ENTER ] ou [ ESPAÇO ] para confirmar",
            True, (255, 220, 85))
        self.screen.blit(hint_mode, hint_mode.get_rect(center=(self.screen_w // 2, card_y + card_h + 18)))

        # Botão de Explicação Física Completa
        btn_exp_w, btn_exp_h = 600, 44
        btn_exp_x = (self.screen_w - btn_exp_w) // 2
        btn_exp_y = card_y + card_h + 40
        self.btn_rects["explanation"] = pygame.Rect(btn_exp_x, btn_exp_y, btn_exp_w, btn_exp_h)
        is_foc_exp = (self.menu_focus == "explanation")

        if is_foc_exp:
            glow_exp = pygame.Surface((btn_exp_w + 10, btn_exp_h + 10), pygame.SRCALPHA)
            pygame.draw.rect(glow_exp, (0, 220, 255, int(90 + 90 * pulse)), (0, 0, btn_exp_w + 10, btn_exp_h + 10), 3, border_radius=12)
            self.screen.blit(glow_exp, (btn_exp_x - 5, btn_exp_y - 5))
            pygame.draw.rect(self.screen, (25, 60, 105), self.btn_rects["explanation"], border_radius=8)
            pygame.draw.rect(self.screen, (100, 240, 255), self.btn_rects["explanation"], 2, border_radius=8)
            exp_txt = self.font_hud.render(
                "►  🔬  [ ENTER / E ] LER EXPLICAÇÃO FÍSICA DETALHADA DOS MODOS  ◄", True, (220, 255, 255))
        else:
            pygame.draw.rect(self.screen, (22, 38, 65), self.btn_rects["explanation"], border_radius=8)
            pygame.draw.rect(self.screen, (0, 190, 240), self.btn_rects["explanation"], 2, border_radius=8)
            exp_txt = self.font_hud.render(
                "🔬 [ E ] LER EXPLICAÇÃO FÍSICA DETALHADA DOS MODOS", True, (0, 220, 255))
        self.screen.blit(exp_txt, exp_txt.get_rect(center=self.btn_rects["explanation"].center))

        # Dica resumida de controles do foguete durante o voo
        ctrl_txt = self.font_small.render(
            "Em voo: [ ESPAÇO ] Propulsão   |   [ ← → ] ou [ A D ] Manobrar   |   [ ⛽ ] Colete combustível no ar",
            True, (160, 185, 215))
        self.screen.blit(ctrl_txt, ctrl_txt.get_rect(center=(self.screen_w // 2, by + ph - 74)))

        # Botão interativo para Começar / Decolar
        btn_start_w, btn_start_h = 620, 48
        btn_start_x = (self.screen_w - btn_start_w) // 2
        btn_start_y = by + ph - 52
        self.btn_rects["start"] = pygame.Rect(btn_start_x, btn_start_y, btn_start_w, btn_start_h)
        is_foc_start = (self.menu_focus == "start")

        if is_foc_start:
            glow_start = pygame.Surface((btn_start_w + 10, btn_start_h + 10), pygame.SRCALPHA)
            pygame.draw.rect(glow_start, (255, 220, 60, int(90 + 90 * pulse)), (0, 0, btn_start_w + 10, btn_start_h + 10), 3, border_radius=14)
            self.screen.blit(glow_start, (btn_start_x - 5, btn_start_y - 5))
            pygame.draw.rect(self.screen, (55, 45, 15), self.btn_rects["start"], border_radius=10)
            pygame.draw.rect(self.screen, (255, 225, 70), self.btn_rects["start"], 2, border_radius=10)
            s = self.font_sub.render(
                f"►  🚀 PRESSIONE [ ENTER / ESPAÇO ] PARA DECOLAR NO {self.selected_mode}  ◄",
                True, (255, 235, 90))
        else:
            bc = (int(255 * (0.8 + 0.2 * pulse)), int(185 * (0.8 + 0.2 * pulse)), 40)
            pygame.draw.rect(self.screen, (20, 32, 28), self.btn_rects["start"], border_radius=10)
            pygame.draw.rect(self.screen, (70, 120, 95), self.btn_rects["start"], 1, border_radius=10)
            s = self.font_sub.render(
                f"🚀 PRESSIONE [ ESPAÇO ] PARA DECOLAR NO {self.selected_mode}", True, bc)
        self.screen.blit(s, s.get_rect(center=self.btn_rects["start"].center))

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

        pw, ph = 700, 575
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
            f"Cápsulas Coletadas no Ar: {self.fuel_canisters_collected} (+{int(self.total_fuel_recharged):,} kg recarregados)",
        ]
        for i, txt in enumerate(stats):
            s = self.font_hud.render(txt, True, (230, 235, 245))
            self.screen.blit(s, (px + 50, py + 175 + i * 27))

        # Separador e estatísticas extras detalhadas
        sep_y = py + 175 + 4 * 27 + 8
        pygame.draw.line(self.screen, (110, 45, 45), (px + 24, sep_y), (px + pw - 24, sep_y), 1)
        lbl_extra_hdr = self.font_small.render("— Estatísticas Detalhadas —", True, (200, 140, 140))
        self.screen.blit(lbl_extra_hdr, lbl_extra_hdr.get_rect(center=(self.screen_w // 2, sep_y + 11)))

        efficiency = (self.thrust_time / self.score * 100) if self.score > 0 else 0.0
        extra_stats = [
            (f"⏱  Motor ligado: {self.thrust_time:.1f}s de {self.score:.1f}s  ({efficiency:.0f}% do tempo)",
             (180, 230, 255)),
            (f"🚀  Mach máximo: {self.max_mach:.3f}" +
             (" (SUPERSÔNICO! 💥)" if self.max_mach >= 1.0 else " (Subsônico)"),
             (255, 200, 80) if self.max_mach >= 1.0 else (190, 215, 245)),
            (f"📉  Entradas em queda livre (Vy < −20 m/s): {self.freefall_count}×",
             (255, 130, 130) if self.freefall_count > 0 else (150, 215, 175)),
        ]
        for i, (txt, col) in enumerate(extra_stats):
            s = self.font_small.render(txt, True, col)
            self.screen.blit(s, (px + 50, sep_y + 26 + i * 24))

        # Dica física caso tenha caído no modo acadêmico
        if self.rocket.mode == "ACADEMICO":
            tip_fail = self.font_small.render(
                "* No Modo Acadêmico (TWR 1,02), qualquer inclinação de 30° faz o foguete perder sustentação e cair.",
                True, (255, 170, 130))
            self.screen.blit(tip_fail, (px + 20, sep_y + 26 + 3 * 24 + 6))

        # Atalhos
        r1 = self.font_sub.render(
            "[ R ] ou [ ESPAÇO ]: Jogar Novamente", True, (255, 220, 80))
        self.screen.blit(r1, r1.get_rect(center=(self.screen_w // 2, py + 490)))

        r2 = self.font_small.render(
            "[ 1 ] Modo Acadêmico   |   [ 2 ] Modo Aeroespacial   |   [ E ] Ver Explicação Física   |   [ ESC ] Sair",
            True, (200, 230, 255))
        self.screen.blit(r2, r2.get_rect(center=(self.screen_w // 2, py + 536)))

    # -----------------------------------------------------------------
    # Tela de Vitória (Missão Cumprida — Órbita Atingida)
    # -----------------------------------------------------------------
    def draw_victory(self):
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((4, 18, 28, 235))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 760, 615
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((12, 24, 38, 250))
        pygame.draw.rect(panel, (0, 230, 170), (0, 0, pw, ph), 3, border_radius=18)
        px = (self.screen_w - pw) // 2
        py = (self.screen_h - ph) // 2
        self.screen.blit(panel, (px, py))

        # Título triunfante com animação suave
        pulse = (math.sin(self.anim_time * 5) + 1) / 2
        t_col = (255, int(210 + 45 * pulse), 50)
        t = self.font_title.render("🏆 VITÓRIA! MISSÃO CUMPRIDA! 🏆", True, t_col)
        self.screen.blit(t, t.get_rect(center=(self.screen_w // 2, py + 42)))

        sub = self.font_sub.render(
            f"O foguete superou a atmosfera e alcançou o espaço ({TARGET_ALTITUDE:.0f} m)!",
            True, (140, 235, 255))
        self.screen.blit(sub, sub.get_rect(center=(self.screen_w // 2, py + 84)))

        # Score final
        score_s = self.font_score.render(
            f"TEMPO FINAL: {self.score:.2f} s", True, (255, 220, 60))
        self.screen.blit(score_s, score_s.get_rect(center=(self.screen_w // 2, py + 132)))

        mode_cfg = GAME_MODES[self.rocket.mode]
        lbl_mod = self.font_hud.render(
            f"Modo Conquistado: {mode_cfg['title']} ({mode_cfg['subtitle']})", True, mode_cfg["badge_color"])
        self.screen.blit(lbl_mod, lbl_mod.get_rect(center=(self.screen_w // 2, py + 176)))

        # Estatísticas da missão
        stats = [
            f"Altitude Atingida: {self.rocket.y:.1f} m (Meta de {TARGET_ALTITUDE:.0f} m superada!)",
            f"Velocidade Máxima: {self.max_speed:.1f} m/s ({self.max_speed * 3.6:.1f} km/h)",
            f"Combustível Restante no Tanque: {self.rocket.fuel_mass:.0f} kg ({self.rocket.fuel_mass / FUEL_TOTAL_MASS * 100:.1f}%)",
            f"Cápsulas Coletadas no Caminho: {self.fuel_canisters_collected} (+{int(self.total_fuel_recharged):,} kg de recarga)",
        ]
        for i, txt in enumerate(stats):
            s = self.font_hud.render(txt, True, (230, 245, 255))
            self.screen.blit(s, (px + 50, py + 210 + i * 29))

        # Separador e estatísticas extras detalhadas
        sep_y = py + 210 + 4 * 29 + 10
        pygame.draw.line(self.screen, (0, 100, 80), (px + 24, sep_y), (px + pw - 24, sep_y), 1)
        lbl_extra_hdr = self.font_small.render("— Estatísticas Detalhadas da Missão —", True, (90, 210, 175))
        self.screen.blit(lbl_extra_hdr, lbl_extra_hdr.get_rect(center=(self.screen_w // 2, sep_y + 11)))

        efficiency = (self.thrust_time / self.score * 100) if self.score > 0 else 0.0
        extra_stats = [
            (f"⏱  Motor ligado: {self.thrust_time:.1f}s de {self.score:.1f}s  ({efficiency:.0f}% do tempo)",
             (180, 235, 255)),
            (f"🚀  Mach máximo: {self.max_mach:.3f}" +
             (" (SUPERSÔNICO! 💥)" if self.max_mach >= 1.0 else " (Subsônico)"),
             (255, 220, 80) if self.max_mach >= 1.0 else (190, 220, 245)),
            (f"📉  Entradas em queda livre (Vy < −20 m/s): {self.freefall_count}×",
             (255, 170, 170) if self.freefall_count > 3 else (130, 245, 190)),
        ]
        for i, (txt, col) in enumerate(extra_stats):
            s = self.font_small.render(txt, True, col)
            self.screen.blit(s, (px + 50, sep_y + 26 + i * 24))

        # Destaque de honra
        lbl_praise = self.font_small.render(
            "★ Parabéns! Excelente pilotagem newtoniana e gerenciamento de energia! ★",
            True, (0, 255, 180))
        self.screen.blit(lbl_praise, lbl_praise.get_rect(center=(self.screen_w // 2, sep_y + 26 + 3 * 24 + 16)))

        # Botão principal de ação
        bc = (int(255 * (0.8 + 0.2 * pulse)), int(220 * (0.8 + 0.2 * pulse)), 70)
        r1 = self.font_sub.render("[ ESPAÇO ] ou [ R ]: Jogar Novamente", True, bc)
        self.screen.blit(r1, r1.get_rect(center=(self.screen_w // 2, py + 534)))

        r2 = self.font_small.render(
            "[ 1 ] Modo Acadêmico   |   [ 2 ] Modo Aeroespacial   |   [ E ] Ver Explicação Física   |   [ ESC ] Sair",
            True, (180, 210, 240))
        self.screen.blit(r2, r2.get_rect(center=(self.screen_w // 2, py + 578)))

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

                elif event.type == pygame.MOUSEMOTION:
                    mpos = event.pos
                    if self.state == "MENU":
                        if "mode_1" in self.btn_rects and self.btn_rects["mode_1"].collidepoint(mpos):
                            self.menu_focus = "mode_1"
                        elif "mode_2" in self.btn_rects and self.btn_rects["mode_2"].collidepoint(mpos):
                            self.menu_focus = "mode_2"
                        elif "explanation" in self.btn_rects and self.btn_rects["explanation"].collidepoint(mpos):
                            self.menu_focus = "explanation"
                        elif "start" in self.btn_rects and self.btn_rects["start"].collidepoint(mpos):
                            self.menu_focus = "start"

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mpos = event.pos
                    if self.state == "MENU":
                        if "mode_1" in self.btn_rects and self.btn_rects["mode_1"].collidepoint(mpos):
                            self.selected_mode = "ACADEMICO"
                            self.menu_focus = "mode_1"
                            self.sounds.play_ui_blip()
                        elif "mode_2" in self.btn_rects and self.btn_rects["mode_2"].collidepoint(mpos):
                            self.selected_mode = "AEROESPACIAL"
                            self.menu_focus = "mode_2"
                            self.sounds.play_ui_blip()
                        elif "explanation" in self.btn_rects and self.btn_rects["explanation"].collidepoint(mpos):
                            self.menu_focus = "explanation"
                            self.previous_state = self.state
                            self.state = "EXPLANATION"
                            self.sounds.play_ui_blip()
                        elif "start" in self.btn_rects and self.btn_rects["start"].collidepoint(mpos):
                            self.sounds.play_ui_blip()
                            self.reset_game()
                            self.state = "PLAYING"

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
                        self.sounds.play_ui_blip()

                    # Teclas para selecionar os Modos
                    elif event.key in (pygame.K_1, pygame.K_KP1):
                        self.selected_mode = "ACADEMICO"
                        self.menu_focus = "mode_1"
                        self.sounds.play_ui_blip()
                        if self.state in ("PLAYING", "GAMEOVER", "VICTORY"):
                            self.reset_game()
                            self.state = "PLAYING"

                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        self.selected_mode = "AEROESPACIAL"
                        self.menu_focus = "mode_2"
                        self.sounds.play_ui_blip()
                        if self.state in ("PLAYING", "GAMEOVER", "VICTORY"):
                            self.reset_game()
                            self.state = "PLAYING"

                    elif event.key == pygame.K_TAB:
                        self.selected_mode = "AEROESPACIAL" if self.selected_mode == "ACADEMICO" else "ACADEMICO"
                        self.menu_focus = "mode_2" if self.selected_mode == "AEROESPACIAL" else "mode_1"
                        self.sounds.play_ui_blip()
                        if self.state in ("PLAYING", "GAMEOVER", "VICTORY"):
                            self.reset_game()
                            self.state = "PLAYING"

                    # Navegação por estados e controle do menu pelas setas
                    elif self.state == "MENU":
                        if event.key in (pygame.K_UP, pygame.K_w):
                            self.sounds.play_ui_blip()
                            if self.menu_focus in ("mode_1", "mode_2"):
                                self.menu_focus = "start"
                            elif self.menu_focus == "explanation":
                                self.menu_focus = "mode_1" if self.selected_mode == "ACADEMICO" else "mode_2"
                            elif self.menu_focus == "start":
                                self.menu_focus = "explanation"
                            else:
                                self.menu_focus = "mode_2"

                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            self.sounds.play_ui_blip()
                            if self.menu_focus in ("mode_1", "mode_2"):
                                self.menu_focus = "explanation"
                            elif self.menu_focus == "explanation":
                                self.menu_focus = "start"
                            elif self.menu_focus == "start":
                                self.menu_focus = "mode_1" if self.selected_mode == "ACADEMICO" else "mode_2"
                            else:
                                self.menu_focus = "explanation"

                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            self.sounds.play_ui_blip()
                            self.selected_mode = "ACADEMICO"
                            if self.menu_focus in ("mode_1", "mode_2"):
                                self.menu_focus = "mode_1"

                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            self.sounds.play_ui_blip()
                            self.selected_mode = "AEROESPACIAL"
                            if self.menu_focus in ("mode_1", "mode_2"):
                                self.menu_focus = "mode_2"

                        elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                            if self.menu_focus == "explanation":
                                self.previous_state = self.state
                                self.state = "EXPLANATION"
                                self.sounds.play_ui_blip()
                            else:
                                self.sounds.play_ui_blip()
                                self.reset_game()
                                self.state = "PLAYING"

                    elif self.state in ("GAMEOVER", "VICTORY"):
                        if event.key in (pygame.K_LEFT, pygame.K_a):
                            self.selected_mode = "ACADEMICO"
                            self.menu_focus = "mode_1"
                            self.sounds.play_ui_blip()
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            self.selected_mode = "AEROESPACIAL"
                            self.menu_focus = "mode_2"
                            self.sounds.play_ui_blip()
                        elif event.key in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN):
                            self.reset_game()
                            self.state = "PLAYING"

                    elif self.state == "EXPLANATION":
                        if event.key in (pygame.K_LEFT, pygame.K_a):
                            self.selected_mode = "ACADEMICO"
                            self.menu_focus = "mode_1"
                            self.sounds.play_ui_blip()
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            self.selected_mode = "AEROESPACIAL"
                            self.menu_focus = "mode_2"
                            self.sounds.play_ui_blip()
                        elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                            if self.previous_state == "PLAYING":
                                self.reset_game()
                            self.state = self.previous_state if self.previous_state not in ("GAMEOVER", "VICTORY") else "PLAYING"

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

                # Atualiza o foguete (física principal com o modo selecionado e efeitos sônicos)
                self.rocket.update(keys, self.particles, self.sounds, floating_texts=self.floating_texts)

                # --- Vento lateral aleatório ---
                self.wind_timer += DT
                if self.wind_timer >= self.wind_interval:
                    self.wind_timer = 0.0
                    self.wind_interval = random.uniform(5.0, 12.0)
                    max_wind = 45_000.0  # N — força máxima do vento
                    self.wind_target = random.uniform(-max_wind, max_wind)
                # Transição suave (efeito ráfaga natural)
                self.wind_force += (self.wind_target - self.wind_force) * 0.018
                # Aplica vento ao foguete — diminui com altitude (atmosfera rarefeita)
                if self.rocket.alive:
                    atmos_w = max(0.0, 1.0 - self.rocket.y / 7500.0)
                    wind_accel = (self.wind_force * atmos_w) / max(1.0, self.rocket.total_mass)
                    self.rocket.vx += wind_accel * DT

                # Estatísticas
                if self.rocket.y > self.max_altitude:
                    self.max_altitude = self.rocket.y
                spd = math.hypot(self.rocket.vx, self.rocket.vy)
                if spd > self.max_speed:
                    self.max_speed = spd

                # Rastreamento de Mach máximo, tempo de empuxo e queda livre
                mach_cur = spd / SPEED_OF_SOUND
                if mach_cur > self.max_mach:
                    self.max_mach = mach_cur
                if self.rocket.is_thrusting:
                    self.thrust_time += DT
                was_freefall = self.in_freefall
                self.in_freefall = (self.rocket.vy < -20.0 and self.rocket.alive)
                if self.in_freefall and not was_freefall:
                    self.freefall_count += 1

                # Atualiza textos flutuantes
                for ft in self.floating_texts:
                    ft.update(DT)
                self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

                # Geração procedural com espaçamento progressivo contínuo
                while self.highest_fuel_y < min(TARGET_ALTITUDE + 200.0, self.rocket.y + 2000):
                    step = self.get_progressive_canister_spacing(self.highest_fuel_y, self.canister_idx)
                    self.highest_fuel_y += step
                    spread = 20.0 + min(25.0, (self.highest_fuel_y / TARGET_ALTITUDE) * 25.0)
                    spawn_x = self.rocket.x + random.uniform(-spread, spread)
                    self.fuel_canisters.append(FuelCanister(spawn_x, self.highest_fuel_y, amount=20_000.0))
                    self.canister_idx += 1

                # Atualiza cápsulas e testa colisão com o foguete
                for can in self.fuel_canisters:
                    if can.collected:
                        continue
                    can.update(DT)

                    # Distância entre o foguete e a cápsula de combustível
                    dx = self.rocket.x - can.x
                    dy = self.rocket.y - can.y
                    dist = math.hypot(dx, dy)

                    # Colisão facilitada (raio de 68m para captura confortável)
                    if dist <= 68.0 and self.rocket.alive:
                        can.collected = True
                        added = self.rocket.refuel(can.amount)
                        self.fuel_canisters_collected += 1
                        self.total_fuel_recharged += added
                        self.sounds.play_refuel()

                        # Partículas cintilantes de coleta
                        for _ in range(35):
                            ang = random.uniform(0, math.pi * 2)
                            p_spd = random.uniform(50, 200)
                            p_col = random.choice([
                                (0, 255, 170), (50, 240, 255), (255, 230, 80), (255, 255, 255)
                            ])
                            self.particles.append(Particle(
                                can.x + random.uniform(-6, 6),
                                can.y + random.uniform(-6, 6),
                                math.cos(ang) * p_spd,
                                math.sin(ang) * p_spd,
                                p_col, life=random.uniform(0.5, 1.1), size=random.uniform(4, 9)
                            ))

                        # Mensagem flutuante
                        if added > 0:
                            msg = f"+{int(added):,} kg COMBUSTÍVEL!"
                        else:
                            msg = "TANQUE CHEIO! (+100%)"
                        self.floating_texts.append(FloatingText(
                            can.x, can.y + 20, msg, color=(0, 255, 180)
                        ))

                # Limpeza de cápsulas coletadas que já ficaram muito para trás
                self.fuel_canisters = [
                    c for c in self.fuel_canisters
                    if not (c.collected and c.y < self.rocket.y - 1200) and c.y > -500
                ]

                # Vitória: atingiu a altitude alvo (órbita / espaço)!
                if self.rocket.y >= TARGET_ALTITUDE:
                    self.state = "VICTORY"
                    self.sounds.play_engine(False)
                    self.sounds.play_victory()
                    # Confetes comemorativos
                    for _ in range(120):
                        ang = random.uniform(0, math.pi * 2)
                        p_spd = random.uniform(80, 320)
                        p_col = random.choice([
                            (255, 215, 0), (0, 245, 180), (255, 100, 200),
                            (100, 220, 255), (255, 255, 255), (255, 180, 50)
                        ])
                        self.particles.append(Particle(
                            self.rocket.x + random.uniform(-30, 30),
                            self.rocket.y + random.uniform(-30, 30),
                            math.cos(ang) * p_spd,
                            math.sin(ang) * p_spd,
                            p_col, life=random.uniform(1.2, 3.0), size=random.uniform(5, 11)
                        ))

                # Game over?
                elif not self.rocket.alive:
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

                # Cápsulas de Combustível no caminho
                for can in self.fuel_canisters:
                    can.draw(self.screen, cam_x, cam_y,
                             self.screen_w, self.screen_h)

                # Indicadores de radar nas bordas da tela para cápsulas próximas
                self.draw_fuel_radar(cam_x, cam_y)

                # Partículas
                for p in self.particles:
                    p.draw(self.screen, cam_x, cam_y,
                           self.screen_w, self.screen_h)

                # Textos flutuantes de recarga
                for ft in self.floating_texts:
                    ft.draw(self.screen, self.font_hud, cam_x, cam_y,
                            self.screen_w, self.screen_h)

                # Foguete (no centro da tela — câmera segue)
                rcx = self.screen_w // 2
                rcy = self.screen_h // 2
                self.rocket.draw(self.screen, rcx, rcy)

                # HUD
                self.draw_hud()

                # Alerta de queda livre (desenhado sobre o HUD para máxima visibilidade)
                self.draw_freefall_alert()

            # --- Telas especiais ---
            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "GAMEOVER":
                self.draw_game_over()
            elif self.state == "VICTORY":
                self.draw_victory()
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
