from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import Provincia, Municipio, Endereco, Empresa, Filial, Funcionario
import re
from rest_framework.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from rest_framework import serializers
from django.db.models import Count, Sum, F
from apps.faturacao.models import  Stock


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

User = get_user_model()


class FilialSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.ReadOnlyField(source='empresa.nome_fantasia')
    endereco = EnderecoSerializer()
    
    # Campo para receber o contexto do request (será preenchido na view)
    empresa_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Filial
        fields = '__all__'
        read_only_fields = ['empresa', 'created_at', 'updated_at']

    def validate(self, data):
        """
        Validações adicionais
        """
        request = self.context.get('request')
        
        # Se não tem request, não valida permissão
        if not request or not request.user:
            return data
        
        user = request.user
        
        # Verifica se o usuário está autenticado
        if not user.is_authenticated:
            raise PermissionDenied("Usuário não autenticado.")
        
        # Verifica se o usuário tem perfil de funcionário
        if not hasattr(user, 'funcionario'):
            raise PermissionDenied("Usuário não tem perfil de funcionário.")
        
        funcionario = user.funcionario
        
        # Verifica se o usuário é SUPERADMIN
        if funcionario.papel != 'SUPERADMIN':
            raise PermissionDenied(
                "Apenas SUPERADMIN pode criar/editar filiais. "
                f"Seu papel atual: {funcionario.get_papel_display()}"
            )
        
        # Se for criação (sem instância), precisa da empresa
        if not self.instance:
            # Pega a empresa do funcionário logado
            empresa = funcionario.filial.empresa
            data['empresa'] = empresa
        
        return data

    @transaction.atomic
    def create(self, validated_data):
        endereco_data = validated_data.pop('endereco')
        endereco = Endereco.objects.create(**endereco_data)
        
        validated_data['endereco'] = endereco
        
        # A empresa já foi definida no validate
        filial = Filial.objects.create(**validated_data)
        return filial
    
    @transaction.atomic
    def update(self, instance, validated_data):
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



# apps/empresa/serializers/filial_serializer.py


class FuncionarioResumidoSerializer(serializers.ModelSerializer):
    """Serializer resumido para funcionários da filial"""
    nome_completo = serializers.ReadOnlyField(source='user.get_full_name')
    email = serializers.ReadOnlyField(source='user.email')
    
    class Meta:
        model = Funcionario
        fields = ['id', 'nome_completo', 'email', 'cargo', 'papel', 'ativo']


class StockProdutoSerializer(serializers.ModelSerializer):
    """Serializer para stock com dados do produto"""
    produto_nome = serializers.ReadOnlyField(source='produto.nome')
    produto_codigo = serializers.ReadOnlyField(source='produto.codigo')
    produto_categoria = serializers.ReadOnlyField(source='produto.categoria.nome')
    preco_venda = serializers.ReadOnlyField(source='produto.preco_venda')
    status_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Stock
        fields = [
            'id', 'produto', 'produto_nome', 'produto_codigo',
            'produto_categoria', 'quantidade', 'stock_minimo',
            'preco_venda', 'corredor', 'prateleira', 'status_stock'
        ]
    
    def get_status_stock(self, obj):
        """Retorna o status do stock baseado na quantidade"""
        if obj.quantidade <= 0:
            return {'status': 'ESGOTADO', 'cor': 'red', 'label': 'Esgotado'}
        elif obj.quantidade <= obj.stock_minimo:
            return {'status': 'STOCK_MINIMO', 'cor': 'yellow', 'label': 'Stock Mínimo'}
        else:
            return {'status': 'NORMAL', 'cor': 'green', 'label': 'Normal'}


class FilialDetailSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.ReadOnlyField(source='empresa.nome_fantasia')
    endereco = EnderecoSerializer()
    
    # Métricas
    total_funcionarios = serializers.SerializerMethodField()
    funcionarios_ativos = serializers.SerializerMethodField()
    total_produtos_stock = serializers.SerializerMethodField()
    produtos_com_stock_minimo = serializers.SerializerMethodField()
    produtos_esgotados = serializers.SerializerMethodField()
    valor_total_stock = serializers.SerializerMethodField()
    
    # Listas (incluir apenas se solicitado via query param)
    funcionarios = serializers.SerializerMethodField()
    stocks = serializers.SerializerMethodField()
    
    class Meta:
        model = Filial
        fields = [
            'id', 'nome', 'codigo_agt', 'e_sede', 'serie_documentos',
            'ativo', 'empresa', 'empresa_nome', 'endereco',
            'created_at', 'updated_at',
            # Métricas
            'total_funcionarios', 'funcionarios_ativos',
            'total_produtos_stock', 'produtos_com_stock_minimo',
            'produtos_esgotados', 'valor_total_stock',
            # Listas (opcionais)
            'funcionarios', 'stocks'
        ]
    
    def get_total_funcionarios(self, obj):
        """Retorna o total de funcionários da filial"""
        return obj.funcionarios.count()
    
    def get_funcionarios_ativos(self, obj):
        """Retorna a quantidade de funcionários ativos"""
        return obj.funcionarios.filter(ativo=True).count()
    
    def get_total_produtos_stock(self, obj):
        """Retorna o total de produtos com stock"""
        return obj.stocks.count()
    
    def get_produtos_com_stock_minimo(self, obj):
        """Retorna a quantidade de produtos com stock abaixo do mínimo"""
        return obj.stocks.filter(quantidade__lte=F('stock_minimo'), quantidade__gt=0).count()
    
    def get_produtos_esgotados(self, obj):
        """Retorna a quantidade de produtos esgotados"""
        return obj.stocks.filter(quantidade=0).count()
    
    def get_valor_total_stock(self, obj):
        """Retorna o valor total do stock (quantidade * preço_venda)"""
        total = obj.stocks.aggregate(
            total=Sum(F('quantidade') * F('produto__preco_venda'))
        )['total']
        return float(total) if total else 0.0
    
    def get_funcionarios(self, obj):
        """Retorna a lista de funcionários (apenas se solicitado)"""
        request = self.context.get('request')
        if request and request.query_params.get('include_funcionarios') == 'true':
            funcionarios = obj.funcionarios.select_related('user').all()
            return FuncionarioResumidoSerializer(funcionarios, many=True).data
        return None
    
    def get_stocks(self, obj):
        """Retorna a lista de stocks (apenas se solicitado)"""
        request = self.context.get('request')
        if request and request.query_params.get('include_stocks') == 'true':
            stocks = obj.stocks.select_related('produto', 'produto__categoria').all()
            return StockProdutoSerializer(stocks, many=True).data
        return None


class FilialResumoSerializer(serializers.ModelSerializer):
    """
    Serializer resumido para listagem de filiais (sem detalhes pesados)
    """
    empresa_nome = serializers.ReadOnlyField(source='empresa.nome_fantasia')
    total_funcionarios = serializers.SerializerMethodField()
    
    class Meta:
        model = Filial
        fields = [
            'id', 'nome', 'codigo_agt', 'e_sede', 'ativo',
            'empresa_nome', 'total_funcionarios', 'created_at'
        ]
    
    def get_total_funcionarios(self, obj):
        return obj.funcionarios.count()

# apps/empresa/serializers/funcionario_serializer.py

class FuncionarioSerializer(serializers.ModelSerializer):
    # ========== CAMPOS DE LEITURA (vêm do User) ==========
    # Estes campos são apenas para leitura na resposta da API
    nome_completo = serializers.ReadOnlyField(source='user.get_full_name')
    user_email = serializers.EmailField(source='user.email', read_only=True)
    first_name_read = serializers.CharField(source='user.first_name', read_only=True)
    last_name_read = serializers.CharField(source='user.last_name', read_only=True)
    user_name = serializers.ReadOnlyField(source='user.username')
    is_active = serializers.ReadOnlyField(source='user.is_active')
    
    # ========== CAMPOS DE ESCRITA (para criação/atualização) ==========
    # Estes campos são write_only e serão usados para criar/atualizar o User
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(write_only=True, required=True)
    password = serializers.CharField(
        write_only=True, 
        style={'input_type': 'password'}, 
        required=False,
        allow_blank=True
    )
    
    # ========== OUTROS CAMPOS ==========
    filial_nome = serializers.ReadOnlyField(source='filial.nome')
    empresa_nome = serializers.ReadOnlyField(source='filial.empresa.nome_fantasia')
    endereco = EnderecoSerializer(required=False, allow_null=True)
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Funcionario
        fields = [
            # Identificação
            'id', 'user', 'user_name',
            
            # Nome (leitura vs escrita)
            'first_name', 'last_name',           # escrita
            'first_name_read', 'last_name_read', # leitura
            'nome_completo',
            
            # Contacto
            'email',          # escrita
            'user_email',     # leitura
            'telemovel',
            
            # Dados profissionais
            'bi', 'cargo', 'papel', 'filial', 'filial_nome',
            'empresa_nome', 'ativo',
            
            # Endereço
            'endereco',
            
            # Senha
            'password',
            
            # Metadados
            'created_at', 'updated_at', 'is_active', 'status_display',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']
        extra_kwargs = {
            'user': {'read_only': True},
            'papel': {'required': False, 'default': 'OPERADOR'},
            'ativo': {'required': False, 'default': True},
            'filial': {'required': True},
            'bi': {'required': True},
            'cargo': {'required': True},
            'telemovel': {'required': True},
            'telemovel': {'required': True},
        }

    def get_status_display(self, obj):
        if not obj.ativo:
            return "Inativo"
        if obj.user and not obj.user.is_active:
            return "Usuário Inativo"
        return "Ativo"

    def to_representation(self, instance):
        """
        Personaliza a representação para incluir dados do User
        """
        ret = super().to_representation(instance)
        if instance.user:
            # Sobrescreve os campos de escrita com valores reais do User
            ret['first_name'] = instance.user.first_name
            ret['last_name'] = instance.user.last_name
            ret['email'] = instance.user.email
            # Remove os campos de leitura duplicados se não quiser
            # ret.pop('first_name_read', None)
            # ret.pop('last_name_read', None)
            # ret.pop('user_email', None)
        return ret

    # ========== VALIDAÇÕES ==========

    def validate_bi(self, value):
        if not value:
            raise ValidationError("O NIF/BI é obrigatório.")
        
        value = value.upper().strip()
        padrao_bi = r'^\d{9}[A-Z]{2}\d{3}$'
        if not re.match(padrao_bi, value):
            raise ValidationError(
                "Formato inválido. Use: 9 números + 2 letras + 3 números. "
                "Exemplo: 009876543BG001"
            )
        
        queryset = Funcionario.objects.filter(bi=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError("Este NIF/BI já está registado.")
        
        return value

    def validate_telemovel(self, value):
        if not value:
            raise ValidationError("O número de telefone é obrigatório.")
        
        apenas_numeros = ''.join(filter(str.isdigit, value))
        if apenas_numeros.startswith('244') and len(apenas_numeros) > 9:
            apenas_numeros = apenas_numeros[3:]

        if not re.match(r'^9\d{8}$', apenas_numeros):
            raise ValidationError(
                "Número inválido. Deve ser angolano, começar com 9 e ter 9 dígitos. "
                "Exemplo: 923456789"
            )
        
        queryset = Funcionario.objects.filter(telemovel=apenas_numeros)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError("Este número de telefone já está registado.")
        
        return apenas_numeros

    def validate_email(self, value):
        """Valida email (apenas para escrita)"""
        if not value:
            raise ValidationError("O email é obrigatório.")
        
        # Verifica unicidade no User
        queryset = User.objects.filter(email=value)
        if self.instance and self.instance.user:
            queryset = queryset.exclude(pk=self.instance.user.pk)
        
        if queryset.exists():
            raise ValidationError("Este email já está registado.")
        
        return value.lower()

    def validate_filial(self, value):
        if not value:
            raise ValidationError("A filial é obrigatória.")
        
        if not value.ativo:
            raise ValidationError("Não é possível associar a uma filial inativa.")
        
        return value

    def validate_papel(self, value):
        papeis_validos = ['SUPERADMIN', 'ADMIN', 'GESTOR', 'OPERADOR', 'CONTABILISTA']
        
        if not value:
            return 'OPERADOR'
        
        if value not in papeis_validos:
            raise ValidationError(f"Papel inválido. Opções: {', '.join(papeis_validos)}")
        
        return value

    # ========== CREATE ==========

    @transaction.atomic
    def create(self, validated_data):
        endereco_data = validated_data.pop('endereco', None)
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        email = validated_data.pop('email', None)
        password = validated_data.pop('password', None)
        
        if not email:
            raise ValidationError({"email": "O email é obrigatório para criar um funcionário."})
        
        # Cria o User
        user_data = {
            'username': email,
            'email': email,
            'first_name': first_name or '',
            'last_name': last_name or '',
        }
        
        if password:
            user = User.objects.create_user(**user_data, password=password)
        else:
            senha_temporaria = User.objects.make_random_password()
            user = User.objects.create_user(**user_data, password=senha_temporaria)
        
        # Cria o Endereço
        endereco = None
        if endereco_data:
            endereco = Endereco.objects.create(**endereco_data)
        
        # Cria o Funcionário
        funcionario = Funcionario.objects.create(
            user=user,
            endereco=endereco,
            **validated_data
        )
        
        return funcionario

    # ========== UPDATE ==========

    @transaction.atomic
    def update(self, instance, validated_data):
        endereco_data = validated_data.pop('endereco', None)
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        email = validated_data.pop('email', None)
        password = validated_data.pop('password', None)
        
        # 1. Atualiza User
        user = instance.user
        if user:
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if email is not None:
                user.email = email
                user.username = email
            if password:
                user.set_password(password)
            user.save()
        
        # 2. Atualiza Endereço
        if endereco_data is not None:
            if instance.endereco:
                for attr, value in endereco_data.items():
                    setattr(instance.endereco, attr, value)
                instance.endereco.save()
            elif endereco_data:
                instance.endereco = Endereco.objects.create(**endereco_data)
        
        # 3. Atualiza Funcionário
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


# Serializers simplificados para listagem e detalhe
class FuncionarioListSerializer(serializers.ModelSerializer):
    nome_completo = serializers.ReadOnlyField(source='user.get_full_name')
    email = serializers.ReadOnlyField(source='user.email')
    filial_nome = serializers.ReadOnlyField(source='filial.nome')
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Funcionario
        fields = ['id', 'nome_completo', 'email', 'bi', 'cargo', 
                  'papel', 'ativo', 'telemovel', 'filial_nome', 
                  'created_at', 'status_display']
    
    def get_status_display(self, obj):
        if not obj.ativo:
            return "Inativo"
        return "Ativo"


class FuncionarioDetailSerializer(FuncionarioSerializer):
    """Reutiliza o serializer principal para detalhes"""
    pass