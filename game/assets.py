from __future__ import annotations
import os
import re
import json
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



def load_atlas_sprites(assets_root: str) -> dict[str, pygame.Surface]:
    """アトラス方式（atlas.png + atlas_map.json）からスプライトを切り出す。

    置き場所（v0.1）:
      assets/sprite/atlas.png
      assets/sprite/atlas_map.json

    atlas_map.json の slots には以下のような形式でタイル座標が入る:
      "body_idle": {"col": 0, "row": 0}

    ここで返す辞書キーは slots のキー名をそのまま使う。
    """
    atlas_png = os.path.join(assets_root, "sprite", "atlas.png")
    atlas_map = os.path.join(assets_root, "sprite", "atlas_map.json")
    if not (os.path.exists(atlas_png) and os.path.exists(atlas_map)):
        return {}

    try:
        with open(atlas_map, "r", encoding="utf-8") as f:
            m = json.load(f)
        tile_w, tile_h = m.get("tile_size", [64, 64])
        slots = m.get("slots", {})
        atlas = load_image(atlas_png)
    except Exception:
        return {}

    out: dict[str, pygame.Surface] = {}
    for name, pos in slots.items():
        try:
            col = int(pos.get("col"))
            row = int(pos.get("row"))
            rect = pygame.Rect(col * tile_w, row * tile_h, tile_w, tile_h)
            surf = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
            surf.blit(atlas, (0, 0), rect)
            out[name] = surf
        except Exception:
            continue
    return out

def load_sprites(scale: int = 3) -> dict[str, pygame.Surface]:
    """スプライト読み込み（atlas優先 / 分割PNGフォールバック）。

    - 旧: assets/img/girl_*.png を参照していた名残があるが、v0.xでは使わない。
    - 新: assets/sprite/atlas.png + atlas_map.json があればそれを優先する。
    - 無ければ assets/sprite/ 以下の分割PNGを読む。
    """
    assets_root = os.path.dirname(cfg.IMG_DIR)
    sprite_dir = os.path.join(assets_root, "sprite")

    def safe_surface(w: int = 64, h: int = 64) -> pygame.Surface:
        return pygame.Surface((w, h), pygame.SRCALPHA)

    def safe_load(path: str) -> pygame.Surface | None:
        try:
            if os.path.exists(path):
                return load_image(path)
        except Exception:
            return None
        return None

    sprites_raw: dict[str, pygame.Surface] = {}

    # 1) atlas（あれば優先）
    try:
        atlas = load_atlas_sprites(assets_root)
        if atlas:
            sprites_raw.update(atlas)
    except Exception:
        pass

    # 2) 分割PNG（不足分だけ補完）
    sprites_raw.setdefault("body_idle", safe_load(os.path.join(sprite_dir, "body_idle.png")) or safe_surface())
    for i in range(3):
        k = f"body_walk_{i}"
        sprites_raw.setdefault(k, safe_load(os.path.join(sprite_dir, f"body_walk_{i}.png")) or sprites_raw["body_idle"])
    sprites_raw.setdefault("body_sleep", safe_load(os.path.join(sprite_dir, "body_sleep.png")) or sprites_raw["body_idle"])
    sprites_raw.setdefault("body_drowsy", safe_load(os.path.join(sprite_dir, "body_drowsy.png")) or sprites_raw["body_idle"])

    sprites_raw.setdefault("clothes_normal", safe_load(os.path.join(sprite_dir, "clothes", "normal.png")) or safe_surface())
    sprites_raw.setdefault("clothes_alt", safe_load(os.path.join(sprite_dir, "clothes", "alt.png")) or sprites_raw["clothes_normal"])

    sprites_raw.setdefault("face_normal", safe_load(os.path.join(sprite_dir, "face", "normal.png")) or safe_surface())
    sprites_raw.setdefault("face_smile", safe_load(os.path.join(sprite_dir, "face", "smile.png")) or sprites_raw["face_normal"])
    sprites_raw.setdefault("face_trouble", safe_load(os.path.join(sprite_dir, "face", "trouble.png")) or sprites_raw["face_normal"])
    sprites_raw.setdefault("face_blink", safe_load(os.path.join(sprite_dir, "face", "blink.png")) or safe_surface())
    sprites_raw.setdefault("face_mouth", safe_load(os.path.join(sprite_dir, "face", "mouth.png")) or safe_surface())

    # 3) 旧キー互換（古い描画コードが参照しても落ちないように）
    sprites_raw.setdefault("idle", sprites_raw["body_idle"])
    sprites_raw.setdefault("sleep", sprites_raw["body_sleep"])
    sprites_raw.setdefault("talk", sprites_raw["body_idle"])

    # 4) スケール（整数倍、ニアレスト）
    if scale and scale != 1:
        out: dict[str, pygame.Surface] = {}
        for k, s in sprites_raw.items():
            try:
                out[k] = scale_nearest(s, scale)
            except Exception:
                out[k] = s
        return out
    return sprites_raw

def load_clothes_offsets(scale: int = 3) -> dict[str, tuple[int, int]]:
    """衣装(clothes_*)の描画オフセットをJSONから読む。

    置き場所: assets/sprite/clothes/offsets.json

    形式(どちらでもOK):
      {"normal": [0, 0], "alt": [1, -2]}
      {"normal": {"x": 0, "y": 0}, "alt": {"x": 1, "y": -2}}

    数値は「元画像(スケール前)のピクセル」を想定し、ここで scale 倍する。
    """
    # assets_root は assets/img の1つ上（= assets）
    assets_root = os.path.dirname(cfg.IMG_DIR)
    path = os.path.join(assets_root, "sprite", "clothes", "offsets.json")
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}

    out: dict[str, tuple[int, int]] = {}
    if not isinstance(raw, dict):
        return out

    for oid, v in raw.items():
        dx = dy = 0
        try:
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                dx, dy = int(v[0]), int(v[1])
            elif isinstance(v, dict):
                dx = int(v.get("x", 0))
                dy = int(v.get("y", 0))
        except Exception:
            dx = dy = 0
        out[str(oid)] = (dx * scale, dy * scale)
    return out


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


def list_background_image_ids() -> list[str]:
    """assets/background 内の画像ファイルを自動検出して id(拡張子なし) を返す。

    対象: png/jpg/jpeg/webp/bmp
    """
    assets_root = os.path.dirname(cfg.IMG_DIR)
    bg_dir = os.path.join(assets_root, "background")
    if not os.path.isdir(bg_dir):
        return []

    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    ids: list[str] = []
    for fn in os.listdir(bg_dir):
        ext = os.path.splitext(fn)[1].lower()
        if ext in exts:
            ids.append(os.path.splitext(fn)[0])
    # "default" を先頭に（あれば）
    ids = sorted(set(ids))
    if "default" in ids:
        ids.remove("default")
        ids.insert(0, "default")
    return ids


def load_background_images(scale: int = 1, thumb_size: tuple[int, int] = (40, 40)) -> tuple[dict[str, pygame.Surface], dict[str, pygame.Surface]]:
    """背景画像を読み込み、(images, thumbs) を返す。

    - images: id -> pygame.Surface (convert)
    - thumbs: id -> pygame.Surface (smoothscale)

    ※ 背景は基本「写真/イラスト」想定なので smoothscale を使う。
    """
    assets_root = os.path.dirname(cfg.IMG_DIR)
    bg_dir = os.path.join(assets_root, "background")
    if not os.path.isdir(bg_dir):
        return {}, {}

    exts = [".png", ".jpg", ".jpeg", ".webp", ".bmp"]

    images: dict[str, pygame.Surface] = {}
    thumbs: dict[str, pygame.Surface] = {}

    for bid in list_background_image_ids():
        path = None
        for ext in exts:
            p = os.path.join(bg_dir, bid + ext)
            if os.path.exists(p):
                path = p
                break
        if not path:
            continue
        try:
            img = pygame.image.load(path).convert()  # 背景はα無しでOK
            if scale and scale != 1:
                w, h = img.get_size()
                img = pygame.transform.smoothscale(img, (max(1, int(w * scale)), max(1, int(h * scale))))
            images[bid] = img

            tw, th = thumb_size
            w0, h0 = img.get_size()
            if w0 > 0 and h0 > 0:
                s = min(tw / w0, th / h0)
                nw = max(1, int(w0 * s))
                nh = max(1, int(h0 * s))
                thumbs[bid] = pygame.transform.smoothscale(img, (nw, nh))
        except Exception:
            pass

    return images, thumbs


def make_theme_thumbs(thumb_size: tuple[int, int] = (40, 40)) -> dict[str, pygame.Surface]:
    """cfg.BG_THEMES の単色背景用サムネを作る。 key は theme name。"""
    tw, th = thumb_size
    out: dict[str, pygame.Surface] = {}
    for t in (cfg.BG_THEMES or []):
        name = str(t.get("name", "theme"))
        col = t.get("bg", (25, 25, 32))
        surf = pygame.Surface((tw, th))
        surf.fill(col)
        out[name] = surf
    return out
