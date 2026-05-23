import subprocess
import sys
from pathlib import Path


def test_generated_api_client_is_up_to_date() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "generate_api_client.py"),
            "--check",
        ],
        cwd=repo_root / "services" / "api",
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
