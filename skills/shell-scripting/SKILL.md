---
name: shell-scripting
description: Menulis skrip bash yang aman dan portabel: strict mode, quoting, trap, argumen, shellcheck.
---
# Skrip bash
Kerangka:
```bash
#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
trap 'echo "gagal di baris $LINENO" >&2' ERR
usage() { echo "Pakai: $0 <arg>" >&2; exit 2; }
[[ $# -ge 1 ]] || usage
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
```
- Selalu kutip variabel `"$var"`; gunakan `[[ ]]`, `$(...)`, array untuk daftar; jangan parse `ls`.
- Konfirmasi sebelum operasi merusak; dukung `--dry-run`. Hindari `rm -rf "$dir/"` jika `$dir` bisa kosong (`${dir:?}`).
- Validasi: `bash -n skrip.sh`, dan `shellcheck skrip.sh` bila terpasang. Uji di folder sementara.
