---
name: changelog-release
description: Menyusun CHANGELOG dan rilis semver: kategori, tag git, catatan rilis.
---
# Changelog & rilis
- Format Keep a Changelog: `## [x.y.z] - YYYY-MM-DD` dengan Ditambahkan / Diubah / Diperbaiki / Dihapus / Keamanan.
- Ambil bahan: `git log --oneline <tag-lama>..HEAD`; kelompokkan menurut dampak untuk user, bukan menurut commit.
- Semver: perubahan rusak = major, fitur = minor, perbaikan = patch.
- Rilis: update versi (`cx/__init__.py`/package.json) -> commit -> `git tag -a vX.Y.Z -m '...'` -> `git push --tags` (hanya bila diminta).
