from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class PadraoPaginacao(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size' # Permite ao front fazer ?page_size=50
    max_page_size = 100

    def get_paginated_response(self, data):
        """Customizamos a resposta para ser mais clara para o Frontend"""
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'total_itens': self.page.paginator.count,
            'total_paginas': self.page.paginator.num_pages,
            'pagina_atual': self.page.number,
            'results': data
        })