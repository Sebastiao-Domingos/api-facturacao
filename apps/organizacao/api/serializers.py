from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import Provincia, Municipio, Endereco, Empresa, Filial, Funcionario
import re
from rest_framework.exceptions import ValidationError
from django.db import transaction


# --- LOCALIZAÇÃO ---
class ProvinciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provincia
        fields = ['id', 'nome', 'created_at', 'updated_at']

class MunicipioSerializer(serializers.ModelSerializer):
    provincia_nome = serializers.ReadOnlyField(source='provincia.nome')

    class Meta:
        model = Municipio
        fields = ['id', 'nome', 'provincia', 'provincia_nome', 'created_at', 'updated_at']


class EnderecoSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.ReadOnlyField(source='municipio.nome')
    provincia_nome = serializers.ReadOnlyField(source='municipio.provincia.nome')
    provincia_id = serializers.ReadOnlyField(source='municipio.provincia.id')

    class Meta:
        model = Endereco
        fields = [
            'id', 'bairro', 'rua', 'ponto_referencia', 
            'longitude', 'latitude', 'municipio', 
            'municipio_nome', 'provincia_nome', 'created_at', 'updated_at', "provincia_id"
        ]


# --- EMPRESA ---
class EmpresaSerializer(serializers.ModelSerializer):
    endereco_data = EnderecoSerializer(write_only=True)
    endereco = EnderecoSerializer(read_only=True)

    class Meta:
        model = Empresa
        fields = [
            'id', 'nome_fantasia', 'razao_social', 'nif', 
            'logotipo', 'endereco_data', 'endereco', "moeda_padrao", "regime_tributario",
            'created_at', 'updated_at'
        ]

    @transaction.atomic
    def create(self, validated_data):
        endereco_data = validated_data.pop('endereco_data')
        endereco_sede = Endereco.objects.create(**endereco_data)

        empresa = Empresa.objects.create(
            endereco=endereco_sede,
            **validated_data
        )

        # Garante a criação da Filial Sede vinculada
        Filial.objects.create(
            empresa=empresa,
            nome=f"Sede - {empresa.nome_fantasia}",
            endereco=endereco_sede,
            e_sede=True,
            codigo_agt="1"
        )
        return empresa

    @transaction.atomic
    def update(self, instance, validated_data):
        """[ADICIONADO] Permite atualizar os dados da Empresa e do seu Endereço Sede"""
        endereco_data = validated_data.pop('endereco_data', None)

        # 1. Atualizar Endereço se enviado
        if endereco_data and instance.endereco:
            for attr, value in endereco_data.items():
                setattr(instance.endereco, attr, value)
            instance.endereco.save()

        # 2. Atualizar dados nativos da Empresa
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
    
    def validate_nif(self, value):
        if not re.match(r'^[0-9A-Z]{9,14}$', value):
            raise ValidationError("O NIF introduzido não parece ser um NIF angolano válido.")
        return value.upper()


# --- FILIAL ---
class FilialSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.ReadOnlyField(source='empresa.nome_fantasia')
    endereco = EnderecoSerializer() # Reutilizado tanto para escrita como leitura

    class Meta:
        model = Filial
        fields = "__all__"

    @transaction.atomic
    def create(self, validated_data):
        endereco_data = validated_data.pop('endereco')
        endereco = Endereco.objects.create(**endereco_data)
        
        validated_data['endereco'] = endereco
        filial = Filial.objects.create(**validated_data)
        return filial
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """[CORRIGIDO] Assinatura correta (instance, validated_data) e suporte a atualização aninhada"""
        endereco_data = validated_data.pop('endereco', None)

        # 1. Tratar atualização do Endereço da Filial
        if endereco_data and instance.endereco:
            for attr, value in endereco_data.items():
                setattr(instance.endereco, attr, value)
            instance.endereco.save()

        # 2. Tratar os restantes campos da Filial
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


# --- FUNCIONÁRIO ---
User = get_user_model()

class FuncionarioSerializer(serializers.ModelSerializer):
    # Declarados como campos normais (sem write_only nem read_only) para aceitarem leitura E escrita
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    
    # Password continua oculta por questões óbvias de segurança de dados
    password = serializers.CharField(write_only=True, style={'input_type': 'password'}, required=False)
    
    # Campos estritamente de leitura do User e Filial
    user_name = serializers.ReadOnlyField(source='user.username')
    nome_completo = serializers.ReadOnlyField(source='user.get_full_name')
    is_active = serializers.ReadOnlyField(source='user.is_active')
    filial_nome = serializers.ReadOnlyField(source='filial.nome')
    
    endereco = EnderecoSerializer()

    class Meta:
        model = Funcionario
        fields = [
            'id', 'user', 'user_name', 'first_name', 'last_name', 'email', 'password', 'nome_completo', 'is_active',
            'telemovel', 'bi', 'cargo', 'filial', 'filial_nome', 
            'endereco', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'user': {'read_only': True, 'required': False}
        }

    def to_representation(self, instance):
        """
        [CRUCIAL] Este método injeta os valores reais do User nos campos da raiz 
        quando a API responde a um GET, simulando uma tabela única para o Next.js.
        """
        ret = super().to_representation(instance)
        if instance.user:
            ret['first_name'] = instance.user.first_name
            ret['last_name'] = instance.user.last_name
            ret['email'] = instance.user.email
        return ret

    def validate_bi(self, value):
        padrao_bi = r'^\d{9}[A-Z]{2}\d{3}$'
        if not re.match(padrao_bi, value.upper()):
            raise ValidationError("O formato do BI deve ser 000000000XX000 (9 números, 2 letras, 3 números).")
        return value.upper()

    def validate_telemovel(self, value):
        apenas_numeros = ''.join(filter(str.isdigit, value))
        if apenas_numeros.startswith('244') and len(apenas_numeros) > 9:
            apenas_numeros = apenas_numeros[3:]

        if not re.match(r'^9\d{8}$', apenas_numeros):
            raise ValidationError("O número de telefone deve ser angolano, começar com 9 e ter 9 dígitos.")
        return apenas_numeros

    @transaction.atomic
    def create(self, validated_data):
        endereco_data = validated_data.pop('endereco')
        
        # Extrai com segurança os dados do utilizador
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        email = validated_data.pop('email')
        password = validated_data.pop('password', None)

        # Criação do User de autenticação
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Criação da entidade geográfica
        endereco = Endereco.objects.create(**endereco_data)

        # Instanciação do Funcionário
        funcionario = Funcionario.objects.create(
            user=user,
            endereco=endereco,
            **validated_data
        )
        return funcionario

    @transaction.atomic
    def update(self, instance, validated_data):
        """Atualiza com sucesso os dados do Funcionário, do seu Endereço e do User associado"""
        endereco_data = validated_data.pop('endereco', None)
        
        # Captura os dados do utilizador enviados na raiz do JSON
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        email = validated_data.pop('email', None)
        password = validated_data.pop('password', None)

        # 1. Atualizar dados de Autenticação (User do Django)
        user = instance.user
        if user:
            if first_name is not None: user.first_name = first_name
            if last_name is not None: user.last_name = last_name
            if email is not None:
                user.email = email
                user.username = email # Mantém o login sincronizado ao alterar o email
            if password:
                user.set_password(password)
            user.save()

        # 2. Atualizar dados de Localização (Endereço)
        if endereco_data and instance.endereco:
            for attr, value in endereco_data.items():
                setattr(instance.endereco, attr, value)
            instance.endereco.save()

        # 3. Atualizar dados da Ficha de Funcionário
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance