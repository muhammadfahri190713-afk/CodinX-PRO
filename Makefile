# CodinX — target pengembangan. Butuh Python >= 3.9.
PY ?= python3

.PHONY: test scan zip vendor docs clean install
test:     ## jalankan seluruh test
	$(PY) -m unittest discover -s tests -t . -v

scan:     ## pindai rahasia sebelum push
	$(PY) scripts/secret_scan.py .

zip:      ## bangun CodinX.zip (tanpa rahasia) di folder dist/
	$(PY) scripts/build_zip.py --out dist/CodinX.zip

vendor:   ## bangun ulang subset Pygments (butuh pygments terpasang di sistem)
	$(PY) scripts/vendor_pygments.py --budget-kb 880

docs:     ## regenerasi docs/COMMANDS.md & docs/CONFIG.md dari kode
	$(PY) scripts/gen_docs.py

install:  ## pasang ke /opt/codinx (root)
	bash install.sh

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf dist
