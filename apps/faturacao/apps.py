from django.apps import AppConfig

class FaturacaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.faturacao'

    def ready(self):
        # Importa os sinais quando a app estiver pronta
        import apps.faturacao.signals

        