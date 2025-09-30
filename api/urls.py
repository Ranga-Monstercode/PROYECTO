from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    registrar_cliente, login_cliente, login_medico_admin,
    UsuarioViewSet, PacienteViewSet, AdministradorViewSet, MedicoViewSet,
    AgendaViewSet, CitaViewSet, NotificacionViewSet, HorarioViewSet
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'pacientes', PacienteViewSet)
router.register(r'administradores', AdministradorViewSet)
router.register(r'medicos', MedicoViewSet)
router.register(r'agendas', AgendaViewSet)
router.register(r'citas', CitaViewSet)
router.register(r'notificaciones', NotificacionViewSet)
router.register(r'horarios', HorarioViewSet)

urlpatterns = [
    path('registrar/', registrar_cliente, name='registrar'),
    path('login/', login_cliente, name='login'),
    path('login-medico-admin/', login_medico_admin, name='login_medico_admin'),
    
    # Endpoints de JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    path('', include(router.urls)),
]
