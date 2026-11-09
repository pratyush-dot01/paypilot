from app.database.session import (
    db_manager,
    connect_to_mongo,
    close_mongo_connection,
    get_database,
    DatabaseManager,
)

# Compatibility alias for Phase 1 db_instance
db_instance = db_manager

__all__ = [
    "db_manager",
    "db_instance",
    "connect_to_mongo",
    "close_mongo_connection",
    "get_database",
    "DatabaseManager",
]

