from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import jwt
from django.conf import settings

from rest_framework.permissions import BasePermission

class IsAdminUserRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.role and user.role.name == "Администратор"

class BearerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise AuthenticationFailed({
                "success": False,
                "error": "Токен не предоставлен",
                "details": "Нужно авторизоваться"
            })
        parts = auth_header.split()
        print(parts)
        if parts[0].lower() != "bearer":
            raise AuthenticationFailed({
                "success": False,
                "error": "Неверный формат токена",
                "details": "Нужно заново авторизоваться"
            })
        elif len(parts) == 1:
            raise AuthenticationFailed({
                "success": False,
                "error": "Токен не предоставлен",
                "details": "Нужно авторизоваться"
            })
        elif len(parts) > 2:
            raise AuthenticationFailed({
                "success": False,
                "error": "Неверный формат токена",
                "details": "Нужно заново авторизоваться"
            })
        token = parts[1]
        try:
            # Обработка тестового токена (создаем тестового пользователя)
            if token == 'test-token':
                User = get_user_model()
                user, _ = User.objects.get_or_create(
                    email="test@example.com",
                    defaults={'is_active': True}
                )
                return (user, None)

            decoded_token = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )

            email = decoded_token.get("email")
            if not email:
                raise AuthenticationFailed({
                    "success": False,
                    "error": "Неверный формат токена",
                    "details": "Нужно заново авторизоваться"
                })
            User = get_user_model()
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(
                    email=email,
                    is_active=True,
                )

            return (user, None)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed({
                "success": False,
                "error": "Токен истек",
                "details": "Нужно заново авторизоваться"
            })
        except jwt.InvalidTokenError:
            raise AuthenticationFailed({
                "success": False,
                "error": "Неверный формат токена",
                "details": "Нужно заново авторизоваться"
            })
