# apps/faturacao/utils.py
from django.db import transaction
from .models import SerieDocumento
from django.utils import timezone


class NumeroDocumentoGenerator:
    @staticmethod
    @transaction.atomic
    def gerar_numero(filial_id, tipo_documento):
        from .models import SerieDocumento, Documento

        # Mapeamento de prefixos por tipo
        prefixos = {
            'FACTURA': 'FAT',
            'PRO_FORMA': 'PRO',
            'RECIBO': 'REC',
            'NOTA_CREDITO': 'NC',
            'NOTA_DEBITO': 'ND',
        }
        prefixo = prefixos.get(tipo_documento, 'DOC')

        # Obtém a série com lock
        serie, created = SerieDocumento.objects.select_for_update().get_or_create(
            filial_id=filial_id,
            tipo=tipo_documento,
            defaults={
                'prefixo': prefixo,
                'numero_atual': 0,
                'ativo': True
            }
        )

        if not serie.ativo:
            raise ValueError(f"Série para {tipo_documento} está inativa")

        # Incrementa o número
        serie.numero_atual += 1
        serie.save()

        ano = timezone.now().year
        numero_formatado = f"{serie.prefixo}-{ano}-{serie.numero_atual:05d}"

        # Segurança extra: garante que o número é único (caso raro de duplicação manual)
        while Documento.objects.filter(numero=numero_formatado).exists():
            serie.numero_atual += 1
            serie.save()
            numero_formatado = f"{serie.prefixo}-{ano}-{serie.numero_atual:05d}"

        return numero_formatado
