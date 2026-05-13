from django.contrib import admin
from .models import Categoria, UnidadeMedida, TaxaIva, Produto, Stock

admin.site.register(Categoria)
admin.site.register(UnidadeMedida)
admin.site.register(TaxaIva)
admin.site.register(Produto)
admin.site.register(Stock)