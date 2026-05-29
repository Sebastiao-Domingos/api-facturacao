# apps/dashboard/viewsets.py
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from calendar import month_name
from apps.faturacao.models import Documento, LinhaDocumento, MovimentacaoStock, Produto, Stock
from apps.organizacao.models import Funcionario, Filial
from apps.clientes.models import Cliente
from .serializers import DashboardSerializer
from .services import DashboardService


class DashboardViewSet(viewsets.GenericViewSet):
    
    permission_classes = [IsAuthenticated]
    filter_backends = [] 
    
    def get_queryset(self):
        return None
    
    def get_filial_id(self):
        """Retorna o ID da filial baseado no usuário e parâmetros"""
        user = self.request.user
        filial_id = self.request.query_params.get('filial')
        
        # Se o usuário não é superadmin, força a sua filial
        if not user.is_superuser and hasattr(user, 'funcionario'):
            return str(user.funcionario.filial.id)
        
        return filial_id
    
    def list(self, request):
        """Retorna todos os dados do dashboard"""
        filial_id = self.get_filial_id()
        
        data = {
            'kpis': self.get_kpis(filial_id),
            'vendas_ultimos_12_meses': self.get_vendas_ultimos_12_meses(filial_id),
            'top_produtos': self.get_top_produtos(filial_id=filial_id),
            'alertas_stock': self.get_alertas_stock(filial_id),
            'ultimas_movimentacoes': self.get_ultimas_movimentacoes(filial_id=filial_id),
            'resumo_filiais': self.get_resumo_filiais() if not filial_id else [],
        }
        
        serializer = DashboardSerializer(data)
        return Response(serializer.data)
    
    # ========== MÉTODOS AUXILIARES ==========
    
    def get_kpis(self, filial_id=None):
        """Retorna os KPIs principais"""
        # Base queryset para documentos (facturas pagas)
        docs_queryset = Documento.objects.filter(
            tipo='FACTURA',
            estado='PAGA'
        )
        if filial_id:
            docs_queryset = docs_queryset.filter(filial_id=filial_id)
        
        # Faturação do mês
        hoje = datetime.now().date()
        primeiro_dia_mes = hoje.replace(day=1)
        faturacao_mes = docs_queryset.filter(
            data_emissao__date__gte=primeiro_dia_mes
        ).aggregate(total=Sum('total'))['total'] or 0
        
        # Faturação do ano
        primeiro_dia_ano = hoje.replace(month=1, day=1)
        faturacao_ano = docs_queryset.filter(
            data_emissao__date__gte=primeiro_dia_ano
        ).aggregate(total=Sum('total'))['total'] or 0
        
        # Faturação do mês anterior (para calcular variação)
        primeiro_dia_mes_anterior = (primeiro_dia_mes - timedelta(days=1)).replace(day=1)
        ultimo_dia_mes_anterior = primeiro_dia_mes - timedelta(days=1)
        faturacao_mes_anterior = docs_queryset.filter(
            data_emissao__date__gte=primeiro_dia_mes_anterior,
            data_emissao__date__lte=ultimo_dia_mes_anterior
        ).aggregate(total=Sum('total'))['total'] or 0
        
        # Variação percentual
        variacao = 0
        if faturacao_mes_anterior > 0:
            variacao = ((faturacao_mes - faturacao_mes_anterior) / faturacao_mes_anterior) * 100
        
        # Total de clientes
        clientes_queryset = Cliente.objects.filter(ativo=True)
        if filial_id:
            clientes_queryset = clientes_queryset.filter(
                documentos__filial_id=filial_id
            ).distinct()
        total_clientes = clientes_queryset.count()
        
        # Total de produtos
        total_produtos = Produto.objects.filter(ativo=True).count()
        
        # Total de funcionários
        funcionarios_queryset = Funcionario.objects.filter(ativo=True)
        if filial_id:
            funcionarios_queryset = funcionarios_queryset.filter(filial_id=filial_id)
        total_funcionarios = funcionarios_queryset.count()
        
        # Total de filiais
        filiais_queryset = Filial.objects.filter(ativo=True)
        if filial_id:
            filiais_queryset = filiais_queryset.filter(id=filial_id)
        total_filiais = filiais_queryset.count()
        
        # Produtos com stock baixo
        stocks_queryset = Stock.objects.select_related('produto', 'filial')
        if filial_id:
            stocks_queryset = stocks_queryset.filter(filial_id=filial_id)
        
        produtos_stock_baixo = stocks_queryset.filter(
            quantidade__lte=F('stock_minimo'),
            quantidade__gt=0
        ).count()
        
        # Produtos esgotados
        produtos_esgotados = stocks_queryset.filter(quantidade=0).count()
        
        return {
            'faturacao_mes': float(faturacao_mes),
            'faturacao_ano': float(faturacao_ano),
            'variacao_mensal': round(variacao, 2),
            'total_clientes': total_clientes,
            'total_produtos': total_produtos,
            'total_funcionarios': total_funcionarios,
            'total_filiais': total_filiais,
            'produtos_stock_baixo': produtos_stock_baixo,
            'produtos_esgotados': produtos_esgotados,
        }
    
    def get_vendas_ultimos_12_meses(self, filial_id=None):
        """Retorna vendas dos últimos 12 meses"""
        hoje = datetime.now().date()
        data_limite = hoje - timedelta(days=365)
        
        docs_queryset = Documento.objects.filter(
            tipo='FACTURA',
            estado='PAGA',
            data_emissao__date__gte=data_limite
        )
        if filial_id:
            docs_queryset = docs_queryset.filter(filial_id=filial_id)
        
        # Agrupar por mês
        vendas_por_mes = docs_queryset.annotate(
            mes=TruncMonth('data_emissao')
        ).values('mes').annotate(
            total=Sum('total'),
            quantidade=Count('id')
        ).order_by('mes')
        
        # Criar dicionário com todos os meses
        resultado = []
        for i in range(11, -1, -1):
            data_mes = hoje.replace(day=1) - timedelta(days=30*i)
            mes_nome = month_name[data_mes.month][:3]
            
            venda_mes = next(
                (v for v in vendas_por_mes if v['mes'] and v['mes'].month == data_mes.month and v['mes'].year == data_mes.year),
                None
            )
            
            resultado.append({
                'periodo': f"{mes_nome}/{str(data_mes.year)[-2:]}",
                'total': float(venda_mes['total']) if venda_mes else 0,
                'quantidade': venda_mes['quantidade'] if venda_mes else 0,
            })
        
        return resultado
    
    def get_top_produtos(self, limit=5, filial_id=None):
        """Retorna os produtos mais vendidos"""
        linhas_queryset = LinhaDocumento.objects.filter(
            documento__tipo='FACTURA',
            documento__estado='PAGA'
        )
        if filial_id:
            linhas_queryset = linhas_queryset.filter(documento__filial_id=filial_id)
        
        top_produtos = linhas_queryset.values(
            'produto_id',
            'produto__nome',
            'produto__codigo_barras',
        ).annotate(
            total_vendido=Sum(F('quantidade') * F('preco_unitario')),
            quantidade=Sum('quantidade')
        ).order_by('-total_vendido')[:limit]
        
        return [
            {
                'id': str(p['produto_id']),
                'nome': p['produto__nome'],
                'codigo': p['produto__codigo_barras'] or '',
                'total_vendido': float(p['total_vendido'] or 0),
                'quantidade': int(p['quantidade'] or 0),
                'imagem': None,
            }
            for p in top_produtos
        ]
    
    def get_alertas_stock(self, filial_id=None):
        """Retorna alertas de stock baixo e esgotado"""
        stocks_queryset = Stock.objects.select_related('produto', 'filial')
        if filial_id:
            stocks_queryset = stocks_queryset.filter(filial_id=filial_id)
        
        alertas = []
        
        # Stock mínimo
        stock_minimo = stocks_queryset.filter(
            quantidade__lte=F('stock_minimo'),
            quantidade__gt=0
        )
        for stock in stock_minimo:
            alertas.append({
                'id': str(stock.id),
                'produto_nome': stock.produto.nome,
                'produto_codigo': stock.produto.codigo_barras or '',
                'filial_nome': stock.filial.nome,
                'quantidade_atual': float(stock.quantidade),
                'stock_minimo': float(stock.stock_minimo),
                'status': 'STOCK_MINIMO',
            })
        
        # Esgotados
        esgotados = stocks_queryset.filter(quantidade=0)
        for stock in esgotados:
            alertas.append({
                'id': str(stock.id),
                'produto_nome': stock.produto.nome,
                'produto_codigo': stock.produto.codigo_barras or '',
                'filial_nome': stock.filial.nome,
                'quantidade_atual': 0,
                'stock_minimo': float(stock.stock_minimo),
                'status': 'ESGOTADO',
            })
        
        # Ordenar: primeiro esgotados, depois stock mínimo
        alertas.sort(key=lambda x: (x['status'] != 'ESGOTADO', x['status']))
        
        return alertas[:10]
    
    def get_ultimas_movimentacoes(self, limit=10, filial_id=None):
        """Retorna as últimas movimentações de stock"""
        mov_queryset = MovimentacaoStock.objects.select_related(
            'stock_filial__produto',
            'stock_filial__filial',
            'operador'
        ).order_by('-created_at')
        
        if filial_id:
            mov_queryset = mov_queryset.filter(stock_filial__filial_id=filial_id)
        
        movimentacoes_list = mov_queryset[:limit]
        
        return [
            {
                'id': str(m.id),
                'produto_nome': m.stock_filial.produto.nome,
                'filial_nome': m.stock_filial.filial.nome,
                'tipo': m.tipo,
                'tipo_display': 'Entrada' if m.tipo == 'E' else 'Saída',
                'quantidade': float(m.quantidade),
                'data': m.created_at.isoformat(),
                'operador': m.operador.get_full_name() if m.operador else None,
            }
            for m in movimentacoes_list
        ]
    
    def get_resumo_filiais(self):
        """Retorna resumo de cada filial"""
        filiais = Filial.objects.filter(ativo=True)
        
        resumo = []
        for filial_obj in filiais:
            # Total faturado
            total_faturado = Documento.objects.filter(
                filial=filial_obj,
                tipo='FACTURA',
                estado='PAGA'
            ).aggregate(total=Sum('total'))['total'] or 0
            
            # Total de clientes que compraram nesta filial
            total_clientes = Cliente.objects.filter(
                documentos__filial=filial_obj
            ).distinct().count()
            
            resumo.append({
                'id': str(filial_obj.id),
                'nome': filial_obj.nome,
                'total_faturado': float(total_faturado),
                'total_clientes': total_clientes,
                'total_funcionarios': filial_obj.funcionarios.filter(ativo=True).count(),
                'total_produtos_stock': filial_obj.stocks.count(),
            })
        
        # Ordenar por total faturado (decrescente)
        resumo.sort(key=lambda x: x['total_faturado'], reverse=True)
        
        return resumo
    
    # ========== ENDPOINTS ESPECÍFICOS ==========
    
    @action(detail=False, methods=['get'], url_path='kpis')
    def kpis(self, request):
        """Retorna apenas os KPIs"""
        filial_id = self.get_filial_id()
        data = self.get_kpis(filial_id)
        return Response(data)
    
    @action(detail=False, methods=['get'], url_path='vendas')
    def vendas(self, request):
        """Retorna vendas por período"""
        filial_id = self.get_filial_id()
        data = DashboardService.get_vendas_ultimos_12_meses(filial_id)
        return Response(data)
    
    @action(detail=False, methods=['get'], url_path='top-produtos')
    def top_produtos(self, request):
        """Retorna os produtos mais vendidos"""
        filial_id = self.get_filial_id()
        limit = int(request.query_params.get('limit', 5))
        data = DashboardService.get_top_produtos(limit, filial_id)
        return Response(data)
    
    @action(detail=False, methods=['get'], url_path='alertas')
    def alertas(self, request):
        """Retorna alertas de stock"""
        filial_id = self.get_filial_id()
        data = DashboardService.get_alertas_stock(filial_id)
        return Response(data)
    
    @action(detail=False, methods=['get'], url_path='movimentacoes')
    def movimentacoes(self, request):
        """Retorna as últimas movimentações de stock"""
        filial_id = self.get_filial_id()
        limit = int(request.query_params.get('limit', 10))
        data = DashboardService.get_ultimas_movimentacoes(limit, filial_id)
        return Response(data)
    
    @action(detail=False, methods=['get'], url_path='resumo-filiais')
    def resumo_filiais(self, request):
        """Retorna resumo por filial"""
        # Apenas SUPERADMIN ou ADMIN podem ver este endpoint
        user = request.user
        if not user.is_superuser and not (hasattr(user, 'funcionario') and user.funcionario.papel in ['SUPERADMIN', 'ADMIN']):
            return Response(
                {"error": "Permissão negada. Apenas administradores podem ver o resumo de todas as filiais."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = DashboardService.get_resumo_filiais()
        return Response(data)
    


    @action(detail=False, methods=['get'], url_path='vendas-periodo')
    def vendas_periodo(self, request):
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        if not data_inicio or not data_fim:
            return Response({"error": "data_inicio e data_fim são obrigatórios"}, status=400)
        filial_id = self.get_filial_id()
        agrupamento = request.query_params.get('agrupamento', 'mes')
        data = DashboardService.get_vendas_por_periodo(data_inicio, data_fim, filial_id, agrupamento)
        return Response(data)

    # apps/dashboard/viewsets.py (adicione dentro da classe DashboardViewSet)

    @action(detail=False, methods=['get'], url_path='relatorio-clientes')
    def relatorio_clientes(self, request):
        """Relatório de clientes por período"""
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        if not data_inicio or not data_fim:
            return Response(
                {"error": "Parâmetros 'data_inicio' e 'data_fim' são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST
            )
        filial_id = self.get_filial_id()
        limit = int(request.query_params.get('limit', 50))
        data = DashboardService.get_relatorio_clientes(data_inicio, data_fim, filial_id, limit)
        return Response(data)


    @action(detail=False, methods=['get'], url_path='relatorio-produtos')
    def relatorio_produtos(self, request):
        """Relatório de produtos vendidos por período"""
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        if not data_inicio or not data_fim:
            return Response(
                {"error": "Parâmetros 'data_inicio' e 'data_fim' são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST
            )
        filial_id = self.get_filial_id()
        categoria_id = request.query_params.get('categoria')
        limit = int(request.query_params.get('limit', 100))
        data = DashboardService.get_relatorio_produtos(
            data_inicio, data_fim, filial_id, categoria_id, limit
        )
        return Response(data)


