# Asset Specification v0.1 (Electro Girl)

## Purpose
- Keep asset creation accessible.
- Fix the number of variations by specification.
- Favor maintainability over expressive excess.
- Maintain quiet desktop-presence aesthetics.

## Base Size
- 64x64 px per frame
- Transparent PNG
- Scaling handled at render time

## Animation Rule
- Sprite sheet per animation
- Horizontal layout
- Walk: exactly 3 frames

## State Rules
- Idle: body + clothes + face parts
- Walk: body + clothes only (neutral face baked into body)
- Sleep/Drowsy: body (+ clothes optional), no face parts
