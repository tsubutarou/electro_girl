from __future__ import annotations
import os
import re
import pygame

from . import config as cfg


def load_image(path: str) -> pygame.Surface:
    """画像を読み込んで convert_alpha して返す"""
    return pygame.image.load(path).convert_alpha()


def scale_nearest(img: pygame.Surface, scale: int) -> pygame.Surface:
    """ドット絵向け：ニアレストで整数倍拡大"""
    w, h = img.get_size()
    return pygame.transform.scale(img, (w * scale, h * scale))


def safe_sound(path: str):
    try:
        if os.path.exists(path):
            return pygame.mixer.Sound(path)
    except Exception:
        pass
    return None


def load_sprites(scale: int = 3) -> dict[str, pygame.Surface]:
    """
    既存：状態別の立ち絵（idle/sleep/music/grumpy）
    追加：瞬き/口パク用の body/face（存在しなければロードしない）
    追加：表情差分 face_{normal/smile/trouble}（存在しなければロードしない）
    """
    sprites_raw: dict[str, pygame.Surface] = {
        "idle":   load_image(os.path.join(cfg.IMG_DIR, "girl_idle.png")),
        "sleep":  load_image(os.path.join(cfg.IMG_DIR, "girl_sleep.png")),
        "music":  load_image(os.path.join(cfg.IMG_DIR, "girl_music.png")),
        "grumpy": load_image(os.path.join(cfg.IMG_DIR, "girl_grumpy.png")),
    }

    # assets_root は assets/img の1つ上（= assets）
    assets_root = os.path.dirname(cfg.IMG_DIR)

    # ---- body ----
    body_path = os.path.join(assets_root, "sprite", "body_idle.png")
    if os.path.exists(body_path):
        sprites_raw["body_idle"] = load_image(body_path)

    # ---- body walk frames (optional) ----
    # Put files like assets/sprite/body_walk_0.png, body_walk_1.png ...
    walk_re = re.compile(r"^body_walk_(\d+)\.png$", re.IGNORECASE)
    sprite_dir = os.path.join(assets_root, "sprite")
    if os.path.isdir(sprite_dir):
        walk_files = []
        for fn in os.listdir(sprite_dir):
            m2 = walk_re.match(fn)
            if m2:
                walk_files.append((int(m2.group(1)), fn))
        for idx, fn in sorted(walk_files, key=lambda t: t[0]):
            p = os.path.join(sprite_dir, fn)
            try:
                sprites_raw[f"body_walk_{idx}"] = load_image(p)
            except Exception:
                pass

    # ---- face base expressions ----
    for name in ("normal", "smile", "trouble"):
        p = os.path.join(assets_root, "sprite", "face", f"{name}.png")
        if os.path.exists(p):
            sprites_raw[f"face_{name}"] = load_image(p)


    # ---- clothes ----
    clothes_dir = os.path.join(assets_root, "sprite", "clothes")
    if os.path.isdir(clothes_dir):
        for fn in os.listdir(clothes_dir):
            if not fn.lower().endswith(".png"):
                continue
            oid = os.path.splitext(fn)[0]
            try:
                sprites_raw[f"clothes_{oid}"] = load_image(os.path.join(clothes_dir, fn))
            except Exception:
                pass

    # ---- overlays ----
    blink_p = os.path.join(assets_root, "sprite", "face", "blink.png")
    mouth_p = os.path.join(assets_root, "sprite", "face", "mouth.png")
    if os.path.exists(blink_p):
        sprites_raw["face_blink"] = load_image(blink_p)
    if os.path.exists(mouth_p):
        sprites_raw["face_mouth"] = load_image(mouth_p)

    return {k: scale_nearest(v, scale) for k, v in sprites_raw.items()}


def load_sounds(mixer_ok: bool) -> dict[str, object]:
    if not mixer_ok:
        return {}
    sounds = {
        "snack": safe_sound(os.path.join(cfg.SFX_DIR, "se_snack.wav")),
        "pet":   safe_sound(os.path.join(cfg.SFX_DIR, "se_pet.wav")),
        "off":   safe_sound(os.path.join(cfg.SFX_DIR, "se_lights_off.wav")),
        "on":    safe_sound(os.path.join(cfg.SFX_DIR, "se_lights_on.wav")),
        "talk":  safe_sound(os.path.join(cfg.SFX_DIR, "se_talk.wav")),
    }
    for k, v in sounds.items():
        if v:
            v.set_volume(0.30 if k in ("pet", "talk") else 0.35)
    return sounds
