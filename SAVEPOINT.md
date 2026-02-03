# SAVEPOINT: wardrobe + x-move (2026-02-04)

この時点の目的:
- 衣装チェンジ（OUTボタン→サムネ一覧→クリックで切替）が動く
- 右パネル内のX軸うろうろ移動が動く

## 主要な依存関係
- 衣装一覧生成: `game/ui.py::WardrobeMenu.relayout(outfits, sprites)`
- 衣装一覧描画: `game/render.py`（wardrobe.open のとき panel/items/prev/next/close を描画）
- 衣装適用: `g.outfit` → `render.py` が `sprites[f"clothes_{g.outfit}"]` を重ねる

- 移動更新: `game/sim.py::step_move()` を `step_sim()` から呼ぶ
- 移動反映: `render.py` の `cx = base_cx + g.x_offset`

## よくある事故と対策
### 1) 機能が消える
パッチzipで `game/render.py` / `game/sim.py` を丸ごと上書きすると、別機能の修正が巻き戻りがち。

**対策**
- 変更はなるべく1ファイルに閉じる
- パッチ配布時に「上書き対象ファイル一覧」を書く
- できれば `SAVEPOINT.md` のように「この時点で動くもの」を固定してから進む

### 2) OUTボタンはあるのに一覧が出ない
原因はだいたいこれ:
- `render.py` が wardrobe を描いていない
- `main.py` が `wardrobe.relayout(outfits, sprites)` を呼んでいない
- `assets.py` が clothes をロードしていない（sprites に `clothes_*` が無い）

### 3) X移動しない
原因はだいたいこれ:
- `sim.py` が `step_move()` を呼んでいない
- `config.py` に WALK_* 定数が無い
- `render.py` が `g.x_offset` を cx に反映していない

