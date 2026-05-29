from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Produto, Stock, MovimentacaoStock
from apps.organizacao.models import Filial

@receiver(post_save, sender=Produto)
def criar_stock_nas_filiais(sender, instance, created, **kwargs):
    if created:
        # Se for um Produto (e não um serviço), cria stock zero em todas as filiais
        if instance.tipo == 'P':
            filiais = Filial.objects.all()
            for filial in filiais:
                Stock.objects.get_or_create(produto=instance, filial=filial)



@receiver(post_save, sender=Stock)
def rastrear_ajuste_direto(sender, instance, created, **kwargs):
    pass
    """
    Deteta se a quantidade no model Stock mudou (via painel administrativo ou modal)
    e grava automaticamente o histórico de auditoria. """