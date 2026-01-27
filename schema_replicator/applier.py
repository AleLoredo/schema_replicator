from sqlalchemy.engine import Engine
from sqlalchemy import text
from typing import List
import logging

logger = logging.getLogger(__name__)

class DDLApplier:
    def __init__(self, engine: Engine):
        self.engine = engine

    def apply_ddl(self, ddl_statements: List[str]):
        """
        Executes a list of DDL statements against the database.
        """
        with self.engine.connect() as conn:
            with conn.begin(): # Transactional DDL if supported
                for stmt in ddl_statements:
                    if not stmt.strip():
                        continue
                        
                    logger.info(f"Executing DDL: {stmt[:50]}...") # Log partial for brevity
                    try:
                        conn.execute(text(stmt))
                    except Exception as e:
                        logger.error(f"Error executing DDL: {stmt}\nError: {e}")
                        raise e
