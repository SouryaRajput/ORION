"""
Simulation Renderer — Handles interactive VPython/Pygame simulations.
Provides a framework for parameter-adjustable physics simulations.
"""

from typing import Optional, Callable
from study.models.scene_schema import ScenePlan, SceneType
from study.utils.logger import get_logger

log = get_logger("simulation")


# Registry of built-in simulation functions
_SIMULATION_REGISTRY: dict[str, Callable] = {}


def register_simulation(name: str):
    """Decorator to register a simulation function."""
    def decorator(func: Callable):
        _SIMULATION_REGISTRY[name] = func
        log.debug(f"Registered simulation: {name}")
        return func
    return decorator


@register_simulation("projectile_motion")
def projectile_motion(params: dict):
    """Interactive projectile motion simulation using Pygame."""
    import pygame
    import math

    pygame.init()
    W, H = 800, 500
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Projectile Motion")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 16)

    g = params.get("gravity", 9.8)
    v0 = params.get("initial_velocity", 40)
    angle = params.get("angle", 45)
    scale = params.get("scale", 5)

    angle_rad = math.radians(angle)
    vx = v0 * math.cos(angle_rad)
    vy = v0 * math.sin(angle_rad)

    trail: list[tuple[int, int]] = []
    t = 0
    dt = 0.02
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    trail.clear()
                    t = 0

        x = vx * t * scale
        y_phys = vy * t - 0.5 * g * t * t
        y_screen = H - 50 - y_phys * scale

        if y_screen < H - 50 and y_phys >= 0:
            trail.append((int(50 + x), int(y_screen)))
            t += dt

        screen.fill((31, 41, 55))
        pygame.draw.line(screen, (100, 100, 100), (0, H - 50), (W, H - 50), 2)

        # Draw trail
        if len(trail) > 1:
            pygame.draw.lines(screen, (59, 130, 246), False, trail, 2)

        # Draw projectile
        if trail:
            pygame.draw.circle(screen, (239, 68, 68), trail[-1], 6)

        # HUD
        info = font.render(f"v₀={v0} m/s  θ={angle}°  g={g} m/s²  [R]eset [ESC]uit", True, (200, 200, 200))
        screen.blit(info, (10, 10))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


@register_simulation("pendulum")
def pendulum_simulation(params: dict):
    """Interactive pendulum simulation using Pygame."""
    import pygame
    import math

    pygame.init()
    W, H = 600, 500
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Pendulum")
    clock = pygame.time.Clock()

    L = params.get("length", 200)
    g = params.get("gravity", 9.8)
    theta = math.radians(params.get("initial_angle", 30))
    omega = 0
    dt = 0.05
    damping = params.get("damping", 0.999)
    pivot = (W // 2, 80)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        alpha = -(g / L) * math.sin(theta) * 50
        omega += alpha * dt
        omega *= damping
        theta += omega * dt

        bx = pivot[0] + L * math.sin(theta)
        by = pivot[1] + L * math.cos(theta)

        screen.fill((31, 41, 55))
        pygame.draw.line(screen, (150, 150, 150), pivot, (int(bx), int(by)), 2)
        pygame.draw.circle(screen, (59, 130, 246), (int(bx), int(by)), 15)
        pygame.draw.circle(screen, (100, 100, 100), pivot, 5)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def run_simulation(name: str, params: Optional[dict] = None) -> bool:
    """Run a registered simulation by name."""
    params = params or {}

    if name not in _SIMULATION_REGISTRY:
        log.error(f"Unknown simulation: {name}")
        log.info(f"Available: {list(_SIMULATION_REGISTRY.keys())}")
        return False

    log.info(f"Starting simulation: {name}")
    try:
        _SIMULATION_REGISTRY[name](params)
        return True
    except Exception as e:
        log.error(f"Simulation error: {e}")
        return False


def list_simulations() -> list[str]:
    """List all registered simulation names."""
    return list(_SIMULATION_REGISTRY.keys())
