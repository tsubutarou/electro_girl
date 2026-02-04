#!/usr/bin/env python
"""dialogue_csv_to_json.py
CSV（id,tags,text）→ assets/dialogue/lines.json 形式に変換する簡易ツール。
tags は | 区切り（例: greet_short|greet_long）
text は \n を含めると手動改行できます（任意）

Usage:
  python tools/dialogue_csv_to_json.py input.csv output.json
"""
import csv, json, sys

def main():
    if len(sys.argv) < 3:
        print("Usage: python tools/dialogue_csv_to_json.py input.csv output.json")
        return 2
    inp, outp = sys.argv[1], sys.argv[2]
    lines=[]
    with open(inp, "r", encoding="utf-8-sig", newline="") as f:
        r=csv.DictReader(f)
        for row in r:
            _id=(row.get("id") or "").strip()
            text=(row.get("text") or "").rstrip()
            if not _id or not text:
                continue
            tags=(row.get("tags") or "").strip()
            tag_list=[t.strip() for t in tags.split("|") if t.strip()] if tags else []
            lines.append({"id": _id, "tags": tag_list, "text": text})
    data={"chatter":{"interval_sec":[6.0,13.0],"chance_per_tick":1.0},"lines":lines}
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(lines)} lines -> {outp}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
