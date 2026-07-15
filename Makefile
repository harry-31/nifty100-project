load:
	python -m src.etl.db_loader

test:
	pytest -v

report:
	python audit.py

clean:
	del nifty100.db