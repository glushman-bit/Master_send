from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор профиля (read)."""
    initials = serializers.ReadOnlyField()
    is_master = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'avatar', 'bio', 'role', 'initials', 'is_master',
            'date_joined',
        )
        read_only_fields = ('id', 'username', 'role', 'date_joined')


class RegisterSerializer(serializers.ModelSerializer):
    """Регистрация нового пользователя."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Пароли не совпадают.'})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Старый пароль введён неверно.')
        return value


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Обновление профиля."""
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'avatar', 'bio')