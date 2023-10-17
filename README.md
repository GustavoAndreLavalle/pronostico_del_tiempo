## Readme de la Aplicación

**Requisitos para Correr la App:**

- Docker.
- Docker Compose.

**Datawarehouse de 2 Capas:**
- **Raw:** La data se ingesta tal cual viene de origen.
- **Staging:** Datos en formato de tabla.

**El Proceso Cuenta con 1 DAG:**
- **pronostico_tiempo_dag:** Consta de 5 operadores que se encargan de extraer los datos de la API, crear las tablas RAW y STAGING correspondientes e ingesta los datos con cada nueva corrida.

**Pasos para Ejecutar la Aplicación:**

1. Abrir una terminal y navegar al directorio Airflow.
2. Ejecutar el comando `docker-compose up airflow-init` y esperar a que termine la ejecución para crear la base de datos de metadata y configurar las credenciales de Airflow.
3. Ejecutar el comando `docker-compose up`, que levantará los servicios necesarios para el funcionamiento de la aplicación (Airflow y PostgreSQL).
4. Ingresar desde un navegador a la UI de Airflow (Usuario: airflow / Contraseña: airflow) en [localhost:8080](http://localhost:8080) y ejecutar el DAG `pronostico_tiempo_dag`.

**Aclaraciones:**

Me hubiera gustado incorporar herramientas de AWS, como una instancia EC2 donde montar la imagen o algunos buckets de S3 para usar como Datalake, pero, por una cuestión de practicidad y tiempos, decidí hacerlo todo en local.

**Consultas SQL:**

- **La Ciudad con la Temperatura Promedio Más Alta en la Última Semana:**
    ```sql
    SELECT ciudad, AVG(temperatura_actual) AS temperatura_promedio
    FROM STAGING
    WHERE fecha_hora >= current_date - interval '7 days'
    GROUP BY ciudad
    ORDER BY temperatura_promedio DESC
    LIMIT 1;
    ```

- **La Variabilidad de la Temperatura (Diferencia entre la Máxima y la Mínima) de una Ciudad en un Día Determinado:**
    ```sql
    SELECT ciudad, fecha_hora::date AS fecha, 
           MAX(temperatura_maxima) - MIN(temperatura_minima) AS variabilidad_temperatura
    FROM STAGING
    WHERE ciudad = 'Córdoba, AR' 
      AND fecha_hora::date = '2023-10-17' 
    GROUP BY ciudad, fecha_hora::date;
    ```
