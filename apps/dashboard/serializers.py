# apps/dashboard/serializers.py
from rest_framework import serializers

class KPISerializer(serializers.Serializer):
    faturacao_mes = serializers.FloatField()
    faturacao_ano = serializers.FloatField()
    variacao_mensal = serializers.FloatField()
    total_clientes = serializers.IntegerField()
    total_produtos = serializers.IntegerField()
    total_funcionarios = serializers.IntegerField()
    total_filiais = serializers.IntegerField()
    produtos_stock_baixo = serializers.IntegerField()
    produtos_esgotados = serializers.IntegerField()


class VendaPeriodoSerializer(serializers.Serializer):
    periodo = serializers.CharField()
    total = serializers.FloatField()
    quantidade = serializers.IntegerField()


class TopProdutoSerializer(serializers.Serializer):
    id = serializers.CharField()
    nome = serializers.CharField()
    codigo = serializers.CharField()
    total_vendido = serializers.FloatField()
    quantidade = serializers.IntegerField()
    imagem = serializers.CharField(allow_null=True)


class AlertaStockSerializer(serializers.Serializer):
    id = serializers.CharField()
    produto_nome = serializers.CharField()
    produto_codigo = serializers.CharField()
    filial_nome = serializers.CharField()
    quantidade_atual = serializers.FloatField()
    stock_minimo = serializers.FloatField()
    status = serializers.ChoiceField(choices=['STOCK_MINIMO', 'ESGOTADO'])


class MovimentacaoRecenteSerializer(serializers.Serializer):
    id = serializers.CharField()
    produto_nome = serializers.CharField()
    filial_nome = serializers.CharField()
    tipo = serializers.CharField()
    tipo_display = serializers.CharField()
    quantidade = serializers.FloatField()
    data = serializers.DateTimeField()
    operador = serializers.CharField(allow_null=True)


class ResumoFilialSerializer(serializers.Serializer):
    id = serializers.CharField()
    nome = serializers.CharField()
    total_faturado = serializers.FloatField()
    total_clientes = serializers.IntegerField()
    total_funcionarios = serializers.IntegerField()
    total_produtos_stock = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    kpis = KPISerializer()
    vendas_ultimos_12_meses = VendaPeriodoSerializer(many=True)
    top_produtos = TopProdutoSerializer(many=True)
    alertas_stock = AlertaStockSerializer(many=True)
    ultimas_movimentacoes = MovimentacaoRecenteSerializer(many=True)
    resumo_filiais = ResumoFilialSerializer(many=True)