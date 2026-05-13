# apps/utilizadores/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions

class SingleTokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        auth_tuple = super().authenticate(request)
        if not auth_tuple:
            return None

        user, validated_token = auth_tuple

        # 🔍 Debug: Descomenta a linha abaixo para ver no terminal se os JTIs estão a chegar
        # print(f"DB: {user.last_login_token_jti} | TOKEN: {validated_token['jti']}")

        db_jti = getattr(user, 'last_login_token_jti', None)
        # O SimpleJWT guarda o JTI na chave 'jti' do payload
        token_jti = validated_token.get('jti')


         # ESTA LINHA VAI MOSTRAR O ERRO NO TEU TERMINAL
        print(f"\n--- VALIDANDO SESSÃO ---")
        print(f"USER: {user.username}")
        print(f"JTI NA DB:    {db_jti}")
        print(f"JTI NO TOKEN: {token_jti}")
        print(f"SÃO IGUAIS?   {db_jti == token_jti}")
        print(f"------------------------\n")

        if db_jti and token_jti and db_jti != token_jti:
            raise exceptions.AuthenticationFailed(
                "Sessão inválida. Outro dispositivo acedeu a esta conta.",
                code="multiple_sessions"
            )

        return user, validated_token
    




