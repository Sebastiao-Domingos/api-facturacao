# 🚀 Facturacão API - Core Engine

![Django](https://img.shields.io/badge/django-%23092E20.svg?style=for-the-badge&logo=django&logoColor=white)
![DjangoREST](https://img.shields.io/badge/DJANGO-REST-ff1709?style=for-the-badge&logo=django&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-black?style=for-the-badge&logo=JSON%20web%20tokens)
![PostgreSQL](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)

Backend robusto e escalável para sistemas de gestão e faturação, desenvolvido com **Python/Django**, focado na conformidade com as regras fiscais de Angola (**AGT**).

## 🛠️ Tecnologias e Arquitetura

- **Core:** Django 6.0 + Django REST Framework.
- **Segurança:** Autenticação via **SimpleJWT** e Custom User Model.
- **Identificadores:** Utilização global de **UUID** (v4) em vez de IDs incrementais.
- **Base de Dados:** Preparado para PostgreSQL (SQLite em desenvolvimento).
- **Padrão de Dados:** Validações rigorosas para NIF, BI e Telemóveis (Angola).

## ✨ Funcionalidades Concluídas (Fase 1)

### 🏢 Organização & Localização

- **Estrutura Multi-Filial:** Suporte para uma empresa com múltiplas filiais (Sede e Lojas).
- **Geografia Integrada:** Base de dados pré-povoada com todas as Províncias e Municípios de Angola.
- **Criação Atómica:** Endpoint inteligente que cria Empresa + Endereço + Filial Sede num único pedido.

### 👤 Gestão de Acessos

- **Perfis Dinâmicos:** Papéis de utilizador (`SUPERADMIN`, `ADMIN`, `OPERADOR`).
- **Endpoint `/me`:** Identificação imediata do funcionário logado e seu contexto de trabalho.
- **Registo Simplificado:** Criação simultânea de Conta de Utilizador, Endereço e Perfil de Funcionário.

## 🚀 Como Começar

### 1. Clonar e Instalar

```bash
git clone [https://github.com/teu-utilizador/teu-projeto.git](https://github.com/teu-utilizador/teu-projeto.git)
cd teu-projeto
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```
