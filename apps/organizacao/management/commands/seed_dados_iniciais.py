# apps/organizacao/management/commands/seed_dados_iniciais.py
"""
Comando Django para popular a base de dados com dados iniciais.
Executar: python manage.py seed_dados_iniciais

Ordem de criação (respeita dependências):
1. Users (auth)
2. Províncias e Municípios (se ainda não existirem)
3. Endereços
4. Empresa
5. Filial (Sede)
6. Funcionários (SUPERADMIN + ADMIN)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.organizacao.models import Empresa, Filial, Endereco, Funcionario, Provincia, Municipio
from datetime import date

User = get_user_model()


class Command(BaseCommand):
    help = 'Popula a base de dados com dados iniciais (empresa, filial sede, funcionários)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🌱 ===== INICIANDO CRIAÇÃO DE DADOS INICIAIS ====='))

        # ═══════════════════════════════════════
        # PASSO 1: Verificar/Criar Províncias e Municípios
        # ═══════════════════════════════════════
        self.stdout.write('\n📌 PASSO 1: Verificar Localização')
        
        # Garantir que Luanda existe
        provincia_luanda, created = Provincia.objects.get_or_create(nome='Luanda')
        if created:
            self.stdout.write(f'  🆕 Província criada: {provincia_luanda.nome}')
        else:
            self.stdout.write(f'  ✅ Província encontrada: {provincia_luanda.nome}')

        # Garantir que o município de Luanda existe
        municipio_luanda, created = Municipio.objects.get_or_create(
            nome='Luanda',
            provincia=provincia_luanda
        )
        if created:
            self.stdout.write(f'  🆕 Município criado: {municipio_luanda.nome}')
        else:
            self.stdout.write(f'  ✅ Município encontrado: {municipio_luanda.nome}')

        # ═══════════════════════════════════════
        # PASSO 2: UTILIZADORES
        # ═══════════════════════════════════════
        self.stdout.write('\n📌 PASSO 2: Utilizadores')
        
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@sergao.co.ao',
                'password': 'Admin123!',
                'first_name': 'Administrador',
                'last_name': 'Sistema',
                'is_superuser': True,
                'is_staff': True,
            },
            {
                'username': 'sebastiao@gmail.com',
                'email': 'sebastiao@gmail.com',
                'password': 'Sebastiao123!',
                'first_name': 'Sebastião',
                'last_name': 'Domingos',
                'is_superuser': True,
                'is_staff': True,
            },
            {
                'username': 'geral@gmail.com',
                'email': 'geral@gmail.com',
                'password': 'Geral123!',
                'first_name': 'Gerente',
                'last_name': 'Geral',
                'is_staff': True,
            },
        ]

        users_map = {}
        for u in users_data:
            user, created = User.objects.get_or_create(
                username=u['username'],
                defaults={
                    'email': u['email'],
                    'first_name': u['first_name'],
                    'last_name': u['last_name'],
                    'is_superuser': u.get('is_superuser', False),
                    'is_staff': u.get('is_staff', False),
                }
            )
            if created:
                user.set_password(u['password'])
                user.save()
            users_map[u['username']] = user
            status = '🆕' if created else '⏭️ (já existe)'
            self.stdout.write(f'  {status} {u["first_name"]} {u["last_name"]} ({u["username"]})')

        # ═══════════════════════════════════════
        # PASSO 3: ENDEREÇO DA SEDE
        # ═══════════════════════════════════════
        self.stdout.write('\n📌 PASSO 3: Endereço da Sede')
        
        endereco_sede, created = Endereco.objects.get_or_create(
            rua='Av. Deolinda Rodrigues, 123',
            bairro='Ingombota',
            municipio=municipio_luanda,
            defaults={
                'ponto_referencia': 'Próximo ao edifício da Sonangol',
            }
        )
        status = '🆕' if created else '⏭️ (já existe)'
        self.stdout.write(f'  {status} {endereco_sede.rua}, {endereco_sede.bairro} - {municipio_luanda.nome}')

        # ═══════════════════════════════════════
        # PASSO 4: EMPRESA
        # ═══════════════════════════════════════
        self.stdout.write('\n📌 PASSO 4: Empresa')
        
        empresa, created = Empresa.objects.get_or_create(
            nif='0077223456',
            defaults={
                'nome_fantasia': 'SERGAO',
                'razao_social': 'SERGAO, LDA',
                'slogan': 'Soluções Digitais',
                'regime_tributario': 'SIMPLIFICADO',
                'moeda_padrao': 'AOA',
                'endereco': endereco_sede,
            }
        )
        status = '🆕' if created else '⏭️ (já existe)'
        self.stdout.write(f'  {status} {empresa.nome_fantasia} | NIF: {empresa.nif} | Regime: {empresa.regime_tributario}')

        # ═══════════════════════════════════════
        # PASSO 5: FILIAL SEDE
        # ═══════════════════════════════════════
        self.stdout.write('\n📌 PASSO 5: Filial Sede')
        
        filial_sede, created = Filial.objects.get_or_create(
            empresa=empresa,
            codigo_agt='F001',
            defaults={
                'nome': 'SERGAO - Sede',
                'e_sede': True,
                'serie_documentos': 'FAT',
                'endereco': endereco_sede,
                'ativo': True,
            }
        )
        status = '🆕' if created else '⏭️ (já existe)'
        self.stdout.write(f'  {status} {filial_sede.nome} | Código: {filial_sede.codigo_agt} | Série: {filial_sede.serie_documentos} | Sede: {filial_sede.e_sede}')

        # ═══════════════════════════════════════
        # PASSO 6: ENDEREÇOS DOS FUNCIONÁRIOS
        # ═══════════════════════════════════════
        self.stdout.write('\n📌 PASSO 6: Endereços dos Funcionários')
        
        # Endereço do Sebastião (SUPERADMIN)
        endereco_sebastiao, created = Endereco.objects.get_or_create(
            rua='Rua da Liberdade, 45',
            bairro='Maianga',
            municipio=municipio_luanda,
            defaults={
                'ponto_referencia': 'Perto do Largo da Maianga',
            }
        )
        status = '🆕' if created else '⏭️ (já existe)'
        self.stdout.write(f'  {status} Sebastião → {endereco_sebastiao.rua}, {endereco_sebastiao.bairro}')

        # Endereço do Gerente (ADMIN)
        endereco_gerente, created = Endereco.objects.get_or_create(
            rua='Rua 10, Casa 5',
            bairro='Alvalade',
            municipio=municipio_luanda,
            defaults={
                'ponto_referencia': 'Próximo à Escola Primária',
            }
        )
        status = '🆕' if created else '⏭️ (já existe)'
        self.stdout.write(f'  {status} Gerente → {endereco_gerente.rua}, {endereco_gerente.bairro}')

        # ═══════════════════════════════════════
        # PASSO 7: FUNCIONÁRIOS
        # ═══════════════════════════════════════
        self.stdout.write('\n📌 PASSO 7: Funcionários')
        
        funcionarios_data = [
            {
                'user': users_map['sebastiao@gmail.com'],
                'filial': filial_sede,
                'papel': 'SUPERADMIN',
                'bi': '001234567LA001',
                'cargo': 'Director Geral',
                'telemovel': '923456789',
                'endereco': endereco_sebastiao,
            },
            {
                'user': users_map['geral@gmail.com'],
                'filial': filial_sede,
                'papel': 'ADMIN',
                'bi': '002345678LA002',
                'cargo': 'Administrador de Filial',
                'telemovel': '934567890',
                'endereco': endereco_gerente,
            },
        ]

        for func in funcionarios_data:
            funcionario, created = Funcionario.objects.get_or_create(
                user=func['user'],
                bi=func['bi'],
                defaults={
                    'filial': func['filial'],
                    'papel': func['papel'],
                    'cargo': func['cargo'],
                    'telemovel': func['telemovel'],
                    'endereco': func['endereco'],
                    'ativo': True,
                }
            )
            status = '🆕' if created else '⏭️ (já existe)'
            self.stdout.write(f'  {status} {func["user"].get_full_name()} → {func["papel"]} @ {func["filial"].nome} | BI: {func["bi"]}')

        # ═══════════════════════════════════════
        # RESUMO FINAL
        # ═══════════════════════════════════════
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ DADOS INICIAIS CRIADOS COM SUCESSO!'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'  🏙️  Províncias:  {Provincia.objects.count()}')
        self.stdout.write(f'  🏘️  Municípios:  {Municipio.objects.count()}')
        self.stdout.write(f'  👑 Utilizadores: {User.objects.count()}')
        self.stdout.write(f'  🏢 Empresas:    {Empresa.objects.count()}')
        self.stdout.write(f'  🏪 Filiais:     {Filial.objects.count()}')
        self.stdout.write(f'  👔 Funcionários: {Funcionario.objects.count()}')
        self.stdout.write('=' * 60)
        self.stdout.write('\n🔑 CREDENCIAIS DE ACESSO:')
        self.stdout.write('─' * 40)
        self.stdout.write(f'  SUPERADMIN: sebastiao@gmail.com / Sebastiao123!')
        self.stdout.write(f'  ADMIN:      geral@gmail.com / Geral123!')
        self.stdout.write(f'  Django:     admin / Admin123!')
        self.stdout.write('─' * 40)
        self.stdout.write(f'\n🏢 Empresa:  {empresa.nome_fantasia} ({empresa.nif})')
        self.stdout.write(f'🏪 Sede:     {filial_sede.nome} ({filial_sede.codigo_agt})')
        self.stdout.write('=' * 60)