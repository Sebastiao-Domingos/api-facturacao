from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from .pagination import PadraoPaginacao
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets, status, serializers as drf_serializers
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from weasyprint import HTML
from django.template.loader import render_to_string
from ..models import Documento, Pagamento

from .serializers import (
    DocumentoListSerializer, DocumentoDetailSerializer,
    DocumentoCreateSerializer, PagamentoCreateSerializer, PagamentoSerializer
)
from ..services import DocumentoService , CompraService
from .pagination import PadraoPaginacao


from ..models import Produto, Categoria, Stock, TaxaIva, UnidadeMedida,MovimentacaoStock, Compra, Fornecedor
from .serializers import (
    ProdutoSerializer, CategoriaSerializer, StockSerializer, FornecedorSerializer,CompraSerializer,CompraCreateSerializer,
    TaxaIvaSerializer, UnidadeMedidaSerializer, MovimentacaoStockSerializer,ExecutarMovimentacaoSerializer
)


class BaseViewSet(viewsets.ModelViewSet):
    """Classe base para evitar repetição de permissões"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

class ProdutoViewSet(BaseViewSet):
    queryset = Produto.objects.select_related('categoria', 'taxa_iva', 'unidade_medida').all()
    serializer_class = ProdutoSerializer
    search_fields = ['nome', 'codigo_barras', 'ref_interna']
    filterset_fields = ['categoria', 'tipo', 'ativo']
    ordering_fields = ['nome']
    pagination_class = PadraoPaginacao


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Stock.objects.select_related('produto', 'filial').all()
    serializer_class = StockSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'filial': ['exact'],
        'produto': ['exact'],
        'produto__nome': ['icontains'],
        'produto__codigo_barras': ['icontains'],
        'produto__categoria': ['exact'],
        'produto__tipo': ['exact'],
        'produto__ativo': ['exact'],
        'quantidade': ['gte', 'lte'],
        'stock_minimo': ['gte', 'lte'],
    }
    ordering_fields = ['quantidade', 'produto__nome']
    pagination_class = PadraoPaginacao


    @action(detail=True, methods=['post'], url_path='movimentar')
    def movimentar_stock(self, request, pk=None):
        stock_filial = self.get_object()
        
        # 1. Passamos os dados recebidos para o Serializer de Execução/Validação
        serializer = ExecutarMovimentacaoSerializer(
            data=request.data, 
            context={'stock_filial': stock_filial}
        )
        
        if serializer.is_valid():
            # 2. O método .save() agora retorna a instância da MovimentacaoStock criada
            movimentacao = serializer.save(
                stock_filial=stock_filial,
                operador=request.user
            )
            
            # 3. Passamos essa instância pelo Serializer de Leitura para devolver o JSON perfeito
            response_serializer = MovimentacaoStockSerializer(movimentacao)
            
            # 4. Retornamos os dados serializados da movimentação com tipo, quantidade e operador
            return Response(
                response_serializer.data, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class CategoriaViewSet(BaseViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    search_fields = ['nome']
    ordering_fields = ['nome']
    pagination_class = PadraoPaginacao

class TaxaIvaViewSet(BaseViewSet):
    queryset = TaxaIva.objects.all()
    serializer_class = TaxaIvaSerializer
    search_fields = ['codigo']
    ordering_fields = ['codigo']
    pagination_class = None

class UnidadeMedidaViewSet(BaseViewSet):
    queryset = UnidadeMedida.objects.all()
    serializer_class = UnidadeMedidaSerializer
    search_fields = ['sigla', 'nome']
    ordering_fields = ['sigla', 'nome']
    pagination_class = None




class MovimentacaoStockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint apenas de leitura para o histórico de auditoria.
    As movimentações devem ser geradas por Triggers ou Services no Back-end.
    """
    queryset = MovimentacaoStock.objects.all()
    serializer_class = MovimentacaoStockSerializer
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['stock_filial'] # Crucial para o Next.js filtrar: /api/movimentacoes/?stock_filial=id_aqui
    ordering_fields = ['created_at']
    pagination_class = PadraoPaginacao




class DocumentoViewSet(viewsets.ModelViewSet):
    """ViewSet para Documentos Fiscais"""
    
    permission_classes = [IsAuthenticated]
    pagination_class = PadraoPaginacao
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tipo', 'estado', 'cliente', 'filial']
    
    def get_queryset(self):
        user = self.request.user
        
        # SUPERADMIN vê tudo
        if user.is_superuser:
            return Documento.objects.select_related('cliente', 'filial').all()
        
        # Funcionário vê apenas documentos da sua filial
        if hasattr(user, 'funcionario'):
            return Documento.objects.select_related('cliente', 'filial').filter(
                filial=user.funcionario.filial
            )
        
        return Documento.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentoListSerializer
        if self.action == 'retrieve':
            return DocumentoDetailSerializer
        if self.action == 'create':
            return DocumentoCreateSerializer
        if self.action == 'registrar_pagamento':
            return PagamentoCreateSerializer
        return DocumentoDetailSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        documento = serializer.save()
        
        # Retorna o documento criado
        output_serializer = DocumentoDetailSerializer(documento)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='emitir')
    def emitir(self, request, pk=None):
        """Emite um documento (atribui número e atualiza stock)"""
        try:
            documento = DocumentoService.emitir_documento(pk , request.user)
            serializer = DocumentoDetailSerializer(documento)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], url_path='anular')
    def anular(self, request, pk=None):
        """Anula um documento (restaura stock)"""
        try:
            documento = DocumentoService.anular_documento(pk)
            serializer = DocumentoDetailSerializer(documento)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], url_path='pagamentos')
    def registrar_pagamento(self, request, pk=None):
        """Registra um pagamento para o documento"""
        documento = self.get_object()
        
        serializer = PagamentoCreateSerializer(
            data=request.data,
            context={'documento': documento, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        pagamento = serializer.save()
        
        output_serializer = PagamentoSerializer(pagamento)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'], url_path='pdf')
    def download_pdf(self, request, pk=None):
        """Gera e baixa o PDF do documento"""
        documento = self.get_object()
        
        # Prepara o contexto para o template
        context = {
            'documento': documento,
            'linhas': documento.linhas.all(),
            'cliente': documento.cliente,
            'filial': documento.filial,
            'empresa': documento.filial.empresa,
            'data_emissao': documento.data_emissao,
        }
        
        # Renderiza o HTML
        html_string = render_to_string('faturacao/documento_pdf.html', context)
        
        # Gera o PDF
        pdf_file = HTML(string=html_string).write_pdf()
        
        # Retorna o PDF
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{documento.numero}.pdf"'
        return response


class PagamentoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para Pagamentos (apenas leitura)"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = PagamentoSerializer
    pagination_class = PadraoPaginacao

    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            return Pagamento.objects.select_related('documento', 'operador').all()
        
        if hasattr(user, 'funcionario'):
            return Pagamento.objects.select_related('documento', 'operador').filter(
                documento__filial=user.funcionario.filial
            )
        
        return Pagamento.objects.none()





# apps/faturacao/viewsets.py

class FornecedorViewSet(viewsets.ModelViewSet):
    queryset = Fornecedor.objects.all()
    serializer_class = FornecedorSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['ativo']
    search_fields = ['nome', 'nif']
    pagination_class = PadraoPaginacao


class CompraViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = PadraoPaginacao
    filterset_fields = ['estado', 'fornecedor', 'filial']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Compra.objects.select_related('fornecedor', 'filial').all()
        if hasattr(user, 'funcionario'):
            return Compra.objects.select_related('fornecedor', 'filial').filter(filial=user.funcionario.filial)
        return Compra.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return CompraCreateSerializer
        if self.action == 'list' or self.action == 'retrieve':
            return CompraSerializer
        return CompraSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        compra = serializer.save()
        output = CompraSerializer(compra)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='confirmar')
    def confirmar(self, request, pk=None):
        try:
            compra = CompraService.confirmar_compra(pk, request.user)
            serializer = CompraSerializer(compra)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
