# apps/utilizadores/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from apps.organizacao.models import Funcionario

class SingleTokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        auth_tuple = super().authenticate(request)
        if not auth_tuple:
            return None

        user, validated_token = auth_tuple

        # Verifica se o usuário tem perfil de funcionário e se está ativo
        try:
            funcionario = user.funcionario
            if not funcionario.ativo:
                raise exceptions.AuthenticationFailed(
                    "Conta desativada. Contacte o administrador.",
                    code="account_disabled"
                )
        except Funcionario.DoesNotExist:
            # Superuser ou usuário sem funcionário – permite acesso
            pass

        # Verifica se o usuário está ativo no Django
        if not user.is_active:
            raise exceptions.AuthenticationFailed(
                "Usuário inativo.",
                code="user_inactive"
            )

        # Validação de sessão única (JTI)
        db_jti = getattr(user, 'last_login_token_jti', None)
        token_jti = validated_token.get('jti')

        if db_jti and token_jti and db_jti != token_jti:
            raise exceptions.AuthenticationFailed(
                "Sessão inválida. Outro dispositivo acedeu a esta conta.",
                code="multiple_sessions"
            )

        return user, validated_token