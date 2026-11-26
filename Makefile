PYTHON := .venv/bin/python

.PHONY: setup validate test film references narration keyframes shots music assemble

setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.txt

validate:
	$(PYTHON) -c "from pipeline.core.validator import load_storyboard; load_storyboard(); print('Storyboard is valid')"

test:
	$(PYTHON) -m pytest tests/ -v

film:
	$(PYTHON) -m pipeline.main

references:
	$(PYTHON) -m pipeline.references

narration:
	$(PYTHON) -m pipeline.narration

keyframes:
	$(PYTHON) -m pipeline.keyframes

shots:
	$(PYTHON) -m pipeline.shots --backend ffmpeg

music:
	$(PYTHON) -m pipeline.music

assemble:
	$(PYTHON) -m pipeline.assemble
