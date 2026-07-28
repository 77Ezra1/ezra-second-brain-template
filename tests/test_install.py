from __future__ import annotations

import importlib.util
import py_compile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install.py"


def load_install():
    module_name = f"install_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, INSTALL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_template(root: Path) -> None:
    (root / "config").mkdir(parents=True)
    (root / "config" / "brain.example.yaml").write_text(
        "root: ./data\n"
        "platform: auto\n"
        "timezone: Asia/Shanghai\n"
        "lark_expense_sync:\n"
        "  enabled: false\n"
        "  base_token: \"\"\n"
        "  table_id: \"\"\n",
        encoding="utf-8",
    )
    (root / "config" / "categories.example.yaml").write_text("categories: {}\n", encoding="utf-8")


def test_install_py_compiles() -> None:
    py_compile.compile(str(INSTALL), doraise=True)


def test_ensure_runtime_layout_writes_macos_config(tmp_path: Path) -> None:
    install = load_install()
    seed_template(tmp_path)

    install.ensure_runtime_layout(tmp_path, platform_name="macos")

    config = (tmp_path / "config" / "brain.yaml").read_text(encoding="utf-8")
    assert "platform: macos" in config
    assert "root: " in config
    assert (tmp_path / "data" / "raw").is_dir()
    assert (tmp_path / "data" / "wiki" / "life").is_dir()
    assert (tmp_path / "config" / "categories.yaml").exists()


def test_ensure_runtime_layout_writes_windows_config(tmp_path: Path) -> None:
    install = load_install()
    seed_template(tmp_path)

    install.ensure_runtime_layout(tmp_path, platform_name="windows")

    config = (tmp_path / "config" / "brain.yaml").read_text(encoding="utf-8")
    assert "platform: windows" in config
    assert "root: " in config
    assert "\\" not in next(line for line in config.splitlines() if line.startswith("root: "))
    assert (tmp_path / "data" / "daily" / "reports").is_dir()


def test_ensure_runtime_layout_updates_copied_template_config(tmp_path: Path) -> None:
    install = load_install()
    seed_template(tmp_path)
    (tmp_path / "config" / "brain.yaml").write_text(
        "root: ./data\nplatform: auto\ntimezone: Asia/Shanghai\n",
        encoding="utf-8",
    )

    install.ensure_runtime_layout(tmp_path, platform_name="windows")

    config = (tmp_path / "config" / "brain.yaml").read_text(encoding="utf-8")
    assert "root: ./data" not in config
    assert "platform: windows" in config


def test_print_platform_next_steps_uses_windows_python_launcher(capsys, tmp_path: Path) -> None:
    install = load_install()

    install.print_platform_next_steps(tmp_path, platform_name="windows")

    out = capsys.readouterr().out
    assert "Platform preset: windows" in out
    assert "py -3 scripts/telegram_brain_router.py" in out
    assert ".venv\\Scripts\\Activate.ps1" in out
