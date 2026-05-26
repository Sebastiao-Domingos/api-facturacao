from rest_framework import serializers
from ..models import Categoria, UnidadeMedida, TaxaIva, Produto, Stock, MovimentacaoStock, SerieDocumento, LinhaDocumento , Pagamento,Documento
from django.db import transaction, models
from rest_framework.exceptions import ValidationError
# apps/faturacao/serializers.py
from django.utils import timezone
from apps.organizacao.models import  Filial
from apps.clientes.models import  Cliente

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nome', 'descricao']

class UnidadeMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeMedida
        fields = ['id', 'sigla', 'nome']

class TaxaIvaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxaIva
        fields = ['id', 'codigo', 'valor', 'descricao', 'motivo_isencao', 'codigo_isencao_agt']

class ProdutoSerializer(serializers.ModelSerializer):
    # Campos detalhados para leitura
    categoria_detalhes = CategoriaSerializer(source='categoria', read_only=True)
    unidade_detalhes = UnidadeMedidaSerializer(source='unidade_medida', read_only=True)
    taxa_detalhes = TaxaIvaSerializer(source='taxa_iva', read_only=True)

    class Meta:
        model = Produto
        fields = [
            'id', 'nome', 'tipo', 'imagem', 'categoria', 'categoria_detalhes',
            'unidade_medida', 'unidade_detalhes', 'taxa_iva', 'taxa_detalhes',
            'preco_venda', 'codigo_barras', 'ref_interna', 'ativo' , "thumbnail"
        ]
        read_only_fields = ['codigo_barras'] # O backend gera, o front não deve enviar

    def validate(self, data):
        """Validação cruzada: Regra de Isenção AGT"""
        taxa = data.get('taxa_iva')
        # No POST/PUT, data['taxa_iva'] é o objeto TaxaIva
        if taxa and taxa.valor == 0:
            if not taxa.motivo_isencao or not taxa.codigo_isencao_agt:
                raise serializers.ValidationError({
                    "taxa_iva": "Para itens isentos (0%), a taxa selecionada deve ter um motivo e código de isenção configurados."
                })
        return data

class StockSerializer(serializers.ModelSerializer):
    produto_nome = serializers.ReadOnlyField(source='produto.nome')
    filial_nome = serializers.ReadOnlyField(source='filial.nome')
    produto_detalhes = ProdutoSerializer(source = "produto" , read_only = True)

    class Meta:
        model = Stock
        fields = [
            'id', 'produto', 'produto_nome', 
            'filial', 'filial_nome', 'quantidade', 'stock_minimo', "produto_detalhes", 
        ]


class MovimentacaoStockSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    data = serializers.DateTimeField(source='created_at', format='%Y-%m-%dT%H:%M:%SZ', read_only=True)
    
    # Campo aninhado dinâmico que vai retornar o objeto com ID e Nome
    operador_detalhes = serializers.SerializerMethodField()

    class Meta:
        model = MovimentacaoStock
        fields = [
            'id',
            'stock_filial',
            'tipo',
            'tipo_display',
            'quantidade',
            'origem_destino',
            'operador_detalhes',  # <--- Novo objeto estruturado
            'data'
        ]

    def get_operador_detalhes(self, obj):
        """
        Retorna o ID e o Nome do operador de forma garantida.
        Se o nome completo estiver vazio, faz fallback para o username.
        """
        user = obj.operador
        if not user:
            return None
            
        # Tenta obter o nome completo
        nome_completo = f"{user.first_name} {user.last_name}".strip()
        
        # Se o nome completo estiver vazio, usa o username (ou o email se preferires)
        if not nome_completo:
            nome_completo = getattr(user, 'username', 'Sistema')

        return {
            "id": str(user.id),
            "nome": nome_completo
        }


class ExecutarMovimentacaoSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=['E', 'S'])
    quantidade = serializers.DecimalField(max_digits=12, decimal_places=3)
    origem_destino = serializers.CharField(max_length=255)

    def validate(self, data):
        """
        Validações de regras de negócio antes de executar a mutação.
        """
        tipo = data.get('tipo')
        quantidade = data.get('quantidade')

        # 1. Impedir movimentações com valores zero ou negativos enviados no payload
        if quantidade <= 0:
            raise ValidationError({
                "quantidade": "A quantidade movimentada deve ser estritamente superior a zero."
            })

        # Recuperamos o registo de stock que foi passado no contexto da view
        stock_filial = self.context.get('stock_filial')
        
        if stock_filial and tipo == 'S':
            # 2. Regra de Ouro: Impedir que o stock fique negativo numa Saída
            if stock_filial.quantidade < quantidade:
                raise ValidationError({
                    "quantidade": f"Rutura de Stock! Operação rejeitada. Stock atual disponível: {stock_filial.quantidade}, mas tentou retirar: {quantidade}."
                })

        return data

    def save(self, stock_filial, operador):
        tipo = self.validated_data['tipo']
        quantidade = self.validated_data['quantidade']
        origem_destino = self.validated_data['origem_destino']

        with transaction.atomic():
            # Executa a operação matemática com segurança
            if tipo == 'E':
                stock_filial.quantidade += quantidade
            elif tipo == 'S':
                stock_filial.quantidade -= quantidade
            
            stock_filial.save()

            # Grava o histórico imutável
            movimentacao = MovimentacaoStock.objects.create(
                stock_filial=stock_filial,
                tipo=tipo,
                quantidade=quantidade,
                origem_destino=origem_destino,
                operador=operador
            )
            
        return movimentacao




class LinhaDocumentoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.ReadOnlyField(source='produto.nome')
    produto_codigo = serializers.ReadOnlyField(source='produto.codigo_barras')
    subtotal = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    valor_iva = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = LinhaDocumento
        fields = [
            'id', 'produto', 'produto_nome', 'produto_codigo',
            'descricao', 'quantidade', 'preco_unitario', 'desconto_pct',
            'taxa_iva', 'subtotal', 'valor_iva', 'total'
        ]
        read_only_fields = ['subtotal', 'valor_iva', 'total']


class PagamentoSerializer(serializers.ModelSerializer):
    metodo_display = serializers.ReadOnlyField(source='get_metodo_display')
    operador_nome = serializers.ReadOnlyField(source='operador.get_full_name')
    
    class Meta:
        model = Pagamento
        fields = [
            'id', 'valor', 'metodo', 'metodo_display',
            'referencia', 'data_pagamento', 'operador', 'operador_nome'
        ]
        read_only_fields = ['data_pagamento', 'operador']


class DocumentoListSerializer(serializers.ModelSerializer):
    tipo_display = serializers.ReadOnlyField(source='get_tipo_display')
    estado_display = serializers.ReadOnlyField(source='get_estado_display')
    cliente_nome = serializers.ReadOnlyField(source='cliente.nome')
    cliente_nif = serializers.ReadOnlyField(source='cliente.nif')
    filial_nome = serializers.ReadOnlyField(source='filial.nome')
    saldo_pendente = serializers.ReadOnlyField()
    
    class Meta:
        model = Documento
        fields = [
            'id', 'numero', 'tipo', 'tipo_display', 'estado', 'estado_display',
            'cliente', 'cliente_nome', 'cliente_nif', 'filial', 'filial_nome',
            'subtotal', 'total_iva', 'total', 'total_pago', 'saldo_pendente',
            'data_emissao', 'data_vencimento'
        ]


class DocumentoDetailSerializer(serializers.ModelSerializer):
    tipo_display = serializers.ReadOnlyField(source='get_tipo_display')
    estado_display = serializers.ReadOnlyField(source='get_estado_display')
    saldo_pendente = serializers.ReadOnlyField()
    linhas = LinhaDocumentoSerializer(many=True, read_only=True)
    pagamentos = PagamentoSerializer(many=True, read_only=True)
    
    cliente = serializers.SerializerMethodField()
    filial = serializers.SerializerMethodField()
    
    class Meta:
        model = Documento
        fields = [
            'id', 'numero', 'tipo', 'tipo_display', 'estado', 'estado_display',
            'cliente', 'filial', 'subtotal', 'total_iva', 'total',
            'total_pago', 'saldo_pendente', 'data_emissao', 'data_vencimento',
            'observacao', 'linhas', 'pagamentos', 'created_at'
        ]
    
    def get_cliente(self, obj):
        return {
            'id': str(obj.cliente.id),
            'nome': obj.cliente.nome,
            'nif': obj.cliente.nif,
            'email': obj.cliente.email,
            'telefone': obj.cliente.telefone,
        } if obj.cliente else None
    
    def get_filial(self, obj):
        return {
            'id': str(obj.filial.id),
            'nome': obj.filial.nome,
        } if obj.filial else None

from decimal import Decimal

class DocumentoCreateSerializer(serializers.Serializer):
    cliente_id = serializers.UUIDField(required=True)
    filial_id = serializers.UUIDField(required=True)
    tipo = serializers.ChoiceField(choices=Documento.TIPO_CHOICES)
    data_vencimento = serializers.DateField(required=False, allow_null=True)
    observacao = serializers.CharField(required=False, allow_blank=True)
    linhas = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        min_length=1
    )

    def validate_cliente_id(self, value):
        try:
            cliente = Cliente.objects.get(id=value, ativo=True)
            return cliente
        except Cliente.DoesNotExist:
            raise serializers.ValidationError("Cliente não encontrado ou inativo")

    def validate_filial_id(self, value):
        try:
            filial = Filial.objects.get(id=value, ativo=True)
            return filial
        except Filial.DoesNotExist:
            raise serializers.ValidationError("Filial não encontrada ou inativa")

    def validate_linhas(self, value):
        if not value:
            raise serializers.ValidationError("Adicione pelo menos um item")

        for idx, linha in enumerate(value):
            if 'produto' not in linha:
                raise serializers.ValidationError(f"Produto não informado na linha {idx + 1}")

            produto_id = linha['produto']
            try:
                produto = Produto.objects.get(id=produto_id, ativo=True)
                linha['produto_obj'] = produto   # guarda o objeto
            except Produto.DoesNotExist:
                raise serializers.ValidationError(f"Produto não encontrado na linha {idx + 1}")

            # Converte valores numéricos para Decimal
            try:
                linha['quantidade'] = Decimal(str(linha.get('quantidade', 0)))
                linha['preco_unitario'] = Decimal(str(linha.get('preco_unitario', 0)))
                linha['desconto_pct'] = Decimal(str(linha.get('desconto_pct', 0)))
            except (TypeError, ValueError):
                raise serializers.ValidationError(f"Valor numérico inválido na linha {idx + 1}")

            if linha['quantidade'] <= 0:
                raise serializers.ValidationError(f"Quantidade inválida na linha {idx + 1}")

        return value

    @transaction.atomic
    def create(self, validated_data):
        from apps.faturacao.utils import NumeroDocumentoGenerator

        cliente = validated_data['cliente_id']
        filial = validated_data['filial_id']
        tipo = validated_data['tipo']
        linhas_data = validated_data['linhas']

        # Obtém ou cria a série de documento
        serie, _ = SerieDocumento.objects.get_or_create(
            filial=filial,
            tipo=tipo,
            defaults={
                'prefixo': 'FAT' if tipo == 'FACTURA' else 'PRO',
                'numero_atual': 0,
                'ativo': True
            }
        )

        numero = NumeroDocumentoGenerator.gerar_numero(filial.id, tipo)

        documento = Documento.objects.create(
            serie=serie,
            numero=numero,
            tipo=tipo,
            estado='RASCUNHO',
            cliente=cliente,
            filial=filial,
            data_vencimento=validated_data.get('data_vencimento'),
            observacao=validated_data.get('observacao', '')
        )

        subtotal = Decimal('0')
        total_iva = Decimal('0')
        CEM = Decimal('100')
        UM = Decimal('1')

        for linha_data in linhas_data:
            produto = linha_data['produto_obj']
            quantidade = linha_data['quantidade']
            preco_unitario = linha_data['preco_unitario']
            desconto_pct = linha_data['desconto_pct']

            # Cálculos com Decimal
            subtotal_linha = quantidade * preco_unitario * (UM - desconto_pct / CEM)
            taxa_iva = produto.taxa_iva.valor  # já é Decimal
            valor_iva_linha = subtotal_linha * (taxa_iva / CEM)
            total_linha = subtotal_linha + valor_iva_linha

            LinhaDocumento.objects.create(
                documento=documento,
                produto=produto,
                descricao=produto.nome,
                codigo_barras=produto.codigo_barras,
                quantidade=quantidade,
                preco_unitario=preco_unitario,
                desconto_pct=desconto_pct,
                taxa_iva=taxa_iva,
                subtotal=subtotal_linha,
                valor_iva=valor_iva_linha,
                total=total_linha
            )

            subtotal += subtotal_linha
            total_iva += valor_iva_linha

        documento.subtotal = subtotal
        documento.total_iva = total_iva
        documento.total = subtotal + total_iva
        documento.save()

        return documento

class PagamentoCreateSerializer(serializers.Serializer):
    """Serializer para criação de pagamento"""
    valor = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0.01)
    metodo = serializers.ChoiceField(choices=Pagamento.METODO_CHOICES)
    referencia = serializers.CharField(required=False, allow_blank=True)

    
    def validate_valor(self, value):
        documento = self.context.get('documento')
        if documento and value > documento.saldo_pendente:
            raise serializers.ValidationError(
                f"Valor excede o saldo pendente. Saldo: {documento.saldo_pendente}"
            )
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        documento = self.context.get('documento')
        user = self.context.get('request').user
        
        pagamento = Pagamento.objects.create(
            documento=documento,
            valor=validated_data['valor'],
            metodo=validated_data['metodo'],
            referencia=validated_data.get('referencia', ''),
            operador=user
        )
        
        # Atualiza total_pago do documento
        total_pago = documento.pagamentos.aggregate(total=models.Sum('valor'))['total'] or 0
        documento.total_pago = total_pago
        documento.atualizar_estado()
        
        return pagamento


class PagamentoSerializer(serializers.ModelSerializer):
    metodo_display = serializers.ReadOnlyField(source='get_metodo_display')
    operador_nome = serializers.ReadOnlyField(source='operador.get_full_name')
    
    # 🔹 Adiciona dados do documento
    documento_numero = serializers.ReadOnlyField(source='documento.numero')
    documento_cliente_nome = serializers.ReadOnlyField(source='documento.cliente.nome')
    documento_id = serializers.ReadOnlyField(source='documento.id')
    
    # 🔹 Adiciona dados do cliente
    cliente_nif = serializers.ReadOnlyField(source='documento.cliente.nif')
    filial_nome = serializers.ReadOnlyField(source='documento.filial.nome')
    cliente_id = serializers.ReadOnlyField(source='documento.cliente.id')
    filial_id = serializers.ReadOnlyField(source='documento.filial.id')
    
    class Meta:
        model = Pagamento
        fields = [
            'id', 'documento', 'documento_id', 'documento_numero', 'documento_cliente_nome',
            'valor', 'metodo', 'metodo_display', 'referencia',
            'data_pagamento', 'operador', 'operador_nome', "filial_nome", "cliente_nif", "cliente_id", "filial_id"
        ]