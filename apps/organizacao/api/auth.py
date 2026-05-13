from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
    

# views.py (ou onde está o teu Serializer)

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # O SimpleJWT usa 'username' como chave padrão no JSON que vem do Front
        # Mas o nosso Backend agora sabe que esse valor pode ser um email.
        data = super().validate(attrs)
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # ... o teu código de payload (nome, papel, filial_id) continua aqui igual ...
        try:
            funcionario = user.funcionario
            token['nome'] = user.get_full_name()
            token["id"] = str(user.id)
            token['papel'] = funcionario.papel
            token['filial_id'] = str(funcionario.filial.id)
        except:
            token['papel'] = 'SUPERADMIN'
        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer



