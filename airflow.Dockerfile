# Extends the stock Airflow image with the subset of CivicLens dependencies
# actually imported by ingestion/dags/daily_tenders.py's task bodies, plus the
# dbt CLI. Deliberately excludes heavy/unused extras (playwright, camelot,
# prophet, xgboost, geopandas) that the DAG never imports — keeping this
# image lean and avoiding dependency conflicts with Airflow's own pins.
FROM apache/airflow:2.9.3-python3.12

# Airflow's official images run pip installs as the non-root `airflow` user;
# packages land in /home/airflow/.local and are already on PATH.
#
# Deliberately do NOT pin/upgrade sqlalchemy here: Airflow 2.9.3's own ORM
# models require SQLAlchemy 1.4.x (flask-appbuilder enforces <1.5). Forcing
# sqlalchemy>=2.0 breaks `airflow db migrate` itself (TaskInstance.dag_model
# mapping error) because Airflow's declarative models aren't written for 2.0's
# stricter typing. sqlalchemy.ext.asyncio (AsyncEngine/AsyncSession) already
# exists in 1.4, so audit_logger.py works fine against whatever 1.4.x version
# Airflow's base image ships — just don't touch it.
RUN pip install --no-cache-dir \
    httpx>=0.27 \
    structlog>=24.2 \
    beautifulsoup4>=4.12 \
    lxml>=5.2 \
    tenacity>=8.3 \
    pydantic>=2.0 \
    pydantic-settings>=2.3 \
    asyncpg>=0.29 \
    mlflow>=2.13 \
    numpy \
    pandas>=2.2 \
    pyod>=1.1 \
    dbt-postgres>=1.8
