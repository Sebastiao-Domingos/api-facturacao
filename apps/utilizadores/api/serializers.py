# apps/organizacao/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

class UserListSerializer(serializers.ModelSerializer):
    nome_completo = serializers.SerializerMethodField()
    email = serializers.EmailField()
    is_active = serializers.BooleanField()

    class Meta:
        model = User
        fields = ['id', 'email', 'nome_completo', 'is_active', 'last_login', 'date_joined']

    def get_nome_completo(self, obj):
        return obj.get_full_name()

class UserPasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        # Adicione validações adicionais (ex: força)
        return value