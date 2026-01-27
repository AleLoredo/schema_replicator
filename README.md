# Schema Replicator

**Schema Replicator** is a specialized module designed to handle the intelligent replication of database schemas. Unlike standard dump utilities, it is designed to split the DDL (Data Definition Language) generation into logical phases to support high-performance data loading pipelines.

This library will allow you to clone a DB structure to another DB. Then you may use another tool to migrate the data from one DB to another being able to run multiple parallel batches while not having to worry about the order of the data. Finally, with just one command, this library will apply the integrity restrictions on the target DB (Foreign Keys, Constraints) once you are done loading the data. 

## Core Philosophy

Relational databases have strict integrity rules (Foreign Keys, Constraints) that make simple data copying difficult (the "Chicken and Egg" problem).

Schema Replicator solves this by decoupling the **Structure** from the **Integrity**:

1.  **Base DDL**: Creates tables with columns and primary types only.
2.  **Constraint DDL**: Creates Foreign Keys, non-essential Indexes, and complex checks.

By applying "Base DDL" first and "Constraint DDL" last, we allow data pipelines (like `db_orchestrator`) to load data in parallel without worrying about insertion order or constraint violations.

## Components

### `extractor.py` (`DDLExtractor`)
Uses SQLAlchemy's inspection engine to reflect an existing database.
*   `get_table_base_ddl(table_name)`: Returns the `CREATE TABLE` SQL statement stripped of Foreign Keys and complex constraints.
*   `get_constraints_and_indexes_ddl(table_name)`: Returns a list of `ALTER TABLE ADD CONSTRAINT` and `CREATE INDEX` statements.

### `applier.py` (`DDLApplier`)
A simple executor wrapper.
*   `apply_ddl(ddl_statements)`: Executes a list of SQL statements against a target database connection transactionally.

## Integration

### With `db_orchestrator`
This module is the backbone of the Orchestrator's migration strategy.
*   **Phase 1**: Orchestrator calls `get_table_base_ddl` to prepare the destination.
*   **Phase 2**: Orchestrator loads data using `anonimize`.
*   **Phase 3**: Orchestrator calls `get_constraints_and_indexes_ddl` to seal the database integrity.

### With `anonimize`
While `schema_replicator` does not directly import `anonimize`, they are symbiotic.
*   `schema_replicator` ensures the **container** (Table) exists and has the correct data types.
*   `anonimize` ensures the **content** (Rows) is transformed and secure before filling that container.

## Usage Example

```python
from sqlalchemy import create_engine
from schema_replicator.extractor import DDLExtractor
from schema_replicator.applier import DDLApplier

source_engine = create_engine("postgresql://user:pass@source/db")
dest_engine = create_engine("postgresql://user:pass@dest/db")

extractor = DDLExtractor(source_engine)
applier = DDLApplier(dest_engine)

# 1. Base Structure
base_sql = extractor.get_table_base_ddl("users")
applier.apply_ddl([base_sql])

# ... Load Data Here ...

# 2. Integrity
constraints_sql = extractor.get_constraints_and_indexes_ddl("users")
applier.apply_ddl(constraints_sql)
```
