#!/usr/bin/env bash
set -e

mkdir -p projeto/{docs,src/{game,hardware,education,monitoring},data,tests,assets/{images,sounds},scripts}
touch projeto/src/__init__.py
touch projeto/src/game/__init__.py
touch projeto/src/hardware/__init__.py
touch projeto/src/education/__init__.py
touch projeto/src/monitoring/__init__.py

echo "Estrutura criada em ./projeto"
