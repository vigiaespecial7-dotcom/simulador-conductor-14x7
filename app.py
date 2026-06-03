
import calendar
from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Simulador 14x7 - Transporte Especial",
    page_icon="🚐",
    layout="wide"
)

AZUL = "#123A63"
FONDO = "#F6F9FC"

st.markdown(f"""
<style>
.stApp {{ background-color: {FONDO}; }}
.block-container {{ padding-top: 1rem; padding-bottom: 2rem; }}
h1, h2, h3 {{ color: {AZUL}; }}
[data-testid="stMetric"] {{
    background: white;
    border: 1px solid #D8E2EE;
    border-radius: 12px;
    padding: 8px 10px;
    box-shadow: 0 2px 6px rgba(18,58,99,0.06);
}}
[data-testid="stMetricLabel"] {{ font-size: 0.78rem; }}
[data-testid="stMetricValue"] {{ font-size: 1.12rem; }}
div[data-testid="stDataFrame"] {{ background: white; border-radius: 12px; }}
</style>
""", unsafe_allow_html=True)

st.title("🚐 Simulador mensual conductor + vehículo 14x7")
st.caption("Transporte especial empresarial | Nómina operativa mensual + productividad por meta o rangos")

MESES = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
    "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
}
DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def cop(valor):
    return f"${round(float(valor)):,}".replace(",", ".")


def hrs(valor):
    return f"{round(float(valor), 1):,.1f} h".replace(",", ".")


def pct(valor):
    return f"{float(valor) * 100:.2f}%".replace(".", ",")


def rango_horas(inicio, fin):
    base = datetime(2026, 1, 1)
    ini = datetime.combine(base, inicio)
    fi = datetime.combine(base, fin)
    if fi <= ini:
        fi += timedelta(days=1)
    return round((fi - ini).total_seconds() / 3600, 2), ini, fi


def horas_nocturnas_turno(inicio, fin):
    _, ini, fi = rango_horas(inicio, fin)
    cursor = ini
    paso = timedelta(minutes=15)
    nocturnas = 0.0
    while cursor < fi:
        sig = min(cursor + paso, fi)
        bloque = (sig - cursor).total_seconds() / 3600
        t = cursor.time()
        if t >= time(19, 0) or t < time(6, 0):
            nocturnas += bloque
        cursor = sig
    return round(nocturnas, 2)


def tarifa_dom(anio):
    if anio >= 2027:
        return 1.00
    if anio == 2026:
        return 0.90
    return 0.80


def calcular_comision_simple(produccion, meta, porcentaje):
    if produccion >= meta:
        return produccion * porcentaje, "Meta mínima simple", "ACTIVO"
    return 0, "No alcanza meta mínima", "NO APLICA"


def calcular_comision_escalonada(
    produccion,
    porcentaje_base,
    r1_min,
    r1_max,
    r1_factor,
    r2_min,
    r2_max,
    r2_factor,
    r3_min,
    r3_factor,
):
    if r1_min <= produccion <= r1_max:
        return produccion * porcentaje_base * r1_factor, "Rango 1", "ACTIVO"
    if r2_min <= produccion <= r2_max:
        return produccion * porcentaje_base * r2_factor, "Rango 2", "ACTIVO"
    if produccion >= r3_min:
        return produccion * porcentaje_base * r3_factor, "Rango 3", "ACTIVO"
    return 0, "No alcanza rango de comisión", "NO APLICA"



def calcular_pascua(anio):
    """Calcula el domingo de Pascua para generar festivos móviles de Colombia sin librerías externas."""
    a = anio % 19
    b = anio // 100
    c = anio % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)


def siguiente_lunes(fecha):
    """Aplica Ley Emiliani: si no cae lunes, se traslada al lunes siguiente."""
    return fecha + timedelta(days=(7 - fecha.weekday()) % 7)


def festivos_colombia_interno(anio):
    """Festivos Colombia sin dependencia externa, para evitar errores en Streamlit Cloud."""
    pascua = calcular_pascua(anio)
    festivos = {
        date(anio, 1, 1): "Año Nuevo",
        siguiente_lunes(date(anio, 1, 6)): "Día de los Reyes Magos",
        siguiente_lunes(date(anio, 3, 19)): "Día de San José",
        pascua - timedelta(days=3): "Jueves Santo",
        pascua - timedelta(days=2): "Viernes Santo",
        date(anio, 5, 1): "Día del Trabajo",
        pascua + timedelta(days=43): "Ascensión del Señor",
        pascua + timedelta(days=64): "Corpus Christi",
        pascua + timedelta(days=71): "Sagrado Corazón de Jesús",
        siguiente_lunes(date(anio, 6, 29)): "San Pedro y San Pablo",
        date(anio, 7, 20): "Día de la Independencia",
        date(anio, 8, 7): "Batalla de Boyacá",
        siguiente_lunes(date(anio, 8, 15)): "Asunción de la Virgen",
        siguiente_lunes(date(anio, 10, 12)): "Día de la Raza",
        siguiente_lunes(date(anio, 11, 1)): "Todos los Santos",
        siguiente_lunes(date(anio, 11, 11)): "Independencia de Cartagena",
        date(anio, 12, 8): "Inmaculada Concepción",
        date(anio, 12, 25): "Navidad",
    }
    return festivos


def construir_programacion(anio, mes, fecha_inicio_ciclo, hora_inicio, hora_fin):
    """
    Construye la programación mensual 14x7 usando fecha real de inicio y festivos oficiales de Colombia.
    No usa librerías externas para evitar errores de despliegue en Streamlit Cloud.
    """
    festivos_colombia = festivos_colombia_interno(anio)
    dias_mes = calendar.monthrange(anio, mes)[1]
    horas_dia, _, _ = rango_horas(hora_inicio, hora_fin)
    noct_dia = horas_nocturnas_turno(hora_inicio, hora_fin)
    diur_dia = max(0, horas_dia - noct_dia)

    filas = []

    for d in range(1, dias_mes + 1):
        fecha = date(anio, mes, d)
        semana_mes = ((d - 1) // 7) + 1
        dias_desde_inicio = (fecha - fecha_inicio_ciclo).days
        dia_ciclo = (dias_desde_inicio % 21) + 1
        trabaja = dia_ciclo <= 14
        es_domingo = fecha.weekday() == 6
        es_festivo = fecha in festivos_colombia
        nombre_festivo = festivos_colombia.get(fecha, "")

        horas_totales = horas_dia if trabaja else 0
        horas_noct = noct_dia if trabaja else 0
        horas_diur = diur_dia if trabaja else 0

        if not trabaja:
            etiqueta = "DESCANSO"
        elif es_festivo:
            etiqueta = "FESTIVO"
        elif es_domingo:
            etiqueta = "DOMINICAL"
        elif horas_noct > 0:
            etiqueta = "LABORA / NOCT."
        else:
            etiqueta = "LABORA"

        filas.append({
            "Fecha": fecha,
            "Día": d,
            "Semana": semana_mes,
            "Día semana": DIAS_SEMANA[fecha.weekday()],
            "Día ciclo 14x7": dia_ciclo,
            "Estado": "LABORA" if trabaja else "DESCANSO",
            "Etiqueta": etiqueta,
            "Es domingo": es_domingo,
            "Es festivo Colombia": es_festivo,
            "Nombre festivo": nombre_festivo,
            "Dominical laborado": trabaja and es_domingo,
            "Festivo laborado": trabaja and es_festivo,
            "Festivo no laborado": (not trabaja) and es_festivo,
            "Horas totales": horas_totales,
            "Horas diurnas": horas_diur,
            "Horas nocturnas": horas_noct,
        })

    return pd.DataFrame(filas)


with st.sidebar:
    st.header("⚙️ Parámetros")

    anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026)
    mes_nombre = st.selectbox("Mes", list(MESES.keys()), index=5)
    mes = MESES[mes_nombre]
    cantidad_conductores = st.number_input("Cantidad de conductores", min_value=1, max_value=500, value=1)

    st.divider()
    st.subheader("📅 Programación 14x7")
    fecha_inicio_ciclo = st.date_input(
        "Fecha real de inicio del ciclo 14x7",
        value=date(2026, 6, 8),
        help="Desde esta fecha se cuenta: 14 días laborados y 7 días de descanso."
    )
    hora_inicio = st.time_input("Hora inicio", value=time(3, 0), step=1800)
    hora_fin = st.time_input("Hora finalización", value=time(16, 0), step=1800)
    horas_ley_semana = st.number_input("Referencia legal semanal", min_value=1.0, max_value=60.0, value=45.0, step=1.0)
    horas_base_dia_operacional = st.number_input("Horas base operacionales por día laborado", min_value=1.0, max_value=12.0, value=8.0, step=0.5)
    max_disponibles = st.number_input("Máximo recomendado horas disponibles", min_value=1.0, max_value=24.0, value=12.0, step=0.5)
    limite_fatiga = st.number_input("Límite máximo fatiga", min_value=1.0, max_value=24.0, value=15.0, step=0.5)
    st.divider()
    st.subheader("💰 Conductor")
    smlv = st.number_input("SMLV / salario base", min_value=0, value=1750905, step=10000)
    bono_disp = st.number_input("Bono disponibilidad", min_value=0, value=214000, step=10000)
    bono_res = st.number_input("Bono resultados", min_value=0, value=240492, step=10000)
    bono_com = st.number_input("Bono comunicación / auxilio no prestacional", min_value=0, value=30000, step=5000)

    st.markdown("**🎯 Productividad**")
    produccion = st.number_input("Producción vehículo", min_value=0, value=16000000, step=100000)
    modo_comision = st.radio("Escenario de comisión", ["Meta mínima simple", "Escala por rangos"], horizontal=False)

    if modo_comision == "Meta mínima simple":
        meta_produccion = st.number_input("Meta mínima productividad", min_value=0, value=16000000, step=100000)
        pct_comision_input = st.number_input("% comisión productividad", min_value=0.0, max_value=100.0, value=2.2, step=0.01)
        pct_comision = pct_comision_input / 100
        comision_preview, escenario_activo, estado_comision = calcular_comision_simple(produccion, meta_produccion, pct_comision)

        r1_min = r1_max = r2_min = r2_max = r3_min = 0
        r1_factor = r2_factor = r3_factor = 0
    else:
        pct_comision_input = st.number_input("% base comisión productividad", min_value=0.0, max_value=100.0, value=2.2, step=0.01)
        pct_comision = pct_comision_input / 100

        st.caption("Rangos editables")
        r1_min = st.number_input("Rango 1 mínimo", min_value=0, value=12000000, step=100000)
        r1_max = st.number_input("Rango 1 máximo", min_value=0, value=12999000, step=100000)
        r1_factor = st.number_input("Rango 1 factor %", min_value=0.0, max_value=100.0, value=60.0, step=1.0) / 100

        r2_min = st.number_input("Rango 2 mínimo", min_value=0, value=13000000, step=100000)
        r2_max = st.number_input("Rango 2 máximo", min_value=0, value=14999000, step=100000)
        r2_factor = st.number_input("Rango 2 factor %", min_value=0.0, max_value=100.0, value=80.0, step=1.0) / 100

        r3_min = st.number_input("Rango 3 mínimo", min_value=0, value=15000000, step=100000)
        r3_factor = st.number_input("Rango 3 factor %", min_value=0.0, max_value=100.0, value=100.0, step=1.0) / 100

        meta_produccion = r3_min
        comision_preview, escenario_activo, estado_comision = calcular_comision_escalonada(
            produccion, pct_comision, r1_min, r1_max, r1_factor, r2_min, r2_max, r2_factor, r3_min, r3_factor
        )

    st.divider()
    st.subheader("📌 Recargos")
    rec_nocturno = st.number_input("Recargo nocturno %", 0.0, 200.0, 35.0, step=1.0) / 100
    rec_extra_diurna = st.number_input("Extra diurna %", 0.0, 200.0, 25.0, step=1.0) / 100
    rec_extra_nocturna = st.number_input("Extra nocturna %", 0.0, 200.0, 75.0, step=1.0) / 100
    rec_dominical = st.number_input("Dominical %", 0.0, 200.0, tarifa_dom(anio) * 100, step=1.0) / 100
    rec_festivo = st.number_input("Festivo %", 0.0, 200.0, tarifa_dom(anio) * 100, step=1.0) / 100

    st.divider()
    st.subheader("🧾 Prestaciones y aportes empresa")
    prima_pct = st.number_input("Prima %", 0.0, 20.0, 8.33, step=0.01) / 100
    ces_pct = st.number_input("Cesantías %", 0.0, 20.0, 8.33, step=0.01) / 100
    int_ces_pct = st.number_input("Interés cesantías %", 0.0, 10.0, 1.0, step=0.01) / 100
    vac_pct = st.number_input("Vacaciones %", 0.0, 20.0, 4.17, step=0.01) / 100
    pension_emp_pct = st.number_input("Pensión empresa %", 0.0, 30.0, 12.0, step=0.01) / 100
    ccp_pct = st.number_input("CCP / Caja %", 0.0, 20.0, 4.0, step=0.01) / 100
    arl_pct = st.number_input("ARL %", 0.0, 20.0, 6.96, step=0.01) / 100
    salud_emp_pct = st.number_input("Salud empresa %", 0.0, 20.0, 8.5, step=0.01) / 100
    sena_pct = st.number_input("SENA %", 0.0, 10.0, 0.0, step=0.01) / 100
    icbf_pct = st.number_input("ICBF %", 0.0, 10.0, 0.0, step=0.01) / 100

    st.divider()
    st.subheader("💳 Descuentos conductor")
    salud_trab_pct = st.number_input("Salud empleado %", 0.0, 20.0, 4.0, step=0.1) / 100
    pension_trab_pct = st.number_input("Pensión empleado %", 0.0, 20.0, 4.0, step=0.1) / 100
    otros_descuentos = st.number_input("Otros descuentos", min_value=0, value=0, step=10000)

    st.divider()
    st.subheader("🚐 Gastos vehículo")
    soat = st.number_input("SOAT mensualizado", min_value=0, value=0, step=10000)
    tecnomecanica = st.number_input("Técnico-mecánica mensualizada", min_value=0, value=0, step=10000)
    polizas = st.number_input("Pólizas / seguros operación", min_value=0, value=0, step=10000)
    gps = st.number_input("GPS / plataforma monitoreo", min_value=0, value=0, step=10000)
    administracion = st.number_input("Administración / documentación", min_value=0, value=0, step=10000)
    lavado = st.number_input("Lavado general vehículo", min_value=0, value=0, step=10000)
    peaje = st.number_input("Peaje con chip", min_value=0, value=0, step=10000)
    combustible = st.number_input("Combustible", min_value=0, value=0, step=10000)
    parqueadero = st.number_input("Parqueadero", min_value=0, value=0, step=10000)
    mantenimiento = st.number_input("Mantenimiento", min_value=0, value=0, step=10000)

    st.divider()
    st.subheader("👤 Gastos conductor")
    dotacion = st.number_input("Dotación", min_value=0, value=0, step=10000)
    alimentacion = st.number_input("Alimentación", min_value=0, value=0, step=10000)
    estadia = st.number_input("Estadía", min_value=0, value=0, step=10000)


df = construir_programacion(anio, mes, fecha_inicio_ciclo, hora_inicio, hora_fin)

horas_dia, _, _ = rango_horas(hora_inicio, hora_fin)
total_horas = df["Horas totales"].sum()
horas_nocturnas = df["Horas nocturnas"].sum()
horas_diurnas = df["Horas diurnas"].sum()

dias_laborados = int((df["Estado"] == "LABORA").sum())
dias_descanso = int((df["Estado"] == "DESCANSO").sum())
domingos_laborados = int(df["Dominical laborado"].sum())
domingos_no_laborados = int(((df["Es domingo"] == True) & (df["Estado"] == "DESCANSO")).sum())
festivos_laborados = int(df["Festivo laborado"].sum())
festivos_no_laborados = int(df["Festivo no laborado"].sum())

horas_base_operacional = dias_laborados * horas_base_dia_operacional
horas_extras_operacionales = max(0, total_horas - horas_base_operacional)
horas_extras_nocturnas = min(horas_nocturnas, horas_extras_operacionales)
horas_extras_diurnas = max(0, horas_extras_operacionales - horas_extras_nocturnas)

weekly_rows = []
for semana, gp in df.groupby("Semana"):
    ht = gp["Horas totales"].sum()
    hn = gp["Horas nocturnas"].sum()
    hd = gp["Horas diurnas"].sum()
    exceso_semana = max(0, ht - horas_ley_semana)
    faltante_semana = max(0, horas_ley_semana - ht)
    weekly_rows.append({
        "Semana": f"Semana {semana}",
        "Días laborados": int((gp["Estado"] == "LABORA").sum()),
        "Días descanso": int((gp["Estado"] == "DESCANSO").sum()),
        "Horas totales": ht,
        "Referencia legal semanal": horas_ley_semana,
        "Exceso legal semanal": exceso_semana,
        "Faltante semanal": faltante_semana,
        "Horas diurnas": hd,
        "Horas nocturnas": hn,
        "Domingos laborados": int(gp["Dominical laborado"].sum()),
        "Festivos laborados": int(gp["Festivo laborado"].sum())
    })
weekly_df = pd.DataFrame(weekly_rows)

base_fija_salarial = smlv + bono_disp + bono_res
valor_hora = base_fija_salarial / 220 if base_fija_salarial else 0

valor_nocturno = horas_nocturnas * valor_hora * rec_nocturno
valor_extra_diurna = horas_extras_diurnas * valor_hora * (1 + rec_extra_diurna)
valor_extra_nocturna = horas_extras_nocturnas * valor_hora * (1 + rec_extra_nocturna)
valor_dominical = domingos_laborados * horas_dia * valor_hora * rec_dominical
valor_festivo = festivos_laborados * horas_dia * valor_hora * rec_festivo

total_recargos = valor_nocturno + valor_extra_diurna + valor_extra_nocturna + valor_dominical + valor_festivo
comision = comision_preview

base_prestacional_ibc = base_fija_salarial + total_recargos + comision
no_prestacional = bono_com
devengado = base_fija_salarial + total_recargos + comision

prima = base_prestacional_ibc * prima_pct
ces = base_prestacional_ibc * ces_pct
int_ces = base_prestacional_ibc * int_ces_pct
vac = base_prestacional_ibc * vac_pct
total_prestaciones = prima + ces + int_ces + vac

pension_emp = base_prestacional_ibc * pension_emp_pct
ccp = base_prestacional_ibc * ccp_pct
arl = base_prestacional_ibc * arl_pct
salud_emp = base_prestacional_ibc * salud_emp_pct
sena = base_prestacional_ibc * sena_pct
icbf = base_prestacional_ibc * icbf_pct
total_aportes = pension_emp + ccp + arl + salud_emp + sena + icbf

desc_salud = base_prestacional_ibc * salud_trab_pct
desc_pension = base_prestacional_ibc * pension_trab_pct
total_descuentos = desc_salud + desc_pension + otros_descuentos
neto_conductor = devengado - total_descuentos

gasto_vehiculo = soat + tecnomecanica + polizas + gps + administracion + lavado + peaje + combustible + parqueadero + mantenimiento
gasto_conductor = dotacion + alimentacion + estadia + bono_com
costo_conductor_empresa = devengado + total_prestaciones + total_aportes
costo_total_empresa_mensual = costo_conductor_empresa + gasto_vehiculo + gasto_conductor
costo_mensual_flota = costo_total_empresa_mensual * cantidad_conductores

st.subheader("1️⃣ Totales mensuales principales")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total a pagar al conductor", cop(neto_conductor))
c2.metric("Gasto conductor", cop(gasto_conductor))
c3.metric("Gasto vehículo", cop(gasto_vehiculo))
c4.metric("Costo total empresa mensual", cop(costo_total_empresa_mensual))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Costo mensual flota", cop(costo_mensual_flota))
c6.metric("Base prestacional / IBC", cop(base_prestacional_ibc))
c7.metric("Total recargos", cop(total_recargos))
c8.metric("Comisión productividad", cop(comision))

st.info(f"Escenario de comisión aplicado: {modo_comision}. Resultado: {escenario_activo}. Comisión: {cop(comision)}")

st.subheader("2️⃣ Panel operacional mensual")
o1, o2, o3, o4 = st.columns(4)
o1.metric("Días laborados", dias_laborados)
o2.metric("Días descanso", dias_descanso)
o3.metric("Domingos laborados / no", f"{domingos_laborados} / {domingos_no_laborados}")
o4.metric("Festivos laborados / no", f"{festivos_laborados} / {festivos_no_laborados}")

o5, o6, o7, o8 = st.columns(4)
o5.metric("Horas totales", hrs(total_horas))
o6.metric("Horas base operacionales", hrs(horas_base_operacional))
o7.metric("Extras operacionales", hrs(horas_extras_operacionales))
o8.metric("Horas día", hrs(horas_dia))

o9, o10, o11, o12 = st.columns(4)
o9.metric("Horas diurnas", hrs(horas_diurnas))
o10.metric("Horas nocturnas", hrs(horas_nocturnas))
o11.metric("Extras diurnas", hrs(horas_extras_diurnas))
o12.metric("Extras nocturnas", hrs(horas_extras_nocturnas))

if horas_dia > limite_fatiga:
    st.error(f"🚨 Fatiga crítica: {hrs(horas_dia)} por día supera el límite de {hrs(limite_fatiga)}.")
elif horas_dia > max_disponibles:
    st.warning(f"⚠️ Jornada superior a {hrs(max_disponibles)} disponibles. Validar horas adicionales.")
else:
    st.success("✅ Jornada dentro de parámetros operativos configurados.")

st.divider()
st.subheader("3️⃣ Horas del mes")
horas_df = pd.DataFrame({
    "Tipo": [
        "Horas totales", "Horas base operacionales", "Extras operacionales",
        "Horas diurnas", "Horas nocturnas", "Extras diurnas", "Extras nocturnas"
    ],
    "Horas": [
        total_horas, horas_base_operacional, horas_extras_operacionales,
        horas_diurnas, horas_nocturnas, horas_extras_diurnas, horas_extras_nocturnas
    ]
})
st.dataframe(horas_df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("4️⃣ ¿Cuánto se le paga al conductor?")
conductor_df = pd.DataFrame({
    "Concepto": [
        "SMLV / salario base", "Bono disponibilidad", "Bono resultados",
        "Recargo nocturno", "Extras diurnas", "Extras nocturnas", "Dominicales", "Festivos",
        "Comisión productividad", "Descuento salud empleado", "Descuento pensión empleado", "Otros descuentos",
        "NETO A PAGAR A CUENTA BANCARIA"
    ],
    "% aplicado": [
        "", "", "", pct(rec_nocturno), pct(rec_extra_diurna), pct(rec_extra_nocturna),
        pct(rec_dominical), pct(rec_festivo), f"{pct_comision_input:.2f}%".replace(".", ","),
        pct(salud_trab_pct), pct(pension_trab_pct), "", ""
    ],
    "Soporte": [
        "", "", "", hrs(horas_nocturnas), hrs(horas_extras_diurnas), hrs(horas_extras_nocturnas),
        f"{domingos_laborados} domingos", f"{festivos_laborados} festivos",
        escenario_activo, cop(base_prestacional_ibc), cop(base_prestacional_ibc), "", ""
    ],
    "Valor": [
        smlv, bono_disp, bono_res, valor_nocturno, valor_extra_diurna, valor_extra_nocturna,
        valor_dominical, valor_festivo, comision, -desc_salud, -desc_pension, -otros_descuentos, neto_conductor
    ]
})
conductor_show = conductor_df.copy()
conductor_show["Valor"] = conductor_show["Valor"].map(cop)
st.dataframe(conductor_show, use_container_width=True, hide_index=True)

st.divider()
st.subheader("5️⃣ ¿Cuánto paga la empresa por el conductor?")

# Esta sección consolida TODO lo que la empresa debe asumir:
# 1. Nómina del conductor
# 2. Prestaciones
# 3. Aportes empresa
# 4. Gastos conductor
# 5. Gastos vehículo
# 6. Total empresa mensual

costo_conductor_empresa = devengado + total_prestaciones + total_aportes
costo_total_empresa_mensual = costo_conductor_empresa + gasto_conductor + gasto_vehiculo
costo_mensual_flota = costo_total_empresa_mensual * cantidad_conductores

empresa_total_df = pd.DataFrame({
    "Bloque": [
        "NÓMINA CONDUCTOR", "NÓMINA CONDUCTOR",
        "PRESTACIONES", "PRESTACIONES", "PRESTACIONES", "PRESTACIONES",
        "APORTES EMPRESA", "APORTES EMPRESA", "APORTES EMPRESA", "APORTES EMPRESA", "APORTES EMPRESA", "APORTES EMPRESA",
        "GASTOS CONDUCTOR", "GASTOS CONDUCTOR", "GASTOS CONDUCTOR", "GASTOS CONDUCTOR",
        "GASTOS VEHÍCULO", "GASTOS VEHÍCULO", "GASTOS VEHÍCULO", "GASTOS VEHÍCULO", "GASTOS VEHÍCULO",
        "GASTOS VEHÍCULO", "GASTOS VEHÍCULO", "GASTOS VEHÍCULO", "GASTOS VEHÍCULO", "GASTOS VEHÍCULO",
        "TOTAL GENERAL"
    ],
    "Concepto": [
        "Devengado conductor", "Base prestacional / IBC",
        "Prima", "Cesantías", "Interés cesantías", "Vacaciones",
        "Pensión empresa", "Caja compensación / CCP", "ARL", "Salud empresa", "SENA", "ICBF",
        "Dotación", "Alimentación", "Estadía", "Bono de comunicación",
        "SOAT", "Técnico-mecánica", "Pólizas / seguros operación", "GPS / plataforma monitoreo", "Administración / documentación",
        "Lavado general vehículo", "Peaje con chip", "Combustible", "Parqueadero", "Mantenimiento",
        "COSTO TOTAL EMPRESA MENSUAL"
    ],
    "% aplicado": [
        "", "",
        pct(prima_pct), pct(ces_pct), pct(int_ces_pct), pct(vac_pct),
        pct(pension_emp_pct), pct(ccp_pct), pct(arl_pct), pct(salud_emp_pct), pct(sena_pct), pct(icbf_pct),
        "", "", "", "",
        "", "", "", "", "", "", "", "", "", "", ""
    ],
    "Base / soporte": [
        "", cop(base_prestacional_ibc),
        cop(base_prestacional_ibc), cop(base_prestacional_ibc), cop(base_prestacional_ibc), cop(base_prestacional_ibc),
        cop(base_prestacional_ibc), cop(base_prestacional_ibc), cop(base_prestacional_ibc), cop(base_prestacional_ibc), cop(base_prestacional_ibc), cop(base_prestacional_ibc),
        "Lo paga empresa", "Lo paga empresa", "Lo paga empresa", "No prestacional / auxilio comunicación",
        "Lo paga empresa", "Lo paga empresa", "Lo paga empresa", "Lo paga empresa", "Lo paga empresa",
        "Lo paga empresa", "Lo paga empresa", "Lo paga empresa", "Lo paga empresa", "Lo paga empresa",
        ""
    ],
    "Valor": [
        devengado, base_prestacional_ibc,
        prima, ces, int_ces, vac,
        pension_emp, ccp, arl, salud_emp, sena, icbf,
        dotacion, alimentacion, estadia, bono_com,
        soat, tecnomecanica, polizas, gps, administracion,
        lavado, peaje, combustible, parqueadero, mantenimiento,
        costo_total_empresa_mensual
    ]
})

empresa_total_show = empresa_total_df.copy()
empresa_total_show["Valor"] = empresa_total_show["Valor"].map(cop)
st.dataframe(empresa_total_show, use_container_width=True, hide_index=True)

resumen_empresa_df = pd.DataFrame({
    "Resumen": [
        "Subtotal nómina conductor sin gastos",
        "Subtotal gastos conductor",
        "Subtotal gastos vehículo",
        "TOTAL EMPRESA MENSUAL"
    ],
    "Valor": [
        costo_conductor_empresa,
        gasto_conductor,
        gasto_vehiculo,
        costo_total_empresa_mensual
    ]
})
resumen_empresa_show = resumen_empresa_df.copy()
resumen_empresa_show["Valor"] = resumen_empresa_show["Valor"].map(cop)
st.dataframe(resumen_empresa_show, use_container_width=True, hide_index=True)

st.divider()
st.subheader("6️⃣ Escenarios de comisión por productividad")

if modo_comision == "Meta mínima simple":
    escenarios_df = pd.DataFrame([{
        "Escenario": "Meta mínima simple",
        "Producción requerida": f"Desde {cop(meta_produccion)}",
        "Factor aplicado": "100%",
        "Comisión posible": cop(produccion * pct_comision),
        "Estado": "✅ ACTIVO" if estado_comision == "ACTIVO" else "❌ No aplica"
    }])
else:
    escenarios_df = pd.DataFrame([
        {
            "Escenario": "Rango 1",
            "Producción requerida": f"{cop(r1_min)} → {cop(r1_max)}",
            "Factor aplicado": pct(r1_factor),
            "Comisión posible": cop(produccion * pct_comision * r1_factor),
            "Estado": "✅ ACTIVO" if escenario_activo == "Rango 1" else "❌ No aplica"
        },
        {
            "Escenario": "Rango 2",
            "Producción requerida": f"{cop(r2_min)} → {cop(r2_max)}",
            "Factor aplicado": pct(r2_factor),
            "Comisión posible": cop(produccion * pct_comision * r2_factor),
            "Estado": "✅ ACTIVO" if escenario_activo == "Rango 2" else "❌ No aplica"
        },
        {
            "Escenario": "Rango 3",
            "Producción requerida": f"Desde {cop(r3_min)}",
            "Factor aplicado": pct(r3_factor),
            "Comisión posible": cop(produccion * pct_comision * r3_factor),
            "Estado": "✅ ACTIVO" if escenario_activo == "Rango 3" else "❌ No aplica"
        }
    ])

st.dataframe(escenarios_df, use_container_width=True, hide_index=True)

if estado_comision == "ACTIVO":
    st.success(f"🎯 Escenario activo: {escenario_activo} | Producción: {cop(produccion)} | Comisión aplicada: {cop(comision)}")
else:
    st.warning(f"⚠️ No alcanzó productividad mínima o rango válido. Producción: {cop(produccion)} | Comisión aplicada: {cop(comision)}")

p1, p2, p3 = st.columns(3)
p1.metric("Producción alcanzada", cop(produccion))
p2.metric("Comisión aplicada", cop(comision))
p3.metric("Escenario activo", escenario_activo)

st.divider()
st.subheader("7️⃣ Panel legal semanal - alerta")
legal_total = weekly_df.copy()
totales = {}
for col in legal_total.columns:
    if col == "Semana":
        totales[col] = "TOTAL"
    elif pd.api.types.is_numeric_dtype(legal_total[col]):
        totales[col] = legal_total[col].sum()
    else:
        totales[col] = ""
legal_total = pd.concat([legal_total, pd.DataFrame([totales])], ignore_index=True)
st.dataframe(legal_total, use_container_width=True, hide_index=True)

l1, l2, l3 = st.columns(3)
l1.metric("Exceso legal semanal acumulado", hrs(weekly_df["Exceso legal semanal"].sum()))
l2.metric("Faltante semanal acumulado", hrs(weekly_df["Faltante semanal"].sum()))
l3.metric("Referencia semanal", hrs(horas_ley_semana))

st.divider()
st.subheader("8️⃣ Programación visual 14x7")
html = "<table style='width:100%; border-collapse:separate; border-spacing:6px;'>"
for semana in sorted(df["Semana"].unique()):
    html += "<tr>"
    for _, r in df[df["Semana"] == semana].iterrows():
        if r["Estado"] == "DESCANSO":
            bg = "#D9D9D9"
        elif r["Festivo laborado"]:
            bg = "#CFE2F3"
        elif r["Dominical laborado"]:
            bg = "#F4CCCC"
        elif r["Horas nocturnas"] > 0:
            bg = "#D9D2E9"
        else:
            bg = "#D9EAD3"

        festivo_txt = f"<div style='font-size:10px'>🎌 {r['Nombre festivo']}</div>" if r.get("Es festivo Colombia", False) else ""
        cell = f"""
        <div style='font-weight:700;font-size:15px'>{int(r['Día'])}</div>
        <div>{r['Día semana']}</div>
        <div style='font-size:12px'>{r['Estado']}</div>
        {festivo_txt}
        <div style='font-size:11px'>D {round(r['Horas diurnas'])}h / N {round(r['Horas nocturnas'])}h</div>
        """
        html += f"<td style='background:{bg}; padding:9px; border-radius:10px; text-align:center; border:1px solid #E2E8F0;'>{cell}</td>"
    html += "</tr>"
html += "</table>"
st.markdown(html, unsafe_allow_html=True)
st.caption("Verde: labora | Gris: descanso | Morado: nocturno | Rojo: dominical | Azul: festivo real Colombia")

st.divider()
st.subheader("9️⃣ Detalle diario descargable")
detalle = df.copy()
detalle["Horas totales"] = detalle["Horas totales"].round(1)
detalle["Horas diurnas"] = detalle["Horas diurnas"].round(1)
detalle["Horas nocturnas"] = detalle["Horas nocturnas"].round(1)
st.dataframe(detalle, use_container_width=True, hide_index=True)

st.download_button(
    "⬇️ Descargar detalle diario CSV",
    data=detalle.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"detalle_diario_{mes_nombre}_{anio}.csv",
    mime="text/csv"
)
