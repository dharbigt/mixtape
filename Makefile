.PHONY: venv install run clean help

help:
	@echo "Available commands:"
	@echo "  make activate  - Initialize environment for CLI"
	@echo "  make perms     - Set permissions"
	@echo "  make venv      - Create Python virtual environment"
	@echo "  make install   - Install dependencies"
	@echo "  make run       - Run Flask development server"
	@echo "  make clean     - Remove cache files"
	@echo "  make db-init   - Initialize database"

activate:
	./geo/bin/activate

venv:
	python3 -m venv geo

install: venv
	./geo/bin/pip install --upgrade pip
	./geo/bin/pip install -r requirements.txt

perms:
	@echo Setting permissions...
	@touch index.wsgi
	@chmod 755 geo
	@chmod 755 geo/bin/python geo/bin/python3 2>/dev/null || true
	@chmod 755 geo/bin/activate geo/bin/pip geo/bin/pip3 2>/dev/null || true
	@chmod -R u+rX,g+rX,o+rX geo/lib 2>/dev/null || true
	@chmod 644 index.wsgi
	@chmod -R 755 app/
	@chmod -R 644 app/__init__.py app/config.py app/routes.py app/models.py 2>/dev/null || true
	@chmod -R 755 app/templates app/static 2>/dev/null || true
	@chmod -R 644 app/templates/*.html 2>/dev/null || true
	@chmod 2775 app/static/tracks/
	@chmod 644 requirements.txt Makefile run.py
	@echo All set.

run: 
	./geo/bin/python run.py

db-init:
	./geo/bin/python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Database initialized')"

clean:
	find . -name '._*' -delete
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -f .DS_Store

migrate:	clean
	@echo Migrating db...
	@./geo/bin/python3 -m flask db migrate

upgrade:	clean
	@echo Upgrading db...
	@./geo/bin/python3 -m flask db upgrade
