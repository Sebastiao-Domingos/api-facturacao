from django.db import transaction
from django.contrib.auth.models import User
from .models import Endereco, Funcionario

class FuncionarioService:
    @staticmethod
    @transaction.atomic
    def criar_funcionario(user_data, funcionario_data, endereco_data):
        """
        Cria um utilizador completo: Conta + Endereço + Perfil de Funcionário.
        user_data: dict com username, email, password, first_name, last_name
        funcionario_data: dict com filial, bi, cargo, telemovel, papel
        endereco_data: dict com bairro, rua, municipio (objeto ou ID)
        """
        
        # 1. Criar o Endereço
        endereco = Endereco.objects.create(**endereco_data)
        
        # 2. Criar a Conta de Utilizador (User)
        user = User.objects.create_user(
            username=user_data['email'], # Usamos o email como username
            email=user_data['email'],
            password=user_data['password'],
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', '')
        )
        
        # 3. Criar o Perfil do Funcionário ligado ao User e ao Endereço
        funcionario = Funcionario.objects.create(
            user=user,
            endereco=endereco,
            **funcionario_data
        )
        
        return funcionario