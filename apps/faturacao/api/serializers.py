from rest_framework import serializers
from ..models import Categoria, UnidadeMedida, TaxaIva, Produto, Stock

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
            'id', 'nome', 'tipo', 'categoria', 'categoria_detalhes',
            'unidade_medida', 'unidade_detalhes', 'taxa_iva', 'taxa_detalhes',
            'preco_venda', 'codigo_barras', 'ref_interna', 'ativo'
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