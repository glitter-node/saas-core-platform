import getpass
import shutil
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DEPLOYMENT_DIR = ROOT_DIR / "deployment"
RENDERED_DIR = DEPLOYMENT_DIR / "rendered"
SYSTEMD_RENDERED_DIR = RENDERED_DIR / "systemd"
NGINX_RENDERED_DIR = RENDERED_DIR / "nginx"


def load_env(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"').strip("'")
    return values


def render_template(template_path: Path, target_path: Path, replacements: dict[str, str]) -> None:
    content = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        content = content.replace(key, value)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")


def main() -> None:
    _ = getpass.getuser()
    NGINX_RENDERED_DIR.mkdir(parents=True, exist_ok=True)
    SYSTEMD_RENDERED_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEPLOYMENT_DIR / "nginx" / "nginx.conf", NGINX_RENDERED_DIR / "nginx.conf")
    for name in ("saas_api.service", "saas_worker.service", "saas_scheduler.service"):
        shutil.copy2(DEPLOYMENT_DIR / "systemd" / name, SYSTEMD_RENDERED_DIR / name)


if __name__ == "__main__":
    main()
