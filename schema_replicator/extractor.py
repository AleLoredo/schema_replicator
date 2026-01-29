from typing import List, Tuple, Any
from sqlalchemy.engine import Engine
from sqlalchemy import inspect, MetaData, Table, Column
from sqlalchemy.schema import CreateTable, CreateIndex, AddConstraint
from sqlalchemy.ext.compiler import compiles

class DDLExtractor:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.metadata = MetaData()
        self.inspector = inspect(engine)

    def get_table_base_ddl(self, table_name: str) -> str:
        """
        Generates the CREATE TABLE statement WITHOUT Foreign Keys or Indexes.
        Useful for initial data loading.
        """
        # Reflect the table
        table = Table(table_name, self.metadata, autoload_with=self.engine)
        
        # Create a copy of the table without constraints/indexes for DDL generation
        # We manually construct the CreateTable logic to exclude constraints if needed,
        # or we can iterate columns and build a clean table object.
        
        # A safer way to strip constraints for the SQL generation is using the 
        # CreateTable construct and manipulating it or the table object temporarily.
        
        # However, modifying the reflected table is risky. 
        # Strategy: Clone the table columns into a new MetaData object without constraints.
        
        clean_metadata = MetaData()
        clean_table = Table(table_name, clean_metadata)
        
        for col in table.columns:
            # Copy column definition
            # We copy name, type, and nullable. 
            # We might want to keep PrimaryKey for basic structure? 
            # The prompt asked for "without FKs/Indexes". 
            # PKs are usually Index-enforced.
            # If we want pure data load speed, maybe no PKs either initially?
            # Usually PKs are okay, but if prompt said "without constraints" likely implies NO foreign keys.
            # Let's keep PK definition in the column but ensure no ForeignKeyConstraints are added at table level.
            
            # Note: col.copy() preserves everything.
            # new_col = col.copy()
            # Strip foreign keys from the column definition if any (inline FKs)
            
            # Since .copy() is deprecated, we construct a new Column with the desired attributes
            # We explicitly do NOT include foreign_keys.
            new_col = Column(
                col.name,
                col.type,
                nullable=col.nullable,
                primary_key=col.primary_key,
                autoincrement=col.autoincrement,
                default=col.default,
                server_default=col.server_default,
                comment=col.comment,
                # explicitly omit foreign_keys
            )
            
            clean_table.append_column(new_col)
            
        # Compile
        ddl = CreateTable(clean_table).compile(self.engine, compile_kwargs={"literal_binds": True})
        return str(ddl).strip() + ";"

    def get_constraints_and_indexes_ddl(self, table_name: str) -> List[str]:
        """
        Generates DDL for adding Constraints (PKs, FKs, UQs) and Indexes separately.
        To be applied AFTER data load.
        """
        table = Table(table_name, self.metadata, autoload_with=self.engine, extend_existing=True)
        ddl_statements = []

        # 1. Indexes
        for index in table.indexes:
            # CreateIndex
            stmt = CreateIndex(index).compile(self.engine)
            ddl_statements.append(str(stmt) + ";")
            
        # 2. Constraints (FKs, etc)
        # SQLAlchemy stores constraints in table.constraints
        # We need to filter out the "Primary Key" if we already included it in the CREATE TABLE?
        # If get_base_ddl included PK columns but not the Constraint object explicitly?
        # Actually, `CreateTable` usually includes PK constraints inline or at bottom.
        # If we stripped everything in `get_base_ddl` (schema-less clone), we need to add PKs here too.
        # My implementation of `get_base_ddl` used col.copy(), which keeps `primary_key=True` flag.
        # So PK is likely in Base DDL. 
        
        # Let's handle ForeignKeys specifically.
        # Note: CreateTable(clean_table) in base_ddl won't have Table-level constraints unless we add them.
        # But we didn't add any.
        
        for const in table.constraints:
            # We skip PrimaryKeyConstraint if it was implicitly created by the column definitions in base DDL
            # (which it usually is if primary_key=True on column).
            from sqlalchemy.sql.schema import PrimaryKeyConstraint, ForeignKeyConstraint, UniqueConstraint, CheckConstraint
            
            if isinstance(const, PrimaryKeyConstraint):
                continue # Assumed handled in Base DDL via column flags
                
            # For Foreign Keys and others, we allow them here
            # AddConstraint helps generate "ALTER TABLE ADD CONSTRAINT ..."
            stmt = AddConstraint(const).compile(self.engine)
            ddl_statements.append(str(stmt) + ";")
            
        return ddl_statements
