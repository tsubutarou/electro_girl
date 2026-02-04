# Cleanup Notes

- Generated: 2026-02-04 16:55

## Moves performed
- `assets/sprite/body_idle.png` → `assets/old/sprite_split/body_idle.png`
- `assets/sprite/body_walk_0.png` → `assets/old/sprite_split/body_walk_0.png`
- `assets/sprite/body_walk_1.png` → `assets/old/sprite_split/body_walk_1.png`
- `assets/sprite/body_walk_2.png` → `assets/old/sprite_split/body_walk_2.png`
- `assets/sprite/character.edg` → `assets/old/sprite_split/character.edg`
- `assets/sprite/character.png` → `assets/old/sprite_split/character.png`
- `assets/sprite/clothes` → `assets/old/sprite_split/clothes`
- `assets/sprite/Edge1.anm` → `assets/old/sprite_split/Edge1.anm`
- `assets/sprite/face` → `assets/old/sprite_split/face`
- `assets/characters/sample_girl` → `assets/old/samples/sample_girl`
- `assets/characters/sample_girl_atlas` → `assets/old/samples/sample_girl_atlas`

## Other actions
- Removed `__pycache__`, `*.pyc`, and `.DS_Store` files.

## Rationale
- Atlas assets detected; keeping atlas files in active paths.
- Moved legacy split sprite assets from assets/sprite/* (except atlas files) to assets/old/sprite_split/ .
- Moved sample_* character folders to assets/old/samples/ (kept for reference).
