from __future__ import annotations
import os, sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# -------------------------------
# Bootstrap proyecto y .env
# -------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]  # .../appControl
load_dotenv(BASE_DIR / ".env")

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# -------------------------------
# Meta / Base
# -------------------------------
from app.database import Base  # tu declarative_base()

# Importa módulos de modelos para que SQLAlchemy registre tablas en Base.metadata
def _safe_import(modname: str):
    try:
        __import__(modname)
    except ImportError:
        pass

# 👉 Aquí listamos TODOS los módulos de modelos que queremos que Alembic vea
_safe_import("app.models.rutas")          # define class Ruta(Base) si existe
_safe_import("app.models.users")          # define class User(Base) si existe
_safe_import("app.models.eventos")        # define class Evento(Base) si existe
_safe_import("app.models.user_model")     # si tu User está aquí
_safe_import("app.models.models")         # si agrupaste varios modelos en uno
_safe_import("app.models.cfdi_model_sat") # 👈 AÑADIDO: aquí entra tu CFDI

# -------------------------------
# Alembic config
# -------------------------------
config = context.config  # ESTE es el config de Alembic

if config.config_file_name:
    fileConfig(config.config_file_name)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definido")
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata
VERSION_SCHEMA = "hecorp_schema"

# -------------------------------
# Offline
# -------------------------------
def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=VERSION_SCHEMA,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

# -------------------------------
# Online
# -------------------------------
def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        # Asegura el schema antes de migrar
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS hecorp_schema")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=VERSION_SCHEMA,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

# -------------------------------
# Entry
# -------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
