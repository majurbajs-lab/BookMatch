#!/bin/bash
# BookMatch - avtomatski trening ML modelov
# Nastavite USERNAME in PYTHON_PATH pred zagonom

USERNAME="BookMatch"
PROJECT_DIR="/home/$USERNAME/BookMatch"
PYTHON="$PROJECT_DIR/venv/bin/python"

echo "=== BookMatch ML trening: $(date) ==="

echo "--- train_recommender ---"
$PYTHON "$PROJECT_DIR/manage.py" train_recommender
echo "--- train_matcher ---"
$PYTHON "$PROJECT_DIR/manage.py" train_matcher

echo "=== Konec: $(date) ==="
