from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    registrar_cliente, login_cliente, login_medico_admin,
    verificar_rut,  # listar_especialidades removed
    UsuarioViewSet, PacienteViewSet, AdministradorViewSet,
    MedicoViewSet, CitaViewSet, AgendaViewSet,
    NotificacionViewSet, HorarioViewSet, EspecialidadViewSet,
    MedicoEspecialidadViewSet
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'pacientes', PacienteViewSet)
router.register(r'administradores', AdministradorViewSet)
router.register(r'medicos', MedicoViewSet)
router.register(r'citas', CitaViewSet)
router.register(r'agendas', AgendaViewSet)
router.register(r'notificaciones', NotificacionViewSet)
router.register(r'medico-especialidades', MedicoEspecialidadViewSet)
router.register(r'horarios', HorarioViewSet)
router.register(r'especialidades', EspecialidadViewSet)  # nuevo

urlpatterns = [
    path('registrar/', registrar_cliente, name='registrar'),
    path('login/', login_cliente, name='login'),
    path('login-medico-admin/', login_medico_admin, name='login_medico_admin'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('verificar-rut/', verificar_rut, name='verificar-rut'),
    path('', include(router.urls)),
]
