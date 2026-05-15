import importlib
import os
import subprocess
import sys
from pathlib import Path

from app.domain.auth.passwords import hash_password


def _reload_cli(tmp_path: Path):
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "cli.sqlite3")
    settings = importlib.import_module("app.settings")
    importlib.reload(settings)
    user_mod = importlib.import_module("app.storage.user_store")
    importlib.reload(user_mod)
    cli_mod = importlib.import_module("app.tools.create_user")
    importlib.reload(cli_mod)
    return cli_mod, user_mod.UserStore()


def test_create_user_main_prints_id_and_exits_zero(tmp_path, capsys):
    cli_mod, user_store = _reload_cli(tmp_path)

    code = cli_mod.main(["--username", "admin", "--password", "s3cret!"])
    captured = capsys.readouterr()

    assert code == 0
    user_id = captured.out.strip()
    assert user_id
    loaded = user_store.get_by_username("admin")
    assert loaded is not None
    assert loaded.id == user_id
    assert "s3cret!" not in captured.out
    assert "s3cret!" not in captured.err


def test_create_user_main_exits_one_when_username_exists(tmp_path, capsys):
    cli_mod, _ = _reload_cli(tmp_path)
    assert cli_mod.main(["--username", "alice", "--password", "pw1"]) == 0
    capsys.readouterr()

    code = cli_mod.main(["--username", "  ALICE  ", "--password", "pw2"])
    captured = capsys.readouterr()

    assert code == 1
    assert "already exists" in captured.err
    assert captured.out == ""


def test_create_user_main_never_prints_password(tmp_path, capsys):
    cli_mod, _ = _reload_cli(tmp_path)
    secret = "do-not-leak-me"

    cli_mod.main(["--username", "bob", "--password", secret])
    captured = capsys.readouterr()

    assert secret not in captured.out
    assert secret not in captured.err


def test_create_user_subprocess(tmp_path):
    db_path = tmp_path / "subprocess.sqlite3"
    env = {**os.environ, "FC_SQLITE_PATH": str(db_path)}
    api_root = Path(__file__).resolve().parents[1]
    password = "cli-pass-99"

    first = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.tools.create_user",
            "--username",
            "cli-user",
            "--password",
            password,
        ],
        cwd=api_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert first.returncode == 0
    user_id = first.stdout.strip()
    assert user_id
    assert password not in first.stdout
    assert password not in first.stderr

    second = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.tools.create_user",
            "--username",
            "cli-user",
            "--password",
            password,
        ],
        cwd=api_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert second.returncode == 1
    assert "already exists" in second.stderr

    os.environ["FC_SQLITE_PATH"] = str(db_path)
    settings = importlib.import_module("app.settings")
    importlib.reload(settings)
    user_mod = importlib.import_module("app.storage.user_store")
    importlib.reload(user_mod)
    loaded = user_mod.UserStore().get_by_id(user_id)
    assert loaded is not None
    assert loaded.username == "cli-user"
