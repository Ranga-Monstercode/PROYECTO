from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    registrar_cliente, login, verificar_rut, verificar_o_crear_rut, actualizar_usuario_con_historial,
    UsuarioViewSet, PacienteViewSet, AdministradorViewSet,
    MedicoViewSet, CitaViewSet, NotificacionViewSet, HorarioViewSet,
    EspecialidadViewSet, MedicoEspecialidadViewSet, BoxViewSet
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'pacientes', PacienteViewSet)
router.register(r'administradores', AdministradorViewSet)
router.register(r'medicos', MedicoViewSet)
router.register(r'citas', CitaViewSet)
router.register(r'notificaciones', NotificacionViewSet)
router.register(r'horarios', HorarioViewSet)
router.register(r'especialidades', EspecialidadViewSet)
router.register(r'medico-especialidades', MedicoEspecialidadViewSet)
router.register(r'boxes', BoxViewSet)

urlpatterns = [
    path('registrar/', registrar_cliente, name='registrar'),
    path('login/', login, name='login'),
    path('verificar-rut/', verificar_rut, name='verificar-rut'),
    path('verificar-o-crear-rut/', verificar_o_crear_rut, name='verificar-o-crear-rut'),
    path('actualizar-usuario-historial/', actualizar_usuario_con_historial, name='actualizar-usuario-historial'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('', include(router.urls)),
]
