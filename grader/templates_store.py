import json
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates"

# Thư mục dùng khi chưa truyền teacher_id — giữ tương thích ngược cho script/test cũ
# gọi các hàm này mà không có khái niệm GV (vd test nội bộ của grader/).
_LEGACY_NAMESPACE = "_legacy"


def _teacher_dir(teacher_id) -> Path:
    namespace = str(teacher_id) if teacher_id is not None else _LEGACY_NAMESPACE
    d = TEMPLATES_ROOT / namespace
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_templates(teacher_id=None):
    return sorted(p.stem for p in _teacher_dir(teacher_id).glob("*.json"))


def load_template(name: str, teacher_id=None) -> dict:
    return json.loads((_teacher_dir(teacher_id) / f"{name}.json").read_text(encoding="utf-8"))


def save_template(name: str, data: dict, teacher_id=None) -> str:
    """Lưu khung mẫu, trả về tên file thực tế (đã chuẩn hoá) để gọi nơi khác đồng bộ lại lựa chọn."""
    safe_name = "".join(c for c in name if c.isalnum() or c in "_- ").strip().replace(" ", "_")
    (_teacher_dir(teacher_id) / f"{safe_name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return safe_name


def delete_template(name: str, teacher_id=None):
    path = _teacher_dir(teacher_id) / f"{name}.json"
    if path.exists():
        path.unlink()
