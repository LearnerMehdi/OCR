"""
Simple MongoDB Manager - Save Data Only
Handles only inserting data to local MongoDB server
"""

from datetime import datetime
from typing import List, Dict, Optional, Any

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, PyMongoError
except ImportError:
    raise ImportError("pymongo is required. Install with: pip install pymongo")


class SimpleMongoManager:
    """Minimal MongoDB manager for saving data only."""
    
    def __init__(self, 
                 connection_string: str,
                 database_name: str,
                 collection_name: str):
        """
        Initialize MongoDB connection.
        
        Args:
            connection_string: MongoDB connection URI (default: local server)
            database_name: Database name
            collection_name: Collection name
        """
        self.client = MongoClient(connection_string)
        self.db = self.client[database_name]
        self.collection = self.db[collection_name]
        
        # Verify connection
        try:
            self.client.admin.command('ping')
            print(f"✓ Connected to MongoDB: {database_name}/{collection_name}")
        except ConnectionFailure as e:
            raise ConnectionFailure(f"Failed to connect to MongoDB: {e}")
    
    def save(self, data: Dict[str, Any]) -> str:
        """
        Save a single document to MongoDB.
        
        Args:
            data: Dictionary containing the data to save
        
        Returns:
            MongoDB document _id as string
        
        Example:
            manager.save({
                'countries': ['FRANCE', 'ITALY'],
                'weights': [{'value': 850.0, 'unit': 'KG'}],
                'items': ['SANTOS NO:33 BAR BLENDIR']
            })
        """
        # Add timestamp
        data['created_at'] = datetime.utcnow()
        
        try:
            result = self.collection.insert_one(data)
            print(f"✓ Document saved: {result.inserted_id}")
            return str(result.inserted_id)
        except PyMongoError as e:
            raise Exception(f"Failed to save document: {e}")
    
    def save_batch(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Save multiple documents in batch.
        
        Args:
            documents: List of dictionaries to save
        
        Returns:
            List of inserted document _ids
        
        Example:
            documents = [
                {'countries': ['FRANCE'], 'items': ['Item 1']},
                {'countries': ['ITALY'], 'items': ['Item 2']}
            ]
            ids = manager.save_batch(documents)
        """
        # Add timestamps to all documents
        for doc in documents:
            doc['created_at'] = datetime.utcnow()
        
        try:
            result = self.collection.insert_many(documents)
            print(f"✓ {len(result.inserted_ids)} documents saved")
            return [str(doc_id) for doc_id in result.inserted_ids]
        except PyMongoError as e:
            raise Exception(f"Failed to save batch: {e}")
    
    def close(self):
        """Close MongoDB connection."""
        self.client.close()
        print("✓ Connection closed")


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("SIMPLE MONGODB MANAGER - TEST")
    print("=" * 60)
    
    try:
        # Initialize
        print("\n1. Connecting to MongoDB...")
        manager = SimpleMongoManager(
            connection_string="mongodb://localhost:27017/",
            database_name="OCR",
            collection_name="OCR_results"
        )
        
        # Save single document
        print("\n2. Saving single document...")
        doc_id = manager.save({
            'countries': ['FRANCE', 'ITALY'],
            'weights': [
                {'value': 850.0, 'unit': 'KG'},
                {'value': 2280.0, 'unit': 'KG'}
            ],
            'items': [
                'SANTOS NO:33 BAR BLENDIR',
                'ROBOT COUPE MP 450',
                'LAINOX ICET051 FIRIN'
            ],
            'source_file': 'invoice_001.pdf'
        })
        print(f"  Saved with ID: {doc_id}")
        
        # Save multiple documents
        print("\n3. Saving batch of documents...")
        documents = [
            {
                'countries': ['GERMANY'],
                'weights': [{'value': 150.0, 'unit': 'KG'}],
                'items': ['Product A']
            },
            {
                'countries': ['SPAIN'],
                'weights': [{'value': 200.0, 'unit': 'KG'}],
                'items': ['Product B']
            }
        ]
        ids = manager.save_batch(documents)
        print(f"  Saved IDs: {ids}")
        
        # Close
        print("\n4. Closing connection...")
        manager.close()
        
        print("\n" + "=" * 60)
        print("✓ Test completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure MongoDB is running:")
        print("  docker run -d -p 27017:27017 mongo")