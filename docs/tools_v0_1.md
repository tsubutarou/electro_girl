# 制作補助ツール（v0.1）

## tools/dialogue_csv_to_json.py
会話をCSVで管理して、JSONに変換します。

CSV列:
- id
- tags（|区切り）
- text（\nで手動改行可）

例:
```
python tools/dialogue_csv_to_json.py dialogue.csv assets/dialogue/lines.json
```

## tools/validate_atlas.py
atlas.png + atlas_map.json の必須スロットをチェックします。

例:
```
python tools/validate_atlas.py assets/sprite/atlas.png assets/sprite/atlas_map.json
```
