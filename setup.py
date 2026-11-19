"""
Package discovery for ai_platform (everything else is in pyproject.toml).

The sources live in ``code/`` but are installed as ``ai_platform``. A static
package list in pyproject.toml had to name every subpackage and had fallen
behind (a wheel contained 4 of the ~70 packages, so only editable installs
worked); discovering them here keeps the wheel complete as packages are added.
"""

from setuptools import find_packages, setup

SUBPACKAGES = find_packages(where="code", exclude=["*.__pycache__"])

setup(
    package_dir={"ai_platform": "code"},
    packages=["ai_platform"] + [f"ai_platform.{name}" for name in SUBPACKAGES],
)
