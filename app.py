
import calendar
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='Simulador costo conductor 14x7', page_icon='🚐', layout='wide')

st.markdown('''
<style>
.block-container {padding-top: 1.5rem;}
</style>
''', unsafe_allow_html=True)

st.title('🚐 Simulador gerencial costo conductor 14x7')
st.caption('Proyección simple: costo fijo + extras + nocturnas + dominicales + bono variable por facturación.')

MONTHS = {
    'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4, 'Mayo': 5, 'Junio': 6,
    'Julio': 7, 'Agosto': 8, 'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12
}

def cop(value):
    return f'${value:,.0f}'.replace(',', '.')

def default_dominical_rate(year):
    if year >= 2027:
        return 100
    if year == 2026:
        return 90
    return 80

def build_calendar(year, month, start_cycle_day, hours_day, ordinary_day, pct_night):
    days_in_month = calendar.monthrange(year, month)[1]
    records = []
    cycle_day = start_cycle_day

    for d in range(1, days_in_month + 1):
        current = date(year, month, d)
        day_cycle = ((cycle_day - 1) % 21) + 1
        works = day_cycle <= 14
        is_sunday = current.weekday() == 6

        worked_hours = hours_day if works else 0
        ordinary_hours = min(ordinary_day, worked_hours)
        extra_hours = max(0, worked_hours - ordinary_hours)

        night_hours = worked_hours * pct_night
        extra_night_hours = extra_hours * pct_night
        extra_day_hours = extra_hours - extra_night_hours

        if not works:
            label = 'DESCANSO'
            color_type = 'DESCANSO'
        elif is_sunday:
            label = 'DOMINICAL'
            color_type = 'DOMINICAL'
        elif night_hours > 0:
            label = 'LABORA / NOCT.'
            color_type = 'NOCTURNO'
        else:
            label = 'LABORA'
            color_type = 'LABORA'

        records.append({
            'Fecha': current,
            'Dia': d,
            'Semana_mes': ((d - 1) // 7) + 1,
            'Dia_semana': ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'][current.weekday()],
            'Dia_ciclo_14x7': day_cycle,
            'Estado': 'LABORA' if works else 'DESCANSO',
            'Etiqueta': label,
            'Tipo_color': color_type,
            'Es_domingo': is_sunday,
            'Horas': worked_hours,
            'Horas_ordinarias_base': ordinary_hours,
            'Horas_extra_base': extra_hours,
            'Horas_nocturnas_estimadas': night_hours,
            'Horas_extra_diurnas': extra_day_hours,
            'Horas_extra_nocturnas': extra_night_hours
        })
        cycle_day += 1

    return pd.DataFrame(records)

with st.sidebar:
    st.header('⚙️ Parámetros')

    year = st.number_input('Año', min_value=2025, max_value=2035, value=2026, step=1)
    month_name = st.selectbox('Mes', list(MONTHS.keys()), index=4)
    month = MONTHS[month_name]
    drivers = st.number_input('Cantidad de conductores', min_value=1, max_value=500, value=1, step=1)

    city = st.selectbox('Ciudad', ['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Ibagué', 'Villavicencio', 'Otra'])
    operation = st.selectbox('Tipo de operación', ['Transporte especial', 'Transporte empresarial', 'Transporte escolar', 'Operación nocturna', 'Operación mixta', 'Otra'])
    start_cycle_day = st.slider('Día del ciclo 14x7 al iniciar el mes', 1, 21, 1)

    st.divider()
    st.subheader('💰 Fijos por conductor')
    salary = st.number_input('Salario base mensual / SMLV', min_value=0, value=1750905, step=10000)
    transport_allowance = st.number_input('Auxilio de transporte', min_value=0, value=0, step=1000)
    bono_disponibilidad = st.number_input('Bono disponibilidad', min_value=0, value=214000, step=10000)
    bono_resultados = st.number_input('Bono resultados', min_value=0, value=240492, step=10000)
    bono_comunicacion = st.number_input('Bono comunicación', min_value=0, value=30000, step=5000)

    st.divider()
    st.subheader('🎯 Bono variable por facturación')
    valor_facturado = st.number_input('Valor facturado apoyado por conductor', min_value=0, value=5000000, step=100000)
    porcentaje_bono = st.slider('% bonificación sobre facturación', min_value=0.0, max_value=10.0, value=2.0, step=0.5) / 100
    bono_facturacion = valor_facturado * porcentaje_bono

    st.divider()
    st.subheader('⏱️ Jornada')
    weekly_limit = st.number_input('Jornada máxima semanal', min_value=1, max_value=60, value=44, step=1)
    hours_day = st.number_input('Horas disponibles por día laborado', min_value=1.0, max_value=24.0, value=12.0, step=0.5)
    ordinary_day = st.number_input('Horas ordinarias base día', min_value=1.0, max_value=12.0, value=8.0, step=0.5)
    pct_night = st.slider('% estimado de horas nocturnas dentro del turno', 0, 100, 30, 5) / 100

    st.divider()
    st.subheader('📌 Recargos')
    night_rate = st.number_input('Recargo nocturno %', min_value=0, max_value=200, value=35, step=1) / 100
    extra_day_rate = st.number_input('Extra diurna %', min_value=0, max_value=200, value=25, step=1) / 100
    extra_night_rate = st.number_input('Extra nocturna %', min_value=0, max_value=200, value=75, step=1) / 100
    sunday_rate = st.number_input('Dominical/festivo %', min_value=0, max_value=200, value=default_dominical_rate(year), step=1) / 100

    st.divider()
    st.subheader('🧾 Carga empresa')
    provision_pct = st.slider('Prestaciones + seguridad social + parafiscales estimado %', 0, 80, 45, 1) / 100
    bonos_salariales = st.toggle('Incluir bonos dentro de base prestacional', value=False)

df = build_calendar(year, month, start_cycle_day, hours_day, ordinary_day, pct_night)

hour_value = salary / 220 if salary else 0

fixed_bonuses = bono_disponibilidad + bono_resultados + bono_comunicacion
total_bonus = fixed_bonuses + bono_facturacion

total_hours = df['Horas'].sum()
work_days = int((df['Estado'] == 'LABORA').sum())
rest_days = int((df['Estado'] == 'DESCANSO').sum())
sundays_worked = int(((df['Estado'] == 'LABORA') & (df['Es_domingo'])).sum())
sunday_hours = df.loc[(df['Estado'] == 'LABORA') & (df['Es_domingo']), 'Horas'].sum()

night_hours = df['Horas_nocturnas_estimadas'].sum()
extra_day_hours = df['Horas_extra_diurnas'].sum()
extra_night_hours = df['Horas_extra_nocturnas'].sum()

night_cost = night_hours * hour_value * night_rate
extra_day_cost = extra_day_hours * hour_value * (1 + extra_day_rate)
extra_night_cost = extra_night_hours * hour_value * (1 + extra_night_rate)
sunday_cost = sunday_hours * hour_value * sunday_rate

variable_labor_cost = night_cost + extra_day_cost + extra_night_cost + sunday_cost

fixed_month_cost = salary + transport_allowance + fixed_bonuses
subtotal_without_provisions = fixed_month_cost + bono_facturacion + variable_labor_cost

base_for_provisions = salary + variable_labor_cost + (total_bonus if bonos_salariales else 0)
provisions = base_for_provisions * provision_pct

monthly_cost_one = subtotal_without_provisions + provisions
monthly_cost_total = monthly_cost_one * drivers
annual_cost_total = monthly_cost_total * 12

st.subheader('📌 Resultado principal')

k1, k2, k3, k4 = st.columns(4)
k1.metric('Costo mensual total', cop(monthly_cost_total))
k2.metric('Costo mensual por conductor', cop(monthly_cost_one))
k3.metric('Costo anual proyectado', cop(annual_cost_total))
k4.metric('Costo fijo por conductor', cop(fixed_month_cost))

k5, k6, k7, k8 = st.columns(4)
k5.metric('Horas mes por conductor', f'{total_hours:,.1f}'.replace(',', '.'))
k6.metric('Días laborados', work_days)
k7.metric('Días descanso', rest_days)
k8.metric('Dominicales trabajados', sundays_worked)

st.divider()

st.subheader('🧮 Bolsa mensual por conductor')
bolsa = pd.DataFrame({
    'Concepto': [
        'Salario base / SMLV',
        'Auxilio transporte',
        'Bono disponibilidad',
        'Bono resultados',
        'Bono comunicación',
        'Bono variable por facturación',
        'Extras diurnas',
        'Extras nocturnas',
        'Recargo nocturno',
        'Dominicales / festivos',
        'Carga empresa estimada',
        'TOTAL POR CONDUCTOR'
    ],
    'Valor': [
        salary,
        transport_allowance,
        bono_disponibilidad,
        bono_resultados,
        bono_comunicacion,
        bono_facturacion,
        extra_day_cost,
        extra_night_cost,
        night_cost,
        sunday_cost,
        provisions,
        monthly_cost_one
    ]
})
bolsa_show = bolsa.copy()
bolsa_show['Valor'] = bolsa_show['Valor'].map(cop)

c_left, c_right = st.columns([1, 1])

with c_left:
    st.dataframe(bolsa_show, use_container_width=True, hide_index=True)

with c_right:
    fig_bolsa = px.bar(
        bolsa[bolsa['Concepto'] != 'TOTAL POR CONDUCTOR'],
        x='Concepto',
        y='Valor',
        text='Valor',
        title='Composición del costo mensual'
    )
    fig_bolsa.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig_bolsa.update_layout(xaxis_title='', yaxis_title='COP', height=420)
    st.plotly_chart(fig_bolsa, use_container_width=True)

st.divider()

st.subheader(f'📅 Calendario operacional - {month_name} {year}')

html = """<table style='width:100%; border-collapse:separate; border-spacing:7px;'>"""
for week in sorted(df['Semana_mes'].unique()):
    week_data = df[df['Semana_mes'] == week]
    html += '<tr>'
    for _, r in week_data.iterrows():
        if r['Tipo_color'] == 'DESCANSO':
            bg = '#D9D9D9'
        elif r['Tipo_color'] == 'DOMINICAL':
            bg = '#F4CCCC'
        elif r['Tipo_color'] == 'NOCTURNO':
            bg = '#D9D2E9'
        else:
            bg = '#D9EAD3'

        cell = f"""
        <div style='font-weight:700;font-size:16px'>{int(r['Dia'])}</div>
        <div>{r['Dia_semana']}</div>
        <div style='font-size:12px'>{r['Etiqueta']}</div>
        <div style='font-size:12px'>{r['Horas']} h</div>
        """
        html += f"<td style='background:{bg}; padding:10px; border-radius:12px; text-align:center; border:1px solid #ECECEC;'>{cell}</td>"
    html += '</tr>'
html += '</table>'
st.markdown(html, unsafe_allow_html=True)
st.caption('Verde: labora | Gris: descanso | Morado: turno con nocturnidad | Rojo: dominical laborado')

st.divider()

weekly_cost = []
for week, group in df.groupby('Semana_mes'):
    wh = group['Horas'].sum()
    proportion = wh / total_hours if total_hours else 0
    weekly_cost.append({
        'Semana': f'Semana {week}',
        'Horas': wh,
        'Días laborados': int((group['Estado'] == 'LABORA').sum()),
        'Días descanso': int((group['Estado'] == 'DESCANSO').sum()),
        'Dominicales': int(((group['Estado'] == 'LABORA') & (group['Es_domingo'])).sum()),
        'Costo estimado por conductor': monthly_cost_one * proportion,
        'Costo total conductores': monthly_cost_total * proportion
    })

weekly_df = pd.DataFrame(weekly_cost)

w1, w2 = st.columns([1, 1])

with w1:
    st.subheader('💸 Costo por semana')
    fig_week = px.bar(
        weekly_df,
        x='Semana',
        y='Costo total conductores',
        text='Costo total conductores',
        color='Semana'
    )
    fig_week.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig_week.update_layout(showlegend=False, yaxis_title='COP', xaxis_title='', height=420)
    st.plotly_chart(fig_week, use_container_width=True)

with w2:
    st.subheader('📋 Resumen semanal')
    weekly_show = weekly_df.copy()
    weekly_show['Costo estimado por conductor'] = weekly_show['Costo estimado por conductor'].map(cop)
    weekly_show['Costo total conductores'] = weekly_show['Costo total conductores'].map(cop)
    st.dataframe(weekly_show, use_container_width=True, hide_index=True)

st.divider()

g1, g2 = st.columns([1, 1])

with g1:
    st.subheader('📊 Distribución costo variable')
    comp = pd.DataFrame({
        'Concepto': ['Extras diurnas', 'Extras nocturnas', 'Nocturnidad', 'Dominical/festivo', 'Bono facturación'],
        'Valor': [extra_day_cost, extra_night_cost, night_cost, sunday_cost, bono_facturacion]
    })
    fig_pie = px.pie(comp, names='Concepto', values='Valor', hole=0.45)
    st.plotly_chart(fig_pie, use_container_width=True)

with g2:
    st.subheader('📈 Indicadores de horas')
    hours_df = pd.DataFrame({
        'Tipo': ['Horas totales', 'Extras diurnas', 'Extras nocturnas', 'Nocturnas', 'Dominicales'],
        'Horas': [total_hours, extra_day_hours, extra_night_hours, night_hours, sunday_hours]
    })
    fig_hours = px.bar(hours_df, x='Tipo', y='Horas', text='Horas')
    fig_hours.update_traces(texttemplate='%{text:,.1f}', textposition='outside')
    fig_hours.update_layout(xaxis_title='', yaxis_title='Horas', height=420)
    st.plotly_chart(fig_hours, use_container_width=True)

st.divider()

st.subheader('📄 Detalle diario')
detail = df[[
    'Fecha',
    'Semana_mes',
    'Dia_semana',
    'Dia_ciclo_14x7',
    'Estado',
    'Etiqueta',
    'Es_domingo',
    'Horas',
    'Horas_ordinarias_base',
    'Horas_extra_diurnas',
    'Horas_extra_nocturnas',
    'Horas_nocturnas_estimadas'
]].copy()

st.dataframe(detail, use_container_width=True, hide_index=True)

csv = detail.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    '⬇️ Descargar detalle diario CSV',
    data=csv,
    file_name=f'detalle_simulador_14x7_{month_name}_{year}.csv',
    mime='text/csv'
)

st.warning(
    'Este simulador es una proyección gerencial. No reemplaza una liquidación oficial de nómina. '
    'Los bonos pueden ser salariales o no salariales según su naturaleza y deben validarse con el área laboral/contable.'
)
