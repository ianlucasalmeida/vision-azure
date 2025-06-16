#!/bin/bash
# Cria e ativa ambiente virtual
cd backend/functions
python -m venv .venv
source .venv/bin/activate

# Instala dependências
pip install -r requirements.txt

# Configura PYTHONPATH para módulos compartilhados
echo "export PYTHONPATH=\"$PYTHONPATH:$(pwd)/../shared\"" >> .venv/bin/activate