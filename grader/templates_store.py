import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def list_templates():
    TEMPLATES_DIR.mkdir(exist_ok=True)
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))


def load_template(name: str) -> dict:
    return json.loads((TEMPLATES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def save_template(name: str, data: dict) -> str:
    """Lưu khung mẫu, trả về tên file thực tế (đã chuẩn hoá) để gọi nơi khác đồng bộ lại lựa chọn."""
    TEMPLATES_DIR.mkdir(exist_ok=True)
    safe_name = "".join(c for c in name if c.isalnum() or c in "_- ").strip().replace(" ", "_")
    (TEMPLATES_DIR / f"{safe_name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return safe_name


def delete_template(name: str):
    path = TEMPLATES_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
