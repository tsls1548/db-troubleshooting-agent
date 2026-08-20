import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
import sqlalchemy

load_dotenv()

INSTANCE = os.environ["INSTANCE_CONNECTION_NAME"]
DB_NAME = os.environ["DB_NAME"]

_connector = Connector()


def _engine(user: str, password: str) -> sqlalchemy.engine.Engine:
    def getconn():
        return _connector.connect(
            INSTANCE, "pg8000", user=user, password=password, db=DB_NAME
        )

    return sqlalchemy.create_engine(
        "postgresql+pg8000://", creator=getconn, pool_size=2, max_overflow=2,
        pool_pre_ping=True,
    )


def admin_engine() -> sqlalchemy.engine.Engine:
    return _engine(os.environ["DB_ADMIN_USER"], os.environ["DB_ADMIN_PASSWORD"])


def readonly_engine() -> sqlalchemy.engine.Engine:
    return _engine(os.environ["DB_RO_USER"], os.environ["DB_RO_PASSWORD"])