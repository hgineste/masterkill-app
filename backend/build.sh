#!/usr/bin/env bash
set -o errexit # Arrête le script si une commande échoue

echo "--- Running pip install ---"
pip install -r requirements.txt

echo "--- Running manage.py migrate ---"
python manage.py migrate # Exécute les migrations en premier

echo "--- Running manage.py collectstatic ---"
python manage.py collectstatic --no-input --clear # --clear pour nettoyer avant

echo "--- Build script finished ---"