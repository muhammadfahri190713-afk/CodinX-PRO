---
name: camera-capture
description: Mengambil foto dari kamera server dengan tool camera (butuh izin camera + fswebcam/ffmpeg).
---
# Kamera
- Izin `camera` mati secara bawaan: minta user mengaktifkannya lewat /permissions.
- Cek perangkat: `ls /dev/video*`. Gunakan tool `camera` (device, output). Simpan di folder proyek.
- Kalau fswebcam/ffmpeg tidak ada, sarankan `apt install fswebcam`.
- Jangan mengambil foto tanpa permintaan jelas dari user.
