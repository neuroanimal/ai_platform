from pathlib import Path
from importlib.metadata import distributions
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = SCRIPT_DIR / "requirements-pip-packages.txt"


def load_installed():
    installed = {}

    for dist in distributions():
        name = dist.metadata.get("Name")

        if name:
            installed[canonicalize_name(name)] = dist.version

    return installed


def main():
    if not REQUIREMENTS_FILE.exists():
        print(f"ERROR: Missing {REQUIREMENTS_FILE}")
        sys.exit(1)

    installed = load_installed()
    missing = []
    satisfied = []
    incompatible = []

    requirements = []

    for line in REQUIREMENTS_FILE.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        try:
            req = Requirement(line)
        except Exception as exc:
            print(f"Invalid requirement: {line}: {exc}")
            sys.exit(1)

        if req.marker and not req.marker.evaluate():
            continue

        requirements.append(line)

        name = canonicalize_name(req.name)
        version = installed.get(name)

        if version is None:
            missing.append(line)
        elif req.specifier and version not in req.specifier:
            incompatible.append(line)
        else:
            satisfied.append((req.name, version))

    print("\n===== PIP: ALREADY INSTALLED / SATISFIED =====")
    for name, version in satisfied:
        print(f"{name}=={version}")

    print("\n===== PIP: MISSING =====")
    for package in missing:
        print(package)

    print("\n===== PIP: VERSION MISMATCH =====")
    for package in incompatible:
        print(package)

    to_install = missing + incompatible

    if not to_install:
        print("\nNothing to install.")
        return

    print("\n===== PACKAGES TO INSTALL =====")
    for package in to_install:
        print(package)

    answer = input(
        f"\nInstall {len(to_install)} missing/incompatible packages? [y/N] "
    ).strip().lower()

    if answer != "y":
        print("Installation skipped.")
        return

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            *to_install,
        ],
        check=True,
    )


if __name__ == "__main__":
    main()

