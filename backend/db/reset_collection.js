const { MongoClient } = require('mongodb');

const MONGO_URI = 'mongodb://localhost:27017';
const DB_NAME = 'bankfusion_db';
const COLLECTION_NAME = 'bank_statements';

async function resetCollection() {
  const client = new MongoClient(MONGO_URI);
  
  try {
    await client.connect();
    console.log('✓ Connected to MongoDB\n');
    
    const db = client.db(DB_NAME);
    const collection = db.collection(COLLECTION_NAME);
    
    // Option 1: Drop all indexes and recreate
    console.log('🔄 Dropping all indexes...');
    await collection.dropIndexes();
    console.log('✓ All indexes dropped\n');
    
    // Option 2: Or drop entire collection and start fresh
    // console.log('🗑️ Dropping collection...');
    // await collection.drop();
    // console.log('✓ Collection dropped\n');
    
    console.log('✅ Collection reset complete!');
    console.log('You can now run: node import_normalized.js\n');
    
  } catch (error) {
    console.error('❌ Reset failed:', error.message);
  } finally {
    await client.close();
  }
}

resetCollection();