# apps/organizacao/models/__init__.py

from .localizacao import Provincia, Municipio, Endereco
from .empresa import Empresa, Filial
from .funcionario import Funcionario
from .base import BaseModel # Se criaste o base.py lá dentro