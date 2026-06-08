#!/bin/bash

# Instalar dependências
pip install -r requirements.txt

# Coletar ficheiros estáticos
python manage.py collectstatic --noinput

# Executar migrações
python manage.py migrate --noinput

# Criar superutilizador (opcional - só se não existir)
# python manage.py createsuperuser --noinput --username admin --email admin@example.com || true