---
name: json-yaml-tools
description: Mengolah JSON/YAML: pretty-print, ekstrak kunci, validasi, konversi (jq/python).
---
# JSON & YAML
- Rapikan/ekstrak: `python3 {SKILLDIR}/scripts/jsonpp.py file.json [kunci.bersarang]`.
- jq (jika ada): `jq '.items[] | {id, name}' file.json`; Python: `python3 -c "import json,sys; d=json.load(sys.stdin); print(d['k'])" < file.json`.
- YAML: `python3 -c "import yaml,json,sys; print(json.dumps(yaml.safe_load(sys.stdin), indent=2))" < file.yaml` (butuh PyYAML). Gunakan `safe_load`, bukan `load`.
- Validasi: pastikan parse sukses lalu periksa kunci wajib; untuk skema formal gunakan JSON Schema.
- Jangan menimpa file asli sebelum hasil transformasi diperiksa; tulis ke file baru dulu.
