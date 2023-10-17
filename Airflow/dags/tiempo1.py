from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime
import requests
import psycopg2
import json

# Configuración de la DAG
default_args = {
    'owner': 'Gustavo Lavalle',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 11),
    'retries': 1,
}

dag = DAG(
    'pronostico_tiempo_dag',
    default_args=default_args,
    schedule_interval='@daily',  # Define tu programación aquí
)

# Función para obtener el pronóstico del tiempo
def obtener_pronostico(ciudad):
    api_key = 'fb923a2632e685bef4acb90ad14e78dd'
    url = f'https://api.openweathermap.org/data/2.5/weather?q={ciudad}&appid={api_key}'
    response = requests.get(url)
    data = response.json()
    
    if 'main' in data:
        # Extrae la fecha y hora en formato crudo
        fecha_hora_cruda = data['dt']
        
        temperatura_actual = data['main']['temp']
        temperatura_maxima = data['main']['temp_max']
        temperatura_minima = data['main']['temp_min']
        presion = data['main']['pressure']
        humedad = data['main']['humidity']
        
        pronostico = {
            'fecha_hora': fecha_hora_cruda,  # Mantiene la fecha en formato crudo
            'temperatura_actual': temperatura_actual,
            'temperatura_maxima': temperatura_maxima,
            'temperatura_minima': temperatura_minima,
            'presion': presion,
            'humedad': humedad,
        }
        
        return ciudad, pronostico
    else:
        return ciudad, None

# Operadores para obtener el pronóstico del tiempo para tres ciudades
ciudades = ['Córdoba, AR', 'Mendoza, AR', 'Buenos Aires, AR']
obtener_pronostico_ops = []

for ciudad in ciudades:
    ciudad_key = ciudad.replace(' ', '_').replace(',', '')
    obtener_pronostico_op = PythonOperator(
        task_id=f'obtener_pronostico_{ciudad_key}',
        python_callable=obtener_pronostico,
        op_args=[ciudad],
        provide_context=True,
        dag=dag,
    )
    obtener_pronostico_ops.append(obtener_pronostico_op)


# Operador para crear la tabla RAW en la base de datos si no existe
crear_tabla_raw_sql = """
CREATE TABLE IF NOT EXISTS RAW (
    ciudad VARCHAR(50),
    fecha_hora VARCHAR(50), 
    pronostico_json JSONB
);
"""


crear_tabla_raw_op = PostgresOperator(
    task_id='crear_tabla_raw',
    sql=crear_tabla_raw_sql,
    postgres_conn_id='mi_conexion_postgres',  # Define un identificador de conexión personalizado
    autocommit=True,
    dag=dag,
)

# Operador para crear la tabla STAGING en la base de datos si no existe
crear_tabla_staging_sql = """
CREATE TABLE IF NOT EXISTS STAGING (
    ciudad VARCHAR(50),
    fecha_hora TIMESTAMP,  -- Cambia el tipo de datos a TIMESTAMP
    temperatura_actual FLOAT,
    temperatura_maxima FLOAT,
    temperatura_minima FLOAT,
    presion FLOAT,
    humedad FLOAT
);
"""

crear_tabla_staging_op = PostgresOperator(
    task_id='crear_tabla_staging',
    sql=crear_tabla_staging_sql,
    postgres_conn_id='mi_conexion_postgres',  # Define un identificador de conexión personalizado
    autocommit=True,
    dag=dag, 
)


# Función para insertar datos en la tabla RAW en PostgreSQL en formato JSON
def insertar_datos_raw(ti):
    conn = psycopg2.connect(
        host='postgres',
        database='airflow',
        user='airflow',
        password='airflow',
        port='5432'
    )
    cursor = conn.cursor()

    for ciudad in ciudades:
        ciudad_key = ciudad.replace(' ', '_').replace(',', '')
        pronostico = ti.xcom_pull(task_ids=f'obtener_pronostico_{ciudad_key}')
        if pronostico:
            # Convierte el pronóstico en formato JSON
            pronostico_json = json.dumps(pronostico[1])
            cursor.execute("INSERT INTO RAW (ciudad, fecha_hora, pronostico_json) VALUES (%s, %s, %s)", (ciudad, pronostico[1]['fecha_hora'], pronostico_json))
    
    conn.commit()
    conn.close()

# Operador Python para insertar datos en la tabla RAW en formato JSON
insertar_datos_raw_op = PythonOperator(
    task_id='insertar_datos_raw',
    python_callable=insertar_datos_raw,
    provide_context=True,
    dag=dag,
)


# Función para insertar datos en la tabla STAGING en PostgreSQL
def insertar_datos_staging(ti):
    conn = psycopg2.connect(
        host='postgres',
        database='airflow',
        user='airflow',
        password='airflow',
        port='5432'
    )
    cursor = conn.cursor()

    for ciudad in ciudades:
        ciudad_key = ciudad.replace(' ', '_').replace(',', '')
        pronostico = ti.xcom_pull(task_ids=f'obtener_pronostico_{ciudad_key}')
        if pronostico:
            print(pronostico)
            fecha_hora_cruda = pronostico[1]['fecha_hora']
            
            # Convierte la fecha y hora cruda a un objeto datetime
            fecha_hora = datetime.utcfromtimestamp(fecha_hora_cruda)
            
            # Luego, formatea la fecha y hora en el formato SQL deseado
            fecha_hora_sql = fecha_hora.strftime("%Y-%m-%d %H:%M:%S")
            print(fecha_hora_sql)
            cursor.execute("INSERT INTO STAGING (ciudad, fecha_hora, temperatura_actual, temperatura_maxima, temperatura_minima, presion, humedad) VALUES (%s, %s, %s, %s, %s, %s, %s)", (ciudad, fecha_hora_sql, pronostico[1]['temperatura_actual'], pronostico[1]['temperatura_maxima'], pronostico[1]['temperatura_minima'], pronostico[1]['presion'], pronostico[1]['humedad']))
    
    conn.commit()
    conn.close()



# Operador Python para insertar datos en la tabla STAGING
insertar_datos_staging_op = PythonOperator(
    task_id='insertar_datos_staging',
    python_callable=insertar_datos_staging,
    provide_context=True,
    dag=dag,
)

# Definición de dependencias
for obtener_pronostico_op in obtener_pronostico_ops:
    obtener_pronostico_op >> crear_tabla_raw_op
crear_tabla_raw_op >> insertar_datos_raw_op
insertar_datos_raw_op >> crear_tabla_staging_op
crear_tabla_staging_op >> insertar_datos_staging_op

