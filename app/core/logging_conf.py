import sys, os
from loguru import logger

def setup_logging():
    logger.remove()
    # consola (JSON)
    logger.add(sys.stdout, serialize=True, backtrace=False, diagnose=False, level="INFO")

    # archivo rotado (histórico)
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/app.json.log",
        serialize=True,             # JSON
        rotation="10 MB",           # rota por tamaño
        retention="30 days",        # conserva 30 días
        compression="zip",          # opcional
        enqueue=True,               # seguro con multiproceso
        level="INFO"
    )
    return logger
