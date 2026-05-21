# apps/faturacao/utils.py
from django.db import transaction
from .models import SerieDocumento
from django.utils import timezone


class NumeroDocumentoGenerator:
    """Gerador de números sequenciais para documentos fiscais"""
    
    @staticmethod
    @transaction.atomic
    def gerar_numero(filial_id, tipo_documento):
        """
        Gera o próximo número para um tipo de documento específico
        Retorna: Número formatado (ex: FAT-2026-00001)
        """
        
        # Busca ou cria a série para a filial e tipo
        serie, created = SerieDocumento.objects.select_for_update().get_or_create(
            filial_id=filial_id,
            tipo=tipo_documento,
            defaults={
                'prefixo': SerieDocumento._meta.get_field('prefixo').default,
                'numero_atual': 0,
                'ativo': True
            }
        )
        
        if not serie.ativo:
            raise ValueError(f"Série para {tipo_documento} está inativa")
        
        # Incrementa o número
        serie.numero_atual += 1
        serie.save()
        
        # Formata o número (ex: FAT-2026-00001)
        ano = timezone.now().year
        numero_formatado = f"{serie.prefixo}-{ano}-{serie.numero_atual:05d}"
        
        return numero_formatado