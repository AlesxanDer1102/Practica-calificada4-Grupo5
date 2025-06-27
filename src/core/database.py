from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.util.typing import dataclass_transform

# Creación de objeto que establece conexión con la base de datos mediante el objeto de configuración
DATABASE_URL = "postgresql://postgres:12345@localhost:5432/pc_db"
engine = create_engine(DATABASE_URL)

# Creación de objeto de generación de sesiones de interacción con la base de datos
SessionLocal = sessionmaker(autoflush=False, bind=engine)

# Declaración de objeto Base para inicialización de objetos de la base de datos
Base = declarative_base()
