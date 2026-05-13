# apps/organizacao/management/commands/popular_angola.py
from django.core.management.base import BaseCommand
from apps.organizacao.models import Provincia, Municipio

class Command(BaseCommand):
    help = 'Popula a base de dados com Províncias e Municípios de Angola'

    def handle(self, *args, **options):
        # Dicionário de exemplo (podes expandir com todos os municípios)
        dados_angola = {
            "Luanda": ["Belas", "Cacuaco", "Cazenga", "Icolo e Bengo", "Luanda", "Quiçama", "Kilamba Kiaxi", "Talatona", "Viana"],
            "Benguela": ["Baía Farta", "Benguela", "Catumbela", "Chongoroi", "Ganda", "Lobito", "Vila Nova"],
            "Huíla": ["Lubango", "Chibia", "Humpata", "Quilengues", "Cacula"],
            "Huambo": ["Huambo", "Caála", "Ekunha", "Longonjo", "Ukuma"],
            "Cabinda": ["Cabinda", "Cacongo", "Buco-Zau", "Belize"],
            "Zaire": ["Zaire", "Lubango", "Chibia", "Humpata", "Quilengues", "Cacula"],
            "Uíge": ["Uíge", "Alto Cauale", "Ambuíla", "Bembe", "Buengas", "Damba", "Puri" , "Negage"],
            "Cuanza Norte": ["Ndalatando", "Ambaca", "Banga", "Bolongongo", "Cambambe", "Cazengo", "Dembos", "Golungo Alto", "Gonguembo", "Lucala", "Quiculungo"],
            "Cuanza Sul": ["Lubango", "Chibia", "Humpata", "Quilengues", "Cacula"],
            "Bengo" : ["Caxito", "Ambriz", "Bula Atumba", "Dande", "Nambuangongo", "Pango Aluquém"],
            "Móxico": ["Móxica", "Luena", "Cameia", "Leua", "Luchazes", "Mussende"],
            "Bié": ["Kuito", "Andulo", "Chinguar", "Chitembo", "Cuemba", "Cuito Cuanavale", "Cuíto", "Nharea"],
            "Lunda Sul": ["Lunda Sul", "Cacolo", "Dala", "Muconda", "Saurimo"],
            

            # Adiciona as outras províncias conforme necessário
        }

        self.stdout.write(self.style.SUCCESS('A iniciar o povoamento...'))

        for prov_nome, municipios in dados_angola.items():
            # Criar ou buscar a província
            provincia, created = Provincia.objects.get_or_create(nome=prov_nome)
            if created:
                self.stdout.write(f'Província {prov_nome} criada.')

            for mun_nome in municipios:
                # Criar o município ligado à província
                Municipio.objects.get_or_create(nome=mun_nome, provincia=provincia)
            
        self.stdout.write(self.style.SUCCESS('Dados de Angola povoados com sucesso!'))