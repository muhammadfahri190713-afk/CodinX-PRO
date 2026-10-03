---
name: python-testing
description: Menulis dan menjalankan test Python (pytest/unittest): fixture, mock, parametrisasi, cakupan.
---
# Testing Python
- Jalankan otomatis: `bash {SKILLDIR}/scripts/run_tests.sh` (mendeteksi pytest/unittest).
- Pola pytest: fungsi `test_*`, `@pytest.mark.parametrize`, fixture `tmp_path`/`monkeypatch`, `pytest.raises`.
- unittest: `python3 -m unittest discover -s tests -v`.
- Mock jaringan/waktu dengan `unittest.mock.patch`; jangan memanggil API sungguhan di test.
- Tulis test yang GAGAL dulu untuk bug, perbaiki, lalu pastikan lulus. Satu perilaku per test, nama deskriptif.
- Cakupan: `pytest --cov=<pkg> --cov-report=term-missing` (jika pytest-cov ada).
