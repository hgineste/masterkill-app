#!/usr/bin/env bash
set -o errexit  # Arrête le script si une commande échoue
set -o nounset  # Traite les variables non définies comme une erreur
set -o pipefail # Fait échouer le pipeline si une commande dans le pipeline échoue

echo "--- [BUILD SCRIPT] Running pip install ---"
pip install -r requirements.txt

echo "--- [BUILD SCRIPT] Running manage.py migrate ---"
python manage.py migrate # Si cette commande échoue, le "set -o errexit" DEVRAIT arrêter le script
MIGRATE_STATUS=$? 
if [ $MIGRATE_STATUS -ne 0 ]; then
    echo "!!!! [BUILD SCRIPT] manage.py migrate FAILED with status: $MIGRATE_STATUS !!!!"
    exit $MIGRATE_STATUS # Force explicitement la sortie avec un code d'erreur
else
    echo "--- [BUILD SCRIPT] manage.py migrate SUCCEEDED ---"
fi

echo "--- [BUILD SCRIPT] Running manage.py collectstatic ---"
python manage.py collectstatic --no-input --clear

echo "--- [BUILD SCRIPT] Build script finished successfully ---"