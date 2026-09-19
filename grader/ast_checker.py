import ast

_NODE_MAP = {
    "For": ast.For,
    "While": ast.While,
    "ListComp": ast.ListComp,
    "FunctionDef": ast.FunctionDef,
}


def _detect_recursion(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            fname = node.name
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == fname:
                    return True
    return False


def _imported_modules(tree: ast.AST) -> set:
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    return mods


def _called_names(tree: ast.AST) -> set:
    """Tên hàm/phương thức được GỌI trực tiếp trong code, vd sorted(x) -> 'sorted', x.sort() -> 'sort'."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def check_structure(source_code: str, required=None, forbidden=None, forbidden_imports=None, forbidden_calls=None):
    """Kiểm tra tĩnh (chỉ đọc mã nguồn, không chạy chương trình). Trả về (ok, violations)."""
    required = required or []
    forbidden = forbidden or []
    forbidden_imports = forbidden_imports or []
    forbidden_calls = forbidden_calls or []

    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return False, [f"Không parse được code (SyntaxError dòng {e.lineno}): {e.msg}"]

    present = {name for name, cls in _NODE_MAP.items() if any(isinstance(n, cls) for n in ast.walk(tree))}
    if _detect_recursion(tree):
        present.add("Recursion")
    used_imports = _imported_modules(tree)
    used_calls = _called_names(tree)

    violations = [f"Thiếu cấu trúc bắt buộc: phải dùng {r}" for r in required if r not in present]
    violations += [f"Dùng cấu trúc bị cấm: không được dùng {f}" for f in forbidden if f in present]
    violations += [f"Import thư viện bị cấm: {m}" for m in forbidden_imports if m in used_imports]
    violations += [f"Gọi hàm/phương thức bị cấm: {c}()" for c in forbidden_calls if c in used_calls]
    return len(violations) == 0, violations
