---
name: python-project
description: Menyiapkan proyek Python modern: venv, struktur, pyproject, lint, test.
---
# Proyek Python
Struktur: `src/<pkg>/__init__.py`, `tests/`, `pyproject.toml`, `README.md`, `.gitignore`.
1. `python3 -m venv .venv && . .venv/bin/activate && pip install -U pip`
2. `pyproject.toml` minimal: `[project] name, version, requires-python = ">=3.9", dependencies=[...]` dan `[project.scripts]` bila CLI.
3. Dev tools: `pip install pytest ruff` -> `ruff check .` dan `pytest -q`.
4. Pin dependensi: `pip freeze > requirements.txt` (aplikasi) atau rentang versi di pyproject (pustaka).
5. Jalankan sekali untuk memverifikasi, tampilkan pohon folder.
Hindari instal global (`pip install` tanpa venv) pada server produksi.
