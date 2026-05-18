from rest_framework import serializers
from apps.organizacao.api.serializers import EnderecoSerializer
from apps.organizacao.models.localizacao import Endereco
from ..models import Cliente



class ClienteSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    data_criacao = serializers.DateTimeField(source='created_at', format='%Y-%m-%dT%H:%M:%SZ', read_only=True)
    
    # Endereço tratado como um objeto aninhado no JSON
    endereco = EnderecoSerializer(required=False, allow_null=True)

    class Meta:
        model = Cliente
        fields = [
            'id', 'tipo', 'tipo_display', 'nome', 'nif', 'email', 'telefone',
            'endereco', 'razao_social', 'website', 'bilhete_identidade', 'ativo', 'data_criacao'
        ]

    def create(self, validated_data):
        """Trata a criação do Endereço antes de criar o Cliente"""
        endereco_data = validated_data.pop('endereco', None)
        endereco_instancia = None
        
        if endereco_data:
            endereco_instancia = Endereco.objects.create(**endereco_data)
            
        cliente = Cliente.objects.create(endereco=endereco_instancia, **validated_data)
        return cliente

    def update(self, instance, validated_data):
        """Trata a atualização do Endereço junto com a ficha do Cliente"""
        endereco_data = validated_data.pop('endereco', None)
        
        # Atualiza os dados do cliente
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Atualiza ou cria o endereço aninhado
        if endereco_data:
            if instance.endereco:
                for attr, value in endereco_data.items():
                    setattr(instance.endereco, attr, value)
                instance.endereco.save()
            else:
                novo_endereco = Endereco.objects.create(**endereco_data)
                instance.endereco = novo_endereco
                instance.save()
                
        return instance
    def validate(self, data):
        """
        Garante no nível da API REST que campos exclusivos não venham nulos 
        conforme a regra de negócio selecionada no Front-end.
        """
        tipo = data.get('tipo', self.instance.tipo if self.instance else 'P')
        
        if tipo == 'E':
            nome = data.get('nome', self.instance.nome if self.instance else '')
            razao_social = data.get('razao_social', self.instance.razao_social if self.instance else '')
            if not razao_social and nome:
                data['razao_social'] = nome
                
        elif tipo == 'P':
            # Evita ruído de payload: limpa dados corporativos se for particular
            data['razao_social'] = None
            data['website'] = None
            
        return data