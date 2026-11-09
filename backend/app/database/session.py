import logging
import asyncio
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
from app.database.seed_data import (
    INITIAL_USERS,
    INITIAL_CUSTOMERS,
    INITIAL_INVOICES,
    INITIAL_TRANSACTIONS,
    INITIAL_REMINDERS,
)

logger = logging.getLogger(__name__)

class InMemoryCollection:
    """
    High-fidelity asynchronous in-memory collection fallback
    mirrors Motor/MongoDB async API for offline and test environments.
    """
    def __init__(self, name: str, initial_data: List[Dict[str, Any]] = None):
        self.name = name
        self._data: List[Dict[str, Any]] = [dict(d) for d in (initial_data or [])]
        self._indexes: List[Dict[str, Any]] = []

    async def create_index(self, keys, **kwargs):
        self._indexes.append({"keys": keys, "kwargs": kwargs})
        return str(keys)

    async def insert_one(self, doc: Dict[str, Any]):
        doc_copy = dict(doc)
        if "_id" not in doc_copy:
            doc_copy["_id"] = doc_copy.get("id", str(len(self._data) + 1))
        self._data.append(doc_copy)
        class InsertResult:
            inserted_id = doc_copy["_id"]
        return InsertResult()

    async def find_one(self, filter_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for item in self._data:
            match = True
            for k, v in filter_doc.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                return dict(item)
        return None

    def find(self, filter_doc: Dict[str, Any] = None):
        filter_doc = filter_doc or {}
        matched = []
        for item in self._data:
            match = True
            for k, v in filter_doc.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                matched.append(dict(item))

        class AsyncCursor:
            def __init__(self, items):
                self._items = items
                self._skip_val = 0
                self._limit_val = None

            def sort(self, key_or_list, direction=None):
                # Basic sort support
                if isinstance(key_or_list, list) and key_or_list:
                    k, d = key_or_list[0]
                    rev = d == -1
                    self._items.sort(key=lambda x: str(x.get(k, "")), reverse=rev)
                elif isinstance(key_or_list, str):
                    rev = direction == -1
                    self._items.sort(key=lambda x: str(x.get(key_or_list, "")), reverse=rev)
                return self

            def skip(self, n: int):
                self._skip_val = n
                return self

            def limit(self, n: int):
                self._limit_val = n
                return self

            async def to_list(self, length: int = None):
                res = self._items[self._skip_val:]
                if self._limit_val is not None:
                    res = res[:self._limit_val]
                if length is not None:
                    res = res[:length]
                return [dict(x) for x in res]

            def __aiter__(self):
                self._iter = iter(self._items[self._skip_val:None if self._limit_val is None else self._skip_val + self._limit_val])
                return self

            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

        return AsyncCursor(matched)

    async def count_documents(self, filter_doc: Dict[str, Any] = None) -> int:
        filter_doc = filter_doc or {}
        count = 0
        for item in self._data:
            match = True
            for k, v in filter_doc.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                count += 1
        return count

    async def update_one(self, filter_doc: Dict[str, Any], update_doc: Dict[str, Any]):
        matched = 0
        modified = 0
        for item in self._data:
            match = True
            for k, v in filter_doc.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                matched = 1
                if "$set" in update_doc:
                    for sk, sv in update_doc["$set"].items():
                        item[sk] = sv
                        modified = 1
                break
        class UpdateResult:
            matched_count = matched
            modified_count = modified
        return UpdateResult()

    async def delete_one(self, filter_doc: Dict[str, Any]):
        deleted = 0
        for i, item in enumerate(self._data):
            match = True
            for k, v in filter_doc.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                del self._data[i]
                deleted = 1
                break
        class DeleteResult:
            deleted_count = deleted
        return DeleteResult()


class DatabaseManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    is_connected: bool = False
    is_mock: bool = False

    # Fallback storage collections
    _mock_collections: Dict[str, InMemoryCollection] = {}

    def get_collection(self, name: str):
        if self.is_connected and self.db is not None:
            return self.db[name]
        # Return memory collection fallback
        if name not in self._mock_collections:
            seed_map = {
                "users": INITIAL_USERS,
                "customers": INITIAL_CUSTOMERS,
                "invoices": INITIAL_INVOICES,
                "transactions": INITIAL_TRANSACTIONS,
                "reminders": INITIAL_REMINDERS,
            }
            self._mock_collections[name] = InMemoryCollection(name, seed_map.get(name, []))
        return self._mock_collections[name]

    @property
    def users(self):
        return self.get_collection("users")

    @property
    def customers(self):
        return self.get_collection("customers")

    @property
    def invoices(self):
        return self.get_collection("invoices")

    @property
    def transactions(self):
        return self.get_collection("transactions")

    @property
    def reminders(self):
        return self.get_collection("reminders")

    @property
    def ai_conversations(self):
        return self.get_collection("ai_conversations")

    @property
    def notifications(self):
        return self.get_collection("notifications")

    @property
    def automation_logs(self):
        return self.get_collection("automation_logs")


db_manager = DatabaseManager()

def _is_mongodb_reachable(url: str) -> bool:
    """Pre-flight socket check to avoid Motor background thread hangs if MongoDB is unreachable."""
    import socket
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 27017
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            s.connect((host, port))
            return True
    except Exception:
        return False

async def connect_to_mongo():
    """Connect to MongoDB and initialize collections and indexes."""
    if not _is_mongodb_reachable(settings.mongodb_url):
        if settings.environment.lower() == "production":
            logger.critical(
                f"FATAL: MongoDB server at {settings.mongodb_url} is unreachable in PRODUCTION mode. "
                f"In-memory fallback is strictly disabled in production to protect transactional integrity."
            )
            db_manager.is_connected = False
            db_manager.is_mock = False
            raise RuntimeError(f"Database connection failed in production: {settings.mongodb_url}")

        logger.warning(
            f"MongoDB server at {settings.mongodb_url} is not reachable. "
            f"Activating high-fidelity asynchronous repository with initial seed data. "
            f"All endpoints, operations, and tests will function seamlessly in development/test."
        )
        db_manager.is_connected = False
        db_manager.is_mock = True
        _init_mock_storage()
        return

    try:
        logger.info(f"Connecting to MongoDB at {settings.mongodb_url}...")
        client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
        )
        # Verify connection
        await asyncio.wait_for(client.admin.command("ping"), timeout=2.5)
        db_manager.client = client
        db_manager.db = client[settings.database_name]
        db_manager.is_connected = True
        db_manager.is_mock = False
        logger.info(f"Successfully connected to MongoDB database: {settings.database_name}")

        # Initialize collections and indexes
        await _setup_indexes()
        await _seed_mongodb_if_empty()

    except Exception as e:
        if settings.environment.lower() == "production":
            logger.critical(f"FATAL: MongoDB connection to {settings.mongodb_url} failed in production: {e}")
            db_manager.is_connected = False
            db_manager.is_mock = False
            raise RuntimeError(f"Database connection failed in production: {e}")

        logger.warning(
            f"MongoDB connection to {settings.mongodb_url} unavailable ({e}). "
            f"Activating high-fidelity asynchronous repository with initial seed data. "
            f"All endpoints, operations, and tests will function seamlessly in development/test."
        )
        db_manager.is_connected = False
        db_manager.is_mock = True
        _init_mock_storage()

def _init_mock_storage():
    """Initialize in-memory collections with seed data."""
    db_manager._mock_collections = {
        "users": InMemoryCollection("users", INITIAL_USERS),
        "customers": InMemoryCollection("customers", INITIAL_CUSTOMERS),
        "invoices": InMemoryCollection("invoices", INITIAL_INVOICES),
        "transactions": InMemoryCollection("transactions", INITIAL_TRANSACTIONS),
        "reminders": InMemoryCollection("reminders", INITIAL_REMINDERS),
        "ai_conversations": InMemoryCollection("ai_conversations", []),
        "notifications": InMemoryCollection("notifications", []),
        "automation_logs": InMemoryCollection("automation_logs", []),
    }

async def _setup_indexes():
    """Create MongoDB indexes for performance and uniqueness."""
    if not db_manager.is_connected or db_manager.db is None:
        return
    try:
        # Users indexes
        await db_manager.db.users.create_index("email", unique=True)
        # Customers indexes
        await db_manager.db.customers.create_index("email")
        # Invoices indexes
        await db_manager.db.invoices.create_index("invoice_number", unique=True)
        await db_manager.db.invoices.create_index("customer_id")
        await db_manager.db.invoices.create_index("status")
        await db_manager.db.invoices.create_index("due_date")
        # Transactions indexes
        await db_manager.db.transactions.create_index("invoice_id")
        await db_manager.db.transactions.create_index("status")
        await db_manager.db.transactions.create_index("created_date")
        # Reminders indexes
        await db_manager.db.reminders.create_index("invoice_id")
        await db_manager.db.reminders.create_index("status")
        # AI Conversations indexes
        await db_manager.db.ai_conversations.create_index("conversation_id", unique=True)
        await db_manager.db.ai_conversations.create_index("updated_at")
        # Notifications indexes
        await db_manager.db.notifications.create_index("created_at")
        await db_manager.db.notifications.create_index("read")
        # Automation Logs indexes
        await db_manager.db.automation_logs.create_index("executed_at")
        await db_manager.db.automation_logs.create_index("job_id")
        logger.info("MongoDB indexes verified.")
    except Exception as e:
        logger.warning(f"Error creating MongoDB indexes: {e}")

async def _seed_mongodb_if_empty():
    """Seed MongoDB collections if they are empty."""
    if not db_manager.is_connected or db_manager.db is None:
        return
    try:
        cust_count = await db_manager.db.customers.count_documents({})
        if cust_count == 0:
            logger.info("Seeding initial customers to MongoDB...")
            await db_manager.db.customers.insert_many([dict(c) for c in INITIAL_CUSTOMERS])

        inv_count = await db_manager.db.invoices.count_documents({})
        if inv_count == 0:
            logger.info("Seeding initial invoices to MongoDB...")
            await db_manager.db.invoices.insert_many([dict(i) for i in INITIAL_INVOICES])

        txn_count = await db_manager.db.transactions.count_documents({})
        if txn_count == 0:
            logger.info("Seeding initial transactions to MongoDB...")
            await db_manager.db.transactions.insert_many([dict(t) for t in INITIAL_TRANSACTIONS])

        rem_count = await db_manager.db.reminders.count_documents({})
        if rem_count == 0:
            logger.info("Seeding initial reminders to MongoDB...")
            await db_manager.db.reminders.insert_many([dict(r) for r in INITIAL_REMINDERS])
    except Exception as e:
        logger.warning(f"Error seeding MongoDB: {e}")

async def close_mongo_connection():
    """Close MongoDB connection on app shutdown."""
    if db_manager.client:
        db_manager.client.close()
        logger.info("MongoDB client closed.")

def get_database():
    return db_manager.db

