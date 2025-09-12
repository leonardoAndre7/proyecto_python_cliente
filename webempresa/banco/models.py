from django.db import models  # Importa el módulo de modelos de Django

# Modelo Cliente
class Cliente(models.Model):
    # Código único del cliente
    cod_cliente = models.CharField(max_length=100, unique=True)
    # DNI del cliente (8 caracteres)
    dni = models.CharField(max_length=8)
    # Nombre y apellidos del cliente
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    # Correo electrónico (opcional)
    correo = models.EmailField(blank=True, null=True)
    # Número de celular (opcional)
    celular = models.CharField(max_length=20, blank=True, null=True)
    # Estado del cliente (opcional)
    status = models.CharField(max_length=50, blank=True, null=True)
    # Fecha de inicio y final (opcional)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_final = models.DateField(blank=True, null=True)
    # Provincia del cliente (opcional)
    provincia = models.CharField(max_length=100, blank=True, null=True)
    # Ficha o RUC asociado (opcional)
    ficha_ruc = models.CharField(max_length=20, blank=True, null=True)
    # Código y nombre de referido (opcional)
    codigo_referido = models.CharField(max_length=50, blank=True, null=True)
    nombre_referido = models.CharField(max_length=100, blank=True, null=True)
    # Cuenta bancaria e interbancaria del referido (opcional)
    cuenta_banco_referido = models.CharField(max_length=50, blank=True, null=True)
    cuenta_interbancario_referido = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        # Representación en string del cliente
        return f"{self.cod_cliente} - {self.nombre} {self.apellidos}"


# Modelo TarifaOperacion
class TarifaOperacion(models.Model):
    # Código único de la tarifa
    cod_tarifa = models.CharField(max_length=100, unique=True)
    # Descripción de la tarifa
    descripcion = models.CharField(max_length=200)
    # Costo calculado por porcentaje
    costo_por_porcentaje = models.DecimalField(max_digits=18, decimal_places=4)
    # Costo fijo
    costo_fijo = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        # Representación en string de la tarifa
        return f"{self.descripcion}"


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
        # Setter del saldo inicial temporal
        self._saldo_inicial = value or 0

    def calcular_datos(self):
        """
        Calcula automáticamente saldo y comisión antes de guardar.
        Si el monto > 1500, aplica comisión por porcentaje,
        de lo contrario aplica costo fijo.
        """
        self.saldo = (self.monto or 0) + (self._saldo_inicial or 0)
        if self.monto and self.tarifa:
            if self.monto > 1500:
                self.comision = self.monto * self.tarifa.costo_por_porcentaje
            else:
                self.comision = self.tarifa.costo_fijo

    def save(self, *args, **kwargs):
        # Calcula datos antes de guardar
        self.calcular_datos()
        super().save(*args, **kwargs)

    class Meta:
        # Especifica el nombre real de la tabla en la base de datos
        db_table = "BCP"
