from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.settings import api_settings


# views.py (ou onde está o teu Serializer)

# serializers.py
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # 1. Obtém os tokens padrão
        data = super().validate(attrs)

        # 2. Gera um ID de acesso para validar
        from rest_framework_simplejwt.tokens import AccessToken
        access = AccessToken(data['access'])
        jti = access['jti']

        # 3. Força a gravação imediata na BD
        self.user.last_login_token_jti = jti
        self.user.save(update_fields=['last_login_token_jti'])
        
        # Debug no console do Django
        print(f"NOVO LOGIN: {self.user.username} - GRAVADO JTI: {jti}")

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Teus dados customizados aqui (papel, filial, etc)
        try:
            funcionario = user.funcionario
            token['nome'] = user.get_full_name()
            token['papel'] = funcionario.papel
            token['filial_id'] = str(funcionario.filial.id)
        except:
            token['papel'] = 'SUPERADMIN'
        
        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer



