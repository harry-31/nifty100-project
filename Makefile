load:
	python -m src.etl.db_loader

ratios:
	python -m src.analytics.ratio_loader

test:
	pytest -v

report:
	python audit.py

dashboard:
	streamlit run src/dashboard/app.py

api:
	uvicorn src.api.main:app --reload

clean:
	Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
	Get-ChildItem -Recurse -File -Include *.pyc,*.pyo | Remove-Item -Force
