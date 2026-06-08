from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated 
from core.permissions import IsAdminOrGestor, IsAdminOrSuperAdmin,IsAdminOrGestorOrOperador
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


# apps/faturacao/viewsets.py
class ProdutoViewSet(viewsets.ModelViewSet):
    serializer_class = ProdutoSerializer
    pagination_class = PadraoPaginacao
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome', 'codigo_barras', 'ref_interna']
    filterset_fields = ['categoria', 'tipo', 'ativo']
    ordering_fields = ['nome']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # SUPERADMIN vê todos os produtos (ativos e inativos?)
        if user.is_superuser:
            return Produto.objects.select_related('categoria', 'taxa_iva', 'unidade_medida').all()

        if not hasattr(user, 'funcionario'):
            return Produto.objects.none()

        funcionario = user.funcionario

        # ADMIN vê produtos que tenham stock em alguma filial da sua empresa
        if funcionario.papel == 'ADMIN':
            empresa = funcionario.filial.empresa
            return Produto.objects.filter(
                stocks__filial__empresa=empresa
            ).distinct().select_related('categoria', 'taxa_iva', 'unidade_medida')

        # GESTOR, OPERADOR, CONTABILISTA vêem produtos que têm stock na sua filial
        return Produto.objects.filter(
            stocks__filial=funcionario.filial
        ).distinct().select_related('categoria', 'taxa_iva', 'unidade_medida')
    
    def get_permissions(self):
    # Apenas SUPERADMIN e ADMIN podem criar ou actualizar
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrSuperAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()



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
    permission_classes = [IsAuthenticated]
    

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Stock.objects.select_related('produto', 'filial').all()

        if not hasattr(user, 'funcionario'):
            return Stock.objects.none()

        funcionario = user.funcionario

        # ADMIN vê stocks de todas as filiais da sua empresa
        if funcionario.papel == 'ADMIN':
            empresa = funcionario.filial.empresa
            return Stock.objects.select_related('produto', 'filial').filter(
                filial__empresa=empresa
            )

        # GESTOR, OPERADOR, CONTABILISTA vêem apenas da sua filial
        return Stock.objects.select_related('produto', 'filial').filter(
            filial=funcionario.filial
        )


    @action(detail=True, methods=['post'], url_path='movimentar', permission_classes= [IsAdminOrGestor])
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
        if user.is_superuser:
            return Documento.objects.all()
        if not hasattr(user, 'funcionario'):
            return Documento.objects.none()
        funcionario = user.funcionario
        if funcionario.papel == 'ADMIN':
            return Documento.objects.filter(filial__empresa=funcionario.filial.empresa)
        if funcionario.papel == 'GESTOR':
            return Documento.objects.filter(filial=funcionario.filial)
        # OPERADOR e CONTABILISTA vêem apenas documentos que criaram (ou da sua filial)
        return Documento.objects.filter(filial=funcionario.filial)
    
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
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsAdminOrGestorOrOperador()]
        if self.action == 'anular':
            return [IsAuthenticated(), IsAdminOrGestor()]
    
        if self.action == 'registrar_pagamento':
            return [IsAuthenticated(), IsAdminOrGestorOrOperador()]
        return [IsAuthenticated()]
    
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
    
    @action(detail=True, methods=['post'], url_path='anular' )
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
    
    # @action(detail=True, methods=['get'], url_path='pdf')
    # def download_pdf(self, request, pk=None):
    #     """Gera e baixa o PDF do documento"""
    #     documento = self.get_object()
    #     empresa = documento.filial.empresa

    #     print("="*80)
    #     print(f"📄 Gerando PDF: {documento.numero}")
    #     print(f"🏢 Empresa: {empresa.nome_fantasia}")
    #     print(f"🖼️ Logotipo: {empresa.logotipo}")  # Verifique o nome do campo aqui
    #     print(f"📁 URL do logo: {empresa.logotipo.url if empresa.logotipo else 'Sem logo'}")
    #     print(f"👤 Utilizador: {request.user}")
    #     print("="*80)# Debug: Verificar se o documento é recuperado corretamente
    #     # Prepara o contexto para o template
    #     context = {
    #         'documento': documento,
    #         'linhas': documento.linhas.all(),
    #         'cliente': documento.cliente,
    #         'filial': documento.filial,
    #         'empresa':empresa,
    #         'data_emissao': documento.data_emissao,
    #         'user': request.user,
    #     }
        
    #     # Renderiza o HTML
    #     html_string = render_to_string('faturacao/documento_pdf.html', context)
        
    #     # Gera o PDF
    #     pdf_file = HTML(string=html_string).write_pdf()
        
    #     # Retorna o PDF
    #     response = HttpResponse(pdf_file, content_type='application/pdf')
    #     response['Content-Disposition'] = f'inline; filename="{documento.numero}.pdf"'
    #     return response


@action(detail=True, methods=['get'], url_path='pdf')
def download_pdf(self, request, pk=None):
    """Gera e baixa o PDF do documento"""
    import os
    from django.conf import settings
    from django.http import JsonResponse
    
    documento = self.get_object()
    empresa = documento.filial.empresa
    
    # Tentar importar WeasyPrint
    try:
        from weasyprint import HTML
        WEASYPRINT_AVAILABLE = True
    except (OSError, ImportError):
        WEASYPRINT_AVAILABLE = False
    
    # Se WeasyPrint não estiver disponível (Vercel), retornar erro informativo
    if not WEASYPRINT_AVAILABLE:
        # Alternativa: Retornar o HTML diretamente no browser
        html_string = render_to_string('faturacao/documento_pdf.html', {
            'documento': documento,
            'linhas': documento.linhas.all(),
            'cliente': documento.cliente,
            'filial': documento.filial,
            'empresa': empresa,
            'data_emissao': documento.data_emissao,
            'user': request.user,
            'logo_absoluto': None,
            'slogan': getattr(empresa, 'slogan', ''),
            'media_root': settings.MEDIA_ROOT,
        })
        
        return HttpResponse(
            html_string,
            content_type='text/html; charset=utf-8'
        )
    
    # WeasyPrint disponível — gerar PDF normalmente
    # Construir o caminho absoluto do logotipo
    logo_absoluto = None
    if empresa.logotipo:
        logo_absoluto = os.path.join(settings.MEDIA_ROOT, str(empresa.logotipo))
        if not os.path.exists(logo_absoluto):
            logo_absoluto = None
    
    # Prepara o contexto para o template
    context = {
        'documento': documento,
        'linhas': documento.linhas.all(),
        'cliente': documento.cliente,
        'filial': documento.filial,
        'empresa': empresa,
        'data_emissao': documento.data_emissao,
        'user': request.user,
        'logo_absoluto': logo_absoluto,
        'slogan': getattr(empresa, 'slogan', ''),
        'media_root': settings.MEDIA_ROOT,
    }
    
    # Renderiza o HTML
    html_string = render_to_string('faturacao/documento_pdf.html', context)
    
    # Gera o PDF
    try:
        pdf_file = HTML(string=html_string).write_pdf()
    except Exception as e:
        # Se falhar a geração do PDF, retornar o HTML
        return HttpResponse(
            f"<h3>Erro ao gerar PDF: {str(e)}</h3><hr>{html_string}",
            content_type='text/html; charset=utf-8'
        )
    
    # Retorna o PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{documento.numero}.pdf"'
    return response


    # @action(detail=True, methods=['get'], url_path='pdf')
    # def download_pdf(self, request, pk=None):
    #     """Gera e baixa o PDF do documento"""
    #     import os
    #     from django.conf import settings
        
    #     documento = self.get_object()
    #     empresa = documento.filial.empresa
        
    #     # Construir o caminho absoluto do logotipo
    #     logo_absoluto = None
    #     if empresa.logotipo:
    #         logo_absoluto = os.path.join(settings.MEDIA_ROOT, str(empresa.logotipo))
        
        
    #     # Prepara o contexto para o template
    #     context = {
    #         'documento': documento,
    #         'linhas': documento.linhas.all(),
    #         'cliente': documento.cliente,
    #         'filial': documento.filial,
    #         'empresa': empresa,
    #         'data_emissao': documento.data_emissao,
    #         'user': request.user,
    #         'logo_absoluto': logo_absoluto,  # ← CAMINHO ABSOLUTO para WeasyPrint
    #         "slogan": empresa.slogan,
    #         'media_root': settings.MEDIA_ROOT,  # ← Raiz do media
    #     }
        
    #     # Renderiza o HTML
    #     html_string = render_to_string('faturacao/documento_pdf.html', context)
        
    #     # Gera o PDF
    #     pdf_file = HTML(string=html_string).write_pdf()
        
    #     # Retorna o PDF
    #     response = HttpResponse(pdf_file, content_type='application/pdf')
    #     response['Content-Disposition'] = f'inline; filename="{documento.numero}.pdf"'
    #     return response


class PagamentoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para Pagamentos (apenas leitura)"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = PagamentoSerializer
    pagination_class = PadraoPaginacao

    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Pagamento.objects.all()
        if not hasattr(user, 'funcionario'):
            return Pagamento.objects.none()
        funcionario = user.funcionario
        if funcionario.papel == 'ADMIN':
            # Pagamentos de documentos de qualquer filial da sua empresa
            empresa = funcionario.filial.empresa
            return Pagamento.objects.filter(documento__filial__empresa=empresa)
        # GESTOR, OPERADOR, CONTABILISTA: apenas pagamentos da sua filial
        return Pagamento.objects.filter(documento__filial=funcionario.filial)





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
