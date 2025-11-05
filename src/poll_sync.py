import os
import asyncio
import urllib.parse
import time
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# --- Environment Variable Handling ---
DOCDB_USER = os.getenv("DOCDB_USER")
DOCDB_PASSWORD = os.getenv("DOCDB_PASSWORD")
DOCDB_HOST = os.getenv("DOCDB_HOST")
ATLAS_URI = os.getenv("ATLAS_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10000"))  # Increased batch size for large collections
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))  # Poll every 5 seconds
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# --- Validate environment variables ---
required_vars = ["DOCDB_USER", "DOCDB_PASSWORD", "DOCDB_HOST", "ATLAS_URI", "DATABASE_NAME"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

# --- Percent-encode username and password ---
encoded_user = urllib.parse.quote_plus(DOCDB_USER)
encoded_password = urllib.parse.quote_plus(DOCDB_PASSWORD)

# --- MongoDB Clients ---
docdb_client = None
atlas_client = None
source_db = None
target_db = None

async def initialize_clients():
    """Initialize the database clients"""
    global docdb_client, atlas_client, source_db, target_db

    try:
        docdb_client = AsyncIOMotorClient(
            f"mongodb://{encoded_user}:{encoded_password}@{DOCDB_HOST}:27017/?tls=true"
            f"&tlsCAFile=/etc/ssl/certs/global-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred",
            maxPoolSize=200
        )

        atlas_client = AsyncIOMotorClient(ATLAS_URI, maxPoolSize=200)

        source_db = docdb_client[DATABASE_NAME]
        target_db = atlas_client[DATABASE_NAME]

        logger.info("Database clients initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database clients: {e}")
        return False

# Track sync state for each collection in memory instead of database
sync_state = {}

def get_last_sync_time(collection_name):
    """Get the last sync timestamp for a collection from memory"""
    if collection_name not in sync_state:
        # Initialize with a timestamp from 1 hour ago for first sync
        sync_state[collection_name] = datetime.utcnow() - timedelta(hours=1)
    return sync_state[collection_name]

def update_last_sync_time(collection_name, timestamp):
    """Update the last sync timestamp for a collection in memory"""
    sync_state[collection_name] = timestamp

async def sync_document(source_doc, target_collection, collection_name):
    """Sync a single document to the target collection"""
    doc_id = source_doc["_id"]

    try:
        # Check if document exists in target
        existing_doc = await target_collection.find_one({"_id": doc_id})

        if existing_doc:
            # Compare and update if different
            if existing_doc != source_doc:
                await target_collection.replace_one({"_id": doc_id}, source_doc)
                logger.info(f"Updated document {doc_id} in {collection_name}")
        else:
            # Insert new document
            await target_collection.insert_one(source_doc)
            logger.info(f"Inserted document {doc_id} in {collection_name}")

    except Exception as e:
        logger.error(f"Error syncing document {doc_id} in {collection_name}: {e}")
        raise

async def sync_collection_polling(collection_name):
    """Polling-based synchronization for a collection"""
    source_collection = source_db[collection_name]
    target_collection = target_db[collection_name]

    logger.info(f"Starting polling sync for: {collection_name}")

    # Check if collection has timestamp fields on first run
    has_timestamp_field = False
    timestamp_field_used = None

    # Check for common timestamp fields
    timestamp_fields = ["updatedAt", "modifiedAt", "lastModified", "createdAt", "_id"]

    for field in timestamp_fields:
        sample_doc = await source_collection.find_one({field: {"$exists": True}})
        if sample_doc:
            has_timestamp_field = True
            timestamp_field_used = field
            logger.info(f"Using timestamp field '{field}' for {collection_name}")
            break

    if not has_timestamp_field:
        logger.warning(f"No timestamp fields found in {collection_name}. Will use _id for ordering (less efficient)")
        timestamp_field_used = "_id"

    # Track last processed ID for collections without timestamp fields
    last_processed_id = None

    while True:
        try:
            last_sync = get_last_sync_time(collection_name)
            current_time = datetime.utcnow()

            # Build query based on available fields
            if timestamp_field_used == "_id":
                # Use ObjectId for ordering when no timestamp fields exist
                if last_processed_id:
                    query = {"_id": {"$gt": last_processed_id}}
                else:
                    # On first run, get documents from last hour based on ObjectId
                    from bson import ObjectId
                    hour_ago_objectid = ObjectId.from_datetime(datetime.utcnow() - timedelta(hours=1))
                    query = {"_id": {"$gte": hour_ago_objectid}}
            else:
                # Use timestamp field
                query = {timestamp_field_used: {"$gt": last_sync}}

            # Find documents that need syncing
            if timestamp_field_used == "_id":
                cursor = source_collection.find(query).sort("_id", 1).limit(BATCH_SIZE)
            else:
                cursor = source_collection.find(query).limit(BATCH_SIZE)

            documents_synced = 0
            current_batch_last_id = None

            async for doc in cursor:
                await sync_document(doc, target_collection, collection_name)
                documents_synced += 1
                current_batch_last_id = doc["_id"]

            if documents_synced > 0:
                logger.info(f"Synced {documents_synced} documents from {collection_name}")

                # Update tracking based on field type
                if timestamp_field_used == "_id":
                    last_processed_id = current_batch_last_id
                else:
                    update_last_sync_time(collection_name, current_time)
            else:
                # No new documents, update sync time anyway
                if timestamp_field_used != "_id":
                    update_last_sync_time(collection_name, current_time)

            # Wait before next poll
            await asyncio.sleep(POLL_INTERVAL)

        except Exception as e:
            logger.error(f"Error in polling sync for {collection_name}: {e}")
            await asyncio.sleep(POLL_INTERVAL * 2)  # Back off on error

async def test_database_connection():
    """Test database connections and collection access"""
    try:
        logger.info("Testing DocumentDB connection...")
        source_collections = await source_db.list_collection_names()
        logger.info(f"DocumentDB collections found: {len(source_collections)}")

        logger.info("Testing Atlas connection...")
        target_collections = await target_db.list_collection_names()
        logger.info(f"Atlas collections found: {len(target_collections)}")

        # Test sync collection creation
        logger.info("Testing sync collection access...")
        sync_coll = target_db.get_collection("sync_state_tracker")
        test_doc = {"test": "connection", "timestamp": datetime.utcnow()}
        result = await sync_coll.insert_one(test_doc)
        logger.info(f"Test document inserted with ID: {result.inserted_id}")

        # Clean up test document
        await sync_coll.delete_one({"_id": result.inserted_id})
        logger.info("Test document cleaned up")

        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

async def sync_collection(collection_name):
    """Main sync function for a collection (polling only)"""
    try:
        await sync_collection_polling(collection_name)
    except Exception as e:
        logger.error(f"Error in sync_collection for {collection_name}: {e}")

async def main():
    """Main function to orchestrate the synchronization"""
    try:
        # Initialize clients
        if not await initialize_clients():
            logger.error("Failed to initialize database clients. Exiting.")
            return

        # Test connections first
        if not await test_database_connection():
            logger.error("Database connection test failed. Exiting.")
            return

        # Get list of collections to sync
        collection_names = await source_db.list_collection_names()

        # Filter out system collections
        collection_names = [name for name in collection_names if not name.startswith('system.')]

        logger.info(f"Found {len(collection_names)} collections to sync: {collection_names}")

        # Create tasks for each collection
        tasks = []
        for collection_name in collection_names:
            task = asyncio.create_task(
                sync_collection(collection_name)
            )
            tasks.append(task)

        # Run all sync tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        # Close connections
        if docdb_client:
            docdb_client.close()
        if atlas_client:
            atlas_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sync interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

