from django import forms
from .models import Cliente, TarifaOperacion

class UploadExcelForm(forms.Form):
    archivo = forms.FileField(label="Archivo Excel (.xlsx)")

    # Selección de cliente por defecto (aplicará a todas las filas si no cambian en la preview)
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        required=False,
        label="Cliente (por defecto)"
    )

    # Tarifa/estatus por defecto
    tarifa = forms.ModelChoiceField(
        queryset=TarifaOperacion.objects.all(),
        required=False,
        label="Tarifa (por defecto)"
    )

    saldo_inicial = forms.DecimalField(
        max_digits=18, decimal_places=2, required=False, initial=0,
        label="Saldo inicial (por defecto)"
    )
