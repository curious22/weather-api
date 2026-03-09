run:
	python manage.py runserver

install-deps:
	pip install -r requirements-dev.txt
	pre-commit install
