from django.db import models  # Importa el módulo de modelos de Django
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist

class Cliente(models.Model):
    id = models.IntegerField(primary_key=True, db_column="ID")  
    cod_cliente = models.CharField(max_length=100, unique=True, db_column="COD_CLIENTE")
    dni = models.CharField(max_length=8, db_column="DNI")
    nombre = models.CharField(max_length=100, db_column="NOMBRE")
    apellidos = models.CharField(max_length=100, db_column="APELLIDOS")
    correo = models.EmailField(blank=True, null=True, db_column="CORREO")
    celular = models.CharField(max_length=20, blank=True, null=True, db_column="CELULAR")
    status = models.CharField(max_length=50, blank=True, null=True, db_column="STATUS")
    fecha_inicio = models.DateField(blank=True, null=True, db_column="FECHA_INICIO")
    fecha_final = models.DateField(blank=True, null=True, db_column="FECHA_FINAL")
    provincia = models.CharField(max_length=100, blank=True, null=True, db_column="PROVINCIA")
    ficha_ruc = models.CharField(max_length=20, blank=True, null=True, db_column="FICHA_RUC")
    codigo_referido = models.CharField(max_length=50, blank=True, null=True, db_column="CODIGO_REFERIDO")
    nombre_referido = models.CharField(max_length=100, blank=True, null=True, db_column="NOMBRE_REFERIDO")
    cuenta_banco_referido = models.CharField(max_length=50, blank=True, null=True, db_column="CUENTA_BANCO_REFERIDO")
    cuenta_interbancario_referido = models.CharField(max_length=50, blank=True, null=True, db_column="CUENTA_INTERBANCARIO_REFERIDO")
    cod_tarifa = models.CharField(max_length=100,unique=True, db_column="COD_TARIFA")

    class Meta:
        managed = False   # ❌ muy importante: Django no intentará crear ni modificar esta tabla
        db_table = "CLIENTE"

    def __str__(self):
        return f"{self.cod_cliente} - {self.nombre} {self.apellidos}"



# Modelo TarifaOperacion
class TarifaOperacion(models.Model):
    # Código único de la tarifa
    cod_tarifa = models.CharField(max_length=100, unique=True, primary_key=True)
    # Descripción de la tarifa
    descripcion = models.CharField(max_length=200)
    # Costo calculado por porcentaje
    costo_por_porcentaje = models.DecimalField(max_digits=18, decimal_places=4)
    # Costo fijo
    costo_fijo = models.DecimalField(max_digits=18, decimal_places=2)

    def calcular_comision(self, monto: Decimal) -> Decimal:
        if monto > 1500:
            return monto * (self.costo_por_porcentaje or Decimal('0.00'))
        return self.costo_fijo or Decimal('0.00')
    
    class Meta:
        managed =  False
        db_table = "TARIFA_OPERACION"


# Modelo BCP (Banco de Crédito del Perú)
class BCP(models.Model):
    # Código único de la operación
    cod_bcp = models.CharField(max_length=100, unique=True)
    # Fecha de la operación
    fecha = models.DateField(blank=True, null=True)
    # Fecha de valuta
    fecha_valuta = models.DateField(blank=True, null=True)
    # Descripción de la operación
    descripcion = models.CharField(max_length=200)
    # Monto de la operación
    monto = models.DecimalField(max_digits=18, decimal_places=2)
    # Sucursal o agencia (opcional)
    sucursal_agencia = models.CharField(max_length=100, blank=True, null=True)
    # Número de operación (opcional)
    n_operacion = models.CharField(max_length=50, blank=True, null=True)
    # Usuario que registró la operación (opcional)
    usuario = models.CharField(max_length=100, blank=True, null=True)

    # Columnas reales en la base de datos
    saldo = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    comision = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    lm_pagar = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    ganancia_referido = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    #cod_tarifa = models.CharField(max_length=100, blank=True, null=True )

    # Relación con cliente y tarifa
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        to_field="cod_cliente",
        db_column="COD_CLIENTE"
    )
    tarifa = models.ForeignKey(
        TarifaOperacion,
        on_delete=models.CASCADE,
        to_field="cod_tarifa",
        db_column="COD_TARIFA"
    )

    # Campo temporal (no existe en la base de datos) para manejar saldo inicial
    _saldo_inicial = 0  

    @property
    def saldo_inicial(self):
        # Getter del saldo inicial temporal
        return self._saldo_inicial

    @saldo_inicial.setter
    def saldo_inicial(self, value):
        self._saldo_inicial  = value or Decimal('0.00')

    def calcular_datos(self):
        monto = self.monto or Decimal('0.00')
        saldo_inicial = self._saldo_inicial or Decimal('0.00')

        # Saldo
        self.saldo = monto + saldo_inicial

        # Buscar cliente si existe
        cliente_obj = None
        if hasattr(self, "cliente_id") and self.cliente_id:
            try:
                cliente_obj = self.cliente  # relación FK ya cargada
            except ObjectDoesNotExist:
                cliente_obj = None

        # Buscar tarifa
        tarifa_obj = None
        if cliente_obj and cliente_obj.cod_tarifa:
            tarifa_obj = TarifaOperacion.objects.filter(cod_tarifa=cliente_obj.cod_tarifa).first()
        else:
            # Tarifa por defecto si no tiene cliente o cod_tarifa
            tarifa_obj = TarifaOperacion.objects.filter(cod_tarifa="TARIFA01").first()


        # Comisión
        if tarifa_obj:
            if monto > 1500: 
                # Se aplica porcentaje
                self.comision = monto * (tarifa_obj.costo_por_porcentaje or Decimal('0.00'))
            else:
                # Se aplica costo fijo
                self.comision = tarifa_obj.costo_fijo or Decimal('0.00')
        else:
            self.comision = Decimal('0.00')

        


        # LM a pagar
        self.lm_pagar = self.saldo - self.comision

        # 🔥 Ganancia de referido (nueva lógica)
        self.ganancia_referido = Decimal('0.00')
        if cliente_obj and cliente_obj.codigo_referido:
            try:
                cod_ref = int(cliente_obj.codigo_referido)
            except:
                cod_ref = None

            if cod_ref == 6:
                if monto > 1500:
                    self.ganancia_referido = monto * Decimal('0.001')  # 0.1%
                else:
                    self.ganancia_referido = Decimal('1.5')
            else:
                self.ganancia_referido = Decimal('0.00')  # "FALSO"

        # Guardamos el objeto tarifa temporalmente para usar luego
        self.tarifa = tarifa_obj

    def save(self, *args, **kwargs):
        self.calcular_datos()
        super().save(*args, **kwargs)

