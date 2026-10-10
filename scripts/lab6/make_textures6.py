"""Лаба 6: текстуры, собранные скриптом по шагам графического редактора (Photoshop) из методички.
Запуск: .venv/bin/python scripts/lab6/make_textures6.py
Результат: output/lab6/Звёздное_небо_2500x2500.png, Звёздное_небо_6000x3000.png, Планета_2048x1024.png
и промежуточные картинки build/figs6/t_*.png для отчёта."""
import os
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "output", "lab6")
FIG = os.path.join(ROOT, "build", "figs6")
os.makedirs(OUT, exist_ok=True); os.makedirs(FIG, exist_ok=True)


def to_img(a):
    return Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8))


def preview(a, name, size=900):
    """Уменьшенная копия для отчёта. Берётся максимум по блокам, чтобы одиночные звёзды не пропали."""
    k = int(np.ceil(max(a.shape[:2]) / size))
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    small = a[:h, :w].reshape(h // k, k, w // k, k, -1).max(axis=(1, 3))
    to_img(small).save(os.path.join(FIG, name + ".png"))


def gaussian_blur(a, radius):
    """Размытие по Гауссу (радиус в пикселях, как в Photoshop)."""
    chans = [np.asarray(Image.fromarray((a[..., c] * 255).astype(np.uint8), mode="L")
                        .filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255 for c in range(a.shape[2])]
    return np.stack(chans, -1)


def twirl(a, angle_deg):
    """Фильтр «Скручивание» (Twirl): поворот тем сильнее, чем ближе к центру."""
    h, w = a.shape[:2]
    cy, cx = (h - 1) / 2, (w - 1) / 2
    R = min(h, w) / 2
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = x - cx, y - cy
    r = np.hypot(dx, dy)
    t = np.clip(1 - r / R, 0, 1)
    ang = np.radians(angle_deg) * t
    c, s = np.cos(ang), np.sin(ang)
    sx = np.clip(cx + dx * c - dy * s, 0, w - 1).astype(np.int32)
    sy = np.clip(cy + dx * s + dy * c, 0, h - 1).astype(np.int32)
    return a[sy, sx]


def starfield(w, h, seed, prefix=None):
    rng = np.random.default_rng(seed)
    # 1. Новый документ, залить чёрным
    base = np.zeros((h, w, 3), np.float32)
    # 1. Шум «по Гауссу», 10 %, монохромный (одно значение на все каналы)
    noise = rng.normal(0.0, 0.10, (h, w)).astype(np.float32)
    layer = np.clip(base + noise[..., None], 0, 1)
    if prefix:
        preview(layer, prefix + "1_noise")
    # 2. Уровни: входная чёрная точка 0,25, белая 0,40 — остаются только самые яркие точки (звёзды)
    black, white = 0.25, 0.40
    stars = np.clip((layer - black) / (white - black), 0, 1)
    if prefix:
        preview(stars, prefix + "2_levels")
    # 3. Новый слой: цветные пятна кистью
    spots = np.zeros((h, w, 3), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    palette = [(0.75, 0.10, 0.10), (0.45, 0.10, 0.60), (0.10, 0.25, 0.75), (0.80, 0.40, 0.10), (0.15, 0.45, 0.55)]
    scale = min(w, h) / 2500
    n_side = max(3, int(round(5 * w / 2500))), max(3, int(round(5 * h / 2500)))
    for gx in range(n_side[0]):          # пятна разбросаны равномерно: по одному-два в каждой клетке сетки
        for gy in range(n_side[1]):
            for _ in range(rng.integers(1, 3)):
                cx = (gx + rng.uniform(0, 1)) * w / n_side[0]; cy = (gy + rng.uniform(0, 1)) * h / n_side[1]
                rad = rng.uniform(90, 260) * scale
                col = np.array(palette[rng.integers(len(palette))], np.float32) * rng.uniform(0.45, 0.8)
                y0, y1 = int(max(cy - rad, 0)), int(min(cy + rad, h)); x0, x1 = int(max(cx - rad, 0)), int(min(cx + rad, w))
                d2 = ((xx[y0:y1, x0:x1] - cx) ** 2 + (yy[y0:y1, x0:x1] - cy) ** 2) / rad ** 2
                soft = np.clip(1 - d2, 0, 1) ** 1.5      # мягкая кисть
                spots[y0:y1, x0:x1] = np.maximum(spots[y0:y1, x0:x1], soft[..., None] * col)
    if prefix:
        preview(spots, prefix + "3_spots")
    # 3. Размытие по Гауссу, радиус > 30 (взято 60 для 2500 px)
    spots = gaussian_blur(spots, 60 * scale)
    if prefix:
        preview(spots, prefix + "4_blur")
    # 3. Скручивание (Twirl)
    spots = twirl(spots, 120)
    if prefix:
        preview(spots, prefix + "5_twirl")
    # 3. Режим наложения «Экран», непрозрачность слоя 55 %
    opacity = 0.55
    screen = 1 - (1 - stars) * (1 - spots)
    result = stars + (screen - stars) * opacity
    if prefix:
        preview(result, prefix + "6_result")
    return result


# --- Задание 1: квадратная текстура 2500×2500, как в методичке
sq = starfield(2500, 2500, seed=6, prefix="t_")
to_img(sq).save(os.path.join(OUT, "Звёздное_небо_2500x2500.png"), optimize=True)

# --- Вариант 2:1 для «Текстуры окр. среды» (равнопромежуточная проекция требует соотношения 2:1)
eq = starfield(6000, 3000, seed=7)
to_img(eq).save(os.path.join(OUT, "Звёздное_небо_6000x3000.png"), optimize=True)
print("stars done")


# --- Текстура планеты (своя, оригинала из папки с лабораторной нет): шум на сфере → равнопромежуточная 2:1
def value_noise3(p, rng_perm, freq):
    q = p * freq
    i = np.floor(q).astype(np.int64); f = q - i
    f = f * f * (3 - 2 * f)
    perm = rng_perm

    def h(ix, iy, iz):
        return perm[(perm[(perm[ix & 255] + iy) & 255] + iz) & 255] / 255.0

    x, y, z = i[..., 0], i[..., 1], i[..., 2]
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    def lerp(a, b, t): return a + (b - a) * t
    c00 = lerp(h(x, y, z), h(x + 1, y, z), fx); c10 = lerp(h(x, y + 1, z), h(x + 1, y + 1, z), fx)
    c01 = lerp(h(x, y, z + 1), h(x + 1, y, z + 1), fx); c11 = lerp(h(x, y + 1, z + 1), h(x + 1, y + 1, z + 1), fx)
    return lerp(lerp(c00, c10, fy), lerp(c01, c11, fy), fz)


W, H = 2048, 1024
lon = (np.arange(W) + 0.5) / W * 2 * np.pi - np.pi
lat = np.pi / 2 - (np.arange(H) + 0.5) / H * np.pi
LON, LAT = np.meshgrid(lon, lat)
P = np.stack([np.cos(LAT) * np.cos(LON), np.cos(LAT) * np.sin(LON), np.sin(LAT)], -1).astype(np.float64) + 10.0
perm = np.random.default_rng(42).permutation(256)
n = np.zeros((H, W)); amp = 1.0; tot = 0
for o in range(7):
    n += amp * value_noise3(P, perm, 2.2 * 2 ** o); tot += amp; amp *= 0.5
n /= tot
warp = value_noise3(P + 3.3, perm, 3.0)
bands = 0.5 + 0.5 * np.sin(LAT * 9 + (n - 0.5) * 9 + warp * 4)
hgt = np.clip((n - 0.30) / 0.42, 0, 1) * 0.75 + bands * 0.25
# кратеры
rng = np.random.default_rng(3)
for _ in range(60):
    c = rng.normal(size=3); c /= np.linalg.norm(c)
    r = rng.uniform(0.02, 0.09)
    d = np.linalg.norm(P - 10.0 - c, axis=-1) / r
    hgt += np.where(d < 1, -0.18 * (1 - d ** 2), 0) + np.where((d >= 1) & (d < 1.3), 0.12 * (1 - abs(d - 1.15) / 0.15).clip(0), 0)
hgt = np.clip(hgt, 0, 1)
stops = np.array([0.0, 0.3, 0.55, 0.75, 1.0])
cols = np.array([[0.20, 0.10, 0.06], [0.42, 0.22, 0.12], [0.62, 0.40, 0.24], [0.76, 0.58, 0.40], [0.90, 0.80, 0.66]])
planet = np.stack([np.interp(hgt, stops, cols[:, k]) for k in range(3)], -1)
to_img(planet).save(os.path.join(OUT, "Планета_2048x1024.png"), optimize=True)
preview(planet, "t_planet", 1200)
print("planet done")
