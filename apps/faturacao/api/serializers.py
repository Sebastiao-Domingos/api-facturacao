from rest_framework import serializers
from ..models import Categoria, UnidadeMedida, TaxaIva, Produto, Stock

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class UnidadeMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeMedida
        fields = '__all__'

class TaxaIvaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxaIva
        fields = '__all__'

class ProdutoSerializer(serializers.ModelSerializer):
    # Campos detalhados para leitura (Frontend ver nomes em vez de IDs)
    categoria_nome = serializers.ReadOnlyField(source='categoria.nome')
    unidade_sigla = serializers.ReadOnlyField(source='unidade_medida.sigla')
    taxa_valor = serializers.ReadOnlyField(source='taxa_iva.valor')

    class Meta:
        model = Produto
        fields = "__all__"

class StockSerializer(serializers.ModelSerializer):
    produto_nome = serializers.ReadOnlyField(source='produto.nome')

    class Meta:
        model = Stock
        fields = "__all__"