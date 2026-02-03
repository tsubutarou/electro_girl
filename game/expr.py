# 表情指定(JSON)サポート用の小さなヘルパー
# main.py から import して使う想定

def apply_expr(g, expr: str | None, default: str = "smile"):
    if expr:
        g.expression = str(expr)
    else:
        g.expression = default
