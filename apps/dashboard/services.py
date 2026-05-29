# apps/dashboard/services.py (atualizado)
from django.db.models import Sum, Count, F, ExpressionWrapper,DecimalField
from django.db.models.functions import TruncMonth , TruncDay, TruncWeek
from datetime import datetime, timedelta
from calendar import month_name
from apps.faturacao.models import Documento, LinhaDocumento, MovimentacaoStock,Produto,Stock
from apps.organizacao.models import Funcionario, Filial
from apps.clientes.models import Cliente


class DashboardService:
    
    @staticmethod
    def get_kpis(filial_id=None):
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
            'total_clientes': total_clientes,
            'total_produtos': total_produtos,
            'total_funcionarios': total_funcionarios,
            'total_filiais': total_filiais,
            'produtos_stock_baixo': produtos_stock_baixo,
            'produtos_esgotados': produtos_esgotados,
        }
    
    @staticmethod
    def get_vendas_ultimos_12_meses(filial_id=None):
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
            total=Sum('total')
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
                'quantidade': 0,
            })
        
        return resultado
    
    @staticmethod
    def get_top_produtos(limit=5, filial_id=None):
        """Retorna os produtos mais vendidos via linhas_documento"""
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
    
    @staticmethod
    def get_alertas_stock(filial_id=None):
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
        
        return alertas[:10]
    
    @staticmethod
    def get_ultimas_movimentacoes(limit=10, filial_id=None):
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
    
    @staticmethod
    def get_resumo_filiais():
        """Retorna resumo de cada filial"""
        filiais = Filial.objects.filter(ativo=True)
        
        resumo = []
        for filial_obj in filiais:
            resumo.append({
                'id': str(filial_obj.id),
                'nome': filial_obj.nome,
                'total_faturado': float(
                    Documento.objects.filter(
                        filial=filial_obj,
                        tipo='FACTURA',
                        estado='PAGA'
                    ).aggregate(total=Sum('total'))['total'] or 0
                ),
                'total_clientes': Cliente.objects.filter(
                    documentos__filial=filial_obj
                ).distinct().count(),
                'total_funcionarios': filial_obj.funcionarios.filter(ativo=True).count(),
                'total_produtos_stock': filial_obj.stocks.count(),
            })
        
        return resumo
    

    # apps/dashboard/services.py
    @staticmethod
    def get_vendas_por_periodo(data_inicio, data_fim, filial_id=None, agrupamento='mes'):
        queryset = Documento.objects.filter(
            tipo='FACTURA',
            estado='PAGA',
            data_emissao__date__gte=data_inicio,
            data_emissao__date__lte=data_fim
        )
        if filial_id:
            queryset = queryset.filter(filial_id=filial_id)

        if agrupamento == 'dia':
            trunc = TruncDay('data_emissao')
            formatacao = '%Y-%m-%d'
        elif agrupamento == 'semana':
            trunc = TruncWeek('data_emissao')
            formatacao = '%Y-%m-%d'  # semana início
        else:  # mês
            trunc = TruncMonth('data_emissao')
            formatacao = '%Y-%m'

        vendas = queryset.annotate(periodo=trunc).values('periodo').annotate(
            total=Sum('total'),
            quantidade=Count('id')
        ).order_by('periodo')

        return [
            {
                'periodo': p['periodo'].strftime(formatacao) if p['periodo'] else '',
                'total': float(p['total']) if p['total'] else 0,
                'quantidade': p['quantidade'],
            }
            for p in vendas
        ]




# apps/dashboard/services.py (adicione no final da classe)

    @staticmethod
    def get_relatorio_clientes(data_inicio, data_fim, filial_id=None, limit=50):
        """Retorna lista de clientes com total comprado no período"""
        from apps.clientes.models import Cliente
        from django.db.models import Sum

        # Base de clientes que fizeram compras no período
        qs_clientes = Cliente.objects.filter(
            documentos__tipo='FACTURA',
            documentos__estado='PAGA',
            documentos__data_emissao__date__gte=data_inicio,
            documentos__data_emissao__date__lte=data_fim
        ).distinct()

        if filial_id:
            qs_clientes = qs_clientes.filter(
                documentos__filial_id=filial_id
            ).distinct()

        resultado = []
        for cliente in qs_clientes:
            docs = cliente.documentos.filter(
                tipo='FACTURA',
                estado='PAGA',
                data_emissao__date__gte=data_inicio,
                data_emissao__date__lte=data_fim
            )
            if filial_id:
                docs = docs.filter(filial_id=filial_id)
            total = docs.aggregate(total=Sum('total'))['total'] or 0
            quantidade = docs.count()
            resultado.append({
                'id': str(cliente.id),
                'nome': cliente.nome,
                'nif': cliente.nif or '',
                'email': cliente.email or '',
                'telefone': cliente.telefone or '',
                'total_compras': float(total),
                'quantidade_documentos': quantidade,
            })

        resultado.sort(key=lambda x: x['total_compras'], reverse=True)
        return resultado[:limit]

# apps/dashboard/services.py (substitua o método existente)

    @staticmethod
    def get_relatorio_produtos(data_inicio, data_fim, filial_id=None, categoria_id=None, limit=100):
        from collections import defaultdict

        linhas = LinhaDocumento.objects.filter(
            documento__tipo='FACTURA',
            documento__estado='PAGA',
            documento__data_emissao__date__gte=data_inicio,
            documento__data_emissao__date__lte=data_fim
        ).select_related('produto')  # otimização

        if filial_id:
            linhas = linhas.filter(documento__filial_id=filial_id)
        if categoria_id:
            linhas = linhas.filter(produto__categoria_id=categoria_id)

        produtos_dict = defaultdict(lambda: {
            'quantidade': 0,
            'total_vendido': 0,
            'valor_iva': 0,
            'nome': '',
            'codigo': ''
        })

        for linha in linhas:
            pid = linha.produto_id
            produtos_dict[pid]['quantidade'] += linha.quantidade
            produtos_dict[pid]['total_vendido'] += float(linha.quantidade) * float(linha.preco_unitario)
            produtos_dict[pid]['valor_iva'] += float(linha.valor_iva)
            if not produtos_dict[pid]['nome']:
                produtos_dict[pid]['nome'] = linha.produto.nome
                produtos_dict[pid]['codigo'] = linha.produto.codigo_barras or ''

        # Ordenar por total_vendido decrescente e limitar
        produtos_ordenados = sorted(
            produtos_dict.items(),
            key=lambda x: x[1]['total_vendido'],
            reverse=True
        )[:limit]

        return [
            {
                'id': str(pid),
                'nome': dados['nome'],
                'codigo': dados['codigo'],
                'quantidade': int(dados['quantidade']),
                'total_vendido': float(dados['total_vendido']),
                'valor_iva': float(dados['valor_iva']),
            }
            for pid, dados in produtos_ordenados
        ]

