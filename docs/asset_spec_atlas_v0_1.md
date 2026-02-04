# 素材規格 v0.1（アトラス方式） — エレクトロガール

## 目的 / 思想
- 誰でも素材を追加できる敷居の低さを最優先する
- 差分数は仕様で固定し、無限増殖を防ぐ（開発中に増える場合は規格を改訂する）
- 1キャラ＝1枚の画像（アトラス）で管理し、差分漏れを物理的に起こしにくくする
- 常駐キャラとして「うるさくならない」演出を目指す

## 対象ユーザー
- 開発に慣れている仲間内（少人数）
- ドット絵・JSON・ファイル構成に抵抗がない人

---

## 基本仕様

### 1タイル（1マス）のサイズ
- **64×64 px**（透過PNG）
- 拡大・縮小は描画側で行う

### アトラス画像サイズ
- **8×8 タイル固定（512×512 px）**
- 1キャラにつき `atlas.png` 1枚のみ（+ マッピングJSON）

---

## フォルダ構成（1キャラ）

```
assets/characters/<character_id>/
├─ atlas.png
├─ atlas_map.json
└─ meta.json
```

---

## 状態ごとの描画ルール（重要）

### 静止（idle）
合成順：
1. body_idle
2. clothes_idle（任意）
3. 目・口（eye_open/eye_close + mouth_0〜2）
4. 感情（happy/angry/sad/surprise）は **「組み合わせ」または会話側の指定**（v0.1では最小限）

### 歩行（walk）
- **歩行中は表情パーツを使わない**
- 合成順：
  1. body_walk_0/1/2（3フレーム固定）
  2. clothes_walk_0/1/2（任意。ただしあるなら3フレーム揃える）

※歩行用ボディには **ニュートラル顔を焼き込み**（向き・反転で破綻しないため）

### 睡眠（sleep）
- body_sleep + clothes_sleep（任意）
- 目・口パーツは使わない

### あくび（drowsy）
- body_drowsy（+ clothes_idle など任意）
- v0.1では簡易表現でOK（固定顔の描き込み推奨）

---

## アトラス配置（固定）

- 座標は **(col,row)** のタイル座標（左上が (0,0)）
- 各スロットの意味は **規格で固定**（空きは予約）

### 配置図（ASCII）
```
row0: [body_idle] [body_walk0] [body_walk1] [body_walk2] [body_sleep] [body_drowsy] [reserved] [reserved]
row1: [clot_idle] [clot_walk0] [clot_walk1] [clot_walk2] [clot_sleep] [reserved  ] [reserved] [reserved]
row2: [eye_open ] [eye_close ] [mouth_0  ] [mouth_1  ] [mouth_2  ] [reserved  ] [reserved] [reserved]
row3: [reserved ] [reserved ] [reserved ] [reserved ] [reserved ] [reserved  ] [reserved] [reserved]
row4-7: 全て reserved（v0.2+ の拡張用）
```

### 配置図（画像）
`docs/atlas_layout_v0_1.png` を参照（タイル境界とラベル付き）。

---

## atlas_map.json（必須）
- どのスロットが何かを **JSONで明文化**する（コード側が読む／人間の確認にも使う）
- v0.1では上の固定配置だが、将来の拡張やツール化のため **必ず同梱**する

---

## NG / 非推奨（v0.1）
- スロットごとにフレーム数が違う（walkだけ3固定）
- 歩行中に目・口アニメを重ねる
- タイルサイズを勝手に変える
- スロット配置をキャラごとに変える（やるなら規格改訂）

---

## v0.2 以降の拡張余地
- sleep / drowsy のアニメ化（追加スロット消費）
- 表情カテゴリ追加（眉などのパーツ追加）
- 家具・ベッドのインタラクション
- 高解像度対応（規格改訂で別レーン扱い）

---

## まとめ
この規格は表現力を縛るためではなく、**素材を増やし続けられるようにするための制限**。
「1キャラ＝1枚」にすることで、管理コストと差分漏れを最小化する。
