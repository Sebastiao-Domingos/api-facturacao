from rest_framework import serializers
from ..models import Categoria, UnidadeMedida, TaxaIva, Produto, Stock, MovimentacaoStock
from django.db import transaction
from rest_framework.exceptions import ValidationError

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
    codigo_barras = serializers.ReadOnlyField(source='produto.codigo_barras')

    class Meta:
        model = Stock
        fields = [
            'id', 'produto', 'produto_nome', 'codigo_barras', 
            'filial', 'filial_nome', 'quantidade', 'stock_minimo'
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