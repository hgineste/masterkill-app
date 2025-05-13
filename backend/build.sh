#!/usr/bin/env bash
set -o errexit 
set -o nounset 
set -o pipefail 

echo "--- [BUILD SCRIPT] Running pip install ---"
pip install -r requirements.txt

echo "--- [BUILD SCRIPT] Running manage.py migrate ---"
python manage.py migrate # Si cette commande échoue, le "set -o errexit" devrait arrêter le script

echo "--- [BUILD SCRIPT] Running manage.py collectstatic ---"
python manage.py collectstatic --no-input --clear 

echo "--- [BUILD SCRIPT] Build script finished successfully ---"