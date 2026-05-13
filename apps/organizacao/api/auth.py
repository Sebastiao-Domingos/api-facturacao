from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Adicionar dados personalizados ao Payload do Token
        try:
            funcionario = user.funcionario
            token['nome'] = user.get_full_name()
            token["id"] = str(user.id) # Convertemos UUID para string
            token['papel'] = funcionario.papel
            token['filial_id'] = str(funcionario.filial.id) # Convertemos UUID para string
        except:
            token['papel'] = 'SUPERADMIN'

        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer