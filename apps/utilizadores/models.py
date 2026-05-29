import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_login_token_jti = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'auth_user' # Mantém o nome da tabela se preferires