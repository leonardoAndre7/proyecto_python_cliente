from django.urls import path
from . import views

app_name = "banco"

urlpatterns = [
    path('importar/', views.importar_excel, name='importar_excel'),
    path('confirmar/', views.confirmar_import, name='confirmar_import'),
    path("exportar_excel/", views.exportar_excel, name="exportar_excel"),
    
]
