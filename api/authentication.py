from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Usuario

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        """
        Obtiene el usuario desde el token JWT
        """
        try:
            user_id = validated_token.get('user_id')
            if user_id is None:
                raise AuthenticationFailed('Token no contiene user_id')
            
            user = Usuario.objects.get(id=user_id)
            return user
        except Usuario.DoesNotExist:
            raise AuthenticationFailed('Usuario no encontrado')
        except Exception as e:
            raise AuthenticationFailed(f'Error al validar token: {str(e)}')