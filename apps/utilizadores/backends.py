# backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Tenta encontrar o utilizador pelo username OU pelo email
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # Caso existam múltiplos (raro com Unique), pega o primeiro
            user = User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).order_size('id').first()

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None