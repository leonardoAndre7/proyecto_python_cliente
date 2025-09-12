import os
from decimal import Decimal
import pandas as pd
from django.shortcuts import render, redirect
from django.conf import settings
from django.db import transaction
from .forms import UploadExcelForm
from .models import BCP, TarifaOperacion, Cliente
from django.urls import reverse
import re

def importar_excel(request):
    """
    Función que permite subir un archivo Excel y mostrar una PREVIEW editable
    antes de guardar los datos en la base de datos.
    """
    if request.method == "POST":
        form = UploadExcelForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            cliente_default = form.cleaned_data.get('cliente')
            tarifa_default = form.cleaned_data.get('tarifa')
            saldo_inicial_default = form.cleaned_data.get('saldo_inicial') or Decimal('0.00')

            df = pd.read_excel(archivo, sheet_name=0, dtype=str)
            df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]

            rows = []

            for i, r in df.iterrows():
                cod_bcp = str(r.get("COD_BCP") or r.get("COD_BCP ") or "")

                # --- Fechas manejando valores nulos ---
                fecha_raw = r.get("FECHA")
                fecha_valuta_raw = r.get("FECHA_VALUTA") or r.get("FECHA_VAL") or None

                def safe_fecha(f):
                    """Convierte NaT o valores inválidos a None, si no devuelve fecha."""
                    try:
                        if pd.isna(f):
                            return None
                        return pd.to_datetime(f)
                    except:
                        return None

                fecha = safe_fecha(fecha_raw)
                fecha_valuta = safe_fecha(fecha_valuta_raw)

                # Otros campos
                descripcion = r.get("DESCRIPCIÓN_OPERACIÓN") or r.get("DESCRIPCION_OPERACION") or ""
                sucursal_agencia = r.get("SUCURSAL_AGENCIA") or ""
                n_operacion = r.get("N_OPERACIÓN") or r.get("N_OPERACION") or ""

                # Monto
                monto_raw = r.get("MONTO") or r.get("MTO") or "0"
                try:
                    monto = Decimal(str(monto_raw).replace(",", ""))
                except:
                    monto = Decimal('0.00')

                # Extraer DNI de los últimos 8 dígitos de la descripción
                match = re.search(r'(\d{8})$', descripcion)
                dni_encontrado = match.group(1) if match else None

                # Inicializamos datos del cliente
                cliente_auto = None
                cliente_nombre = ""
                cliente_apellidos = ""
                correo = ""
                celular = ""
                status = ""
                provincia = ""
                codigo_referido = ""
                nombre_referido = ""
                cuenta_banco_referido = ""
                cuenta_interbancario_referido = ""

                cliente_obj = None
                if dni_encontrado:
                    cliente_obj = Cliente.objects.filter(dni=dni_encontrado).first()

                # Si no se encontró por DNI, usa cliente default del formulario
                if not cliente_obj and cliente_default:
                    cliente_obj = cliente_default

                # Asignar datos automáticamente
                cliente_auto = cliente_obj.COD_CLIENTE if cliente_obj else ""
                cliente_nombre = f"{cliente_obj.NOMBRE} {cliente_obj.APELLIDOS}" if cliente_obj else ""
                correo = cliente_obj.CORREO or "" if cliente_obj else ""
                celular = cliente_obj.CELULAR or "" if cliente_obj else ""
                status = cliente_obj.STATUS or "" if cliente_obj else ""
                provincia = cliente_obj.PROVINCIA or "" if cliente_obj else ""
                codigo_referido = cliente_obj.CODIGO_REFERIDO or "" if cliente_obj else ""
                nombre_referido = cliente_obj.NOMBRE_REFERIDO or "" if cliente_obj else ""
                cuenta_banco_referido = cliente_obj.CUENTA_BANCO_REFERIDO or "" if cliente_obj else ""
                cuenta_interbancario_referido = cliente_obj.CUENTA_INTERBANCARIO_REFERIDO or "" if cliente_obj else ""


                # Diccionario de fila para preview
                row = {
                    "index": i,
                    "cod_bcp": cod_bcp,
                    "fecha": '' if fecha is None else fecha.strftime('%Y-%m-%d'),
                    "fecha_valuta": '' if fecha_valuta is None else fecha_valuta.strftime('%Y-%m-%d'),
                    "descripcion": descripcion,
                    "monto": monto,
                    "sucursal_agencia": sucursal_agencia,
                    "n_operacion": n_operacion,
                    "usuario": r.get("USUARIO") or "",
                    # Datos automáticos del cliente
                    "dni_cliente": dni_encontrado,
                    "cliente_default": cliente_auto or (cliente_default.COD_CLIENTE if cliente_default else ""),
                    "cliente_nombre": cliente_obj.NOMBRE if cliente_obj else "",
                    "cliente_apellidos": cliente_obj.APELLIDOS if cliente_obj else "",
                    "correo": cliente_obj.CORREO or "" if cliente_obj else "",
                    "celular": cliente_obj.CELULAR or "" if cliente_obj else "",
                    "status": cliente_obj.STATUS or "" if cliente_obj else "",
                    "provincia": cliente_obj.PROVINCIA or "" if cliente_obj else "",
                    "codigo_referido": cliente_obj.CODIGO_REFERIDO or "" if cliente_obj else "",
                    "nombre_referido": cliente_obj.NOMBRE_REFERIDO or "" if cliente_obj else "",
                    "cuenta_banco_referido": cliente_obj.CUENTA_BANCO_REFERIDO or "" if cliente_obj else "",
                    "cuenta_interbancario_referido": cliente_obj.CUENTA_INTERBANCARIO_REFERIDO or "" if cliente_obj else "",
                    "tarifa_default": tarifa_default.cod_tarifa if tarifa_default else "",
                    "saldo_inicial_default": saldo_inicial_default,
                }


                rows.append(row)

            # Contexto para renderizar el template
            context = {
                "rows": rows,
                "clientes": Cliente.objects.all(),
                "tarifas": TarifaOperacion.objects.all(),
                "form": form,
            }

            return render(request, "banco/preview.html", context)

    else:
        form = UploadExcelForm()

    return render(request, "banco/importar_excel.html", {"form": form})

@transaction.atomic
def confirmar_import(request):
    """
    Función que guarda los registros confirmados desde la preview.
    """
    if request.method != "POST":
        return redirect(reverse("banco:importar_excel"))

    # Obtenemos listas de cada campo
    cod_bcp_list = request.POST.getlist("cod_bcp")
    fecha_list = request.POST.getlist("fecha")
    fecha_valuta_list = request.POST.getlist("fecha_valuta")
    descripcion_list = request.POST.getlist("descripcion")
    monto_list = request.POST.getlist("monto")
    sucursal_list = request.POST.getlist("sucursal_agencia")
    n_operacion_list = request.POST.getlist("n_operacion")
    usuario_list = request.POST.getlist("usuario")
    saldo_inicial_list = request.POST.getlist("saldo_inicial")
    codigo_list = request.POST.getlist("codigo")
    cliente_list = request.POST.getlist("cliente")
    tarifa_list = request.POST.getlist("tarifa")

    saved = 0
    errors = []
    total = len(descripcion_list)

    for i in range(total):
        try:
            cod_bcp = cod_bcp_list[i] if i < len(cod_bcp_list) else None

            # Fechas
            f_raw = fecha_list[i] if i < len(fecha_list) else ""
            try:
                fecha = pd.to_datetime(f_raw).date() if f_raw else None
            except:
                fecha = None

            fv_raw = fecha_valuta_list[i] if i < len(fecha_valuta_list) else ""
            try:
                fecha_valuta = pd.to_datetime(fv_raw).date() if fv_raw else None
            except:
                fecha_valuta = None

            descripcion = descripcion_list[i]
            monto = Decimal(monto_list[i].replace(",", "")) if monto_list[i] else Decimal('0.00')
            sucursal_agencia = sucursal_list[i] if i < len(sucursal_list) else ""
            n_operacion = n_operacion_list[i] if i < len(n_operacion_list) else ""
            usuario = usuario_list[i] if i < len(usuario_list) else ""
            saldo_inicial = Decimal(saldo_inicial_list[i].replace(",", "")) if saldo_inicial_list[i] else Decimal('0.00')
            codigo = codigo_list[i] if i < len(codigo_list) else ""

            cliente_obj = Cliente.objects.filter(COD_CLIENTE=cliente_list[i]).first() if cliente_list and cliente_list[i] else None
            tarifa_obj = TarifaOperacion.objects.filter(cod_tarifa=tarifa_list[i]).first() if tarifa_list and tarifa_list[i] else None

            if cod_bcp and BCP.objects.filter(cod_bcp=cod_bcp).exists():
                continue

            b = BCP(
                cod_bcp=cod_bcp or f"autogen_{i}",
                fecha=fecha,
                fecha_valuta=fecha_valuta,
                descripcion=descripcion,
                monto=monto,
                sucursal_agencia=sucursal_agencia,
                n_operacion=n_operacion,
                usuario=usuario,
                codigo=codigo,
                cliente=cliente_obj,
                tarifa=tarifa_obj
            )

            b.saldo_inicial = saldo_inicial
            b.save()
            saved += 1
        except Exception as e:
            errors.append(f"Fila {i}: {str(e)}")

    return render(request, "banco/result.html", {"saved": saved, "errors": errors})
