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
            'municipio_nome', 'provincia_nome','created_at', 'updated_at', "provincia_id"
        ]


class EmpresaSerializer(serializers.ModelSerializer):
    # Campo para receber os dados do endereço da sede
    endereco_data = EnderecoSerializer(write_only=True)
    
    # Detalhes para leitura (o que volta para o front)
    endereco = EnderecoSerializer( read_only=True)

    class Meta:
        model = Empresa
        fields = [
            'id', 'nome_fantasia', 'razao_social', 'nif', 
            'logotipo', 'endereco_data', 'endereco',"moeda_padrao", "regime_tributario",
            'created_at', 'updated_at'
        ]

    @transaction.atomic
    def create(self, validated_data):
        # 1. Extrair os dados do endereço
        endereco_data = validated_data.pop('endereco_data')

        # 2. Criar o Endereço Sede
        endereco_sede = Endereco.objects.create(**endereco_data)

        # 3. Criar a Empresa ligada a esse endereço
        empresa = Empresa.objects.create(
            endereco=endereco_sede,
            **validated_data
        )

        # 4. CRIAR AUTOMATICAMENTE A PRIMEIRA FILIAL (SEDE)
        # Isso garante que a empresa já nasce com um local de venda
        Filial.objects.create(
            empresa=empresa,
            nome=f"Sede - {empresa.nome_fantasia}",
            endereco=endereco_sede,
            e_sede=True,
            codigo_agt="1" # Código inicial padrão para a AGT
        )

        return empresa
    
    def validate_nif(self, value):

        if not re.match(r'^[0-9A-Z]{9,14}$', value):
            raise ValidationError("O NIF introduzido não parece ser um NIF angolano válido.")
        return value.upper()


class FilialSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.ReadOnlyField(source='empresa.nome_fantasia')
    endereco = EnderecoSerializer()
    # endereco_data = EnderecoSerializer(write_only=True)

    class Meta:
        model = Filial
        fields = "__all__"

    
    def create(self, validated_data):
        endereco_data = validated_data.pop('endereco')
        endereco = Endereco.objects.create(**endereco_data)
        validated_data['endereco'] = endereco

        filial = Filial.objects.create(**validated_data)

        filial.save()

        return filial

User = get_user_model()

class FuncionarioSerializer(serializers.ModelSerializer):
        # Campos para receber os dados do utilizador
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    # Campos para receber os dados do endereço (aninhado)
    endereco_data = EnderecoSerializer(write_only=True)
    
    # Campos de leitura que já tinhas
    nome_completo = serializers.ReadOnlyField(source='user.get_full_name')
    user = serializers.ReadOnlyField(source='user.email')
    filial_nome = serializers.ReadOnlyField(source='filial.nome')
    endereco= EnderecoSerializer( read_only=True)



    class Meta:
        model = Funcionario
        fields = "__all__"
        # Opcional: podes definir o user como obrigatório explicitamente
        extra_kwargs = {
            'user': {'required': True}
        }

    def validate_bi(self, value):
        # BI Angola: 9 dígitos + 2 letras + 3 dígitos (Ex: 000573455UE067)
        padrao_bi = r'^\d{9}[A-Z]{2}\d{3}$'
        if not re.match(padrao_bi, value.upper()):
            raise ValidationError("O formato do BI deve ser 000000000XX000 (9 números, 2 letras, 3 números).")
        return value.upper()


    def validate_telemovel(self, value):
        # 1. Remover espaços ou caracteres especiais caso o frontend envie (ex: "+244", "-", " ")
        # Mantemos apenas os dígitos
        apenas_numeros = ''.join(filter(str.isdigit, value))

        # 2. Se o número começar com 244, removemos para validar o corpo do número
        if apenas_numeros.startswith('244') and len(apenas_numeros) > 9:
            apenas_numeros = apenas_numeros[3:]

        # 3. Validar se tem exatamente 9 dígitos e começa com 9
        if not re.match(r'^9\d{8}$', apenas_numeros):
            raise ValidationError(
                "O número de telefone deve ser angolano, começar com 9 e ter 9 dígitos (ex: 923000000)."
            )
        
        return apenas_numeros
    


    @transaction.atomic
    def create(self, validated_data):
        # 1. Extrair dados aninhados
        endereco_data = validated_data.pop('endereco_data')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # 2. Criar o User (CustomUser com UUID)
        user = User.objects.create_user(
            username=email, # Usamos o email como username
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # 3. Criar o Endereço
        endereco = Endereco.objects.create(**endereco_data)

        # 4. Criar o Funcionário ligando ao User e Endereço criados
        funcionario = Funcionario.objects.create(
            user=user,
            endereco=endereco,
            **validated_data
        )

        return funcionario
    






