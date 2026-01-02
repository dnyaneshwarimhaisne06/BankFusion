const { MongoClient } = require('mongodb');

const MONGO_URI = 'mongodb://localhost:27017';
const DB_NAME = 'bankfusion_db';

class BankFusionDB {
  constructor() {
    this.client = null;
    this.db = null;
  }

  async connect() {
    try {
      this.client = new MongoClient(MONGO_URI);
      await this.client.connect();
      this.db = this.client.db(DB_NAME);
      console.log('✓ Connected to MongoDB');
      console.log(`✓ Database: ${DB_NAME}`);
      return this.db;
    } catch (error) {
      console.error('❌ MongoDB connection error:', error.message);
      throw error;
    }
  }

  async setupCollections() {
    try {
      const collections = await this.db.listCollections().toArray();
      const collectionNames = collections.map(c => c.name);

      if (!collectionNames.includes('bank_statements')) {
        await this.db.createCollection('bank_statements', {
          validator: {
            $jsonSchema: {
              bsonType: 'object',
              required: ['accountNumber', 'bankName', 'accountHolder'],
              properties: {
                accountNumber: { 
                  bsonType: 'string',
                  description: 'Account number - required'
                },
                bankName: { 
                  bsonType: 'string',
                  description: 'Bank name (AXIS/BOI) - required'
                },
                accountHolder: { 
                  bsonType: 'string',
                  description: 'Account holder name - required'
                },
                statementDate: { 
                  bsonType: 'date',
                  description: 'Statement date'
                },
                transactions: {
                  bsonType: 'array',
                  description: 'Array of transactions',
                  items: {
                    bsonType: 'object',
                    properties: {
                      date: { bsonType: 'date' },
                      description: { bsonType: 'string' },
                      amount: { bsonType: 'number' },
                      type: { enum: ['debit', 'credit', 'DEBIT', 'CREDIT'] },
                      balance: { bsonType: 'number' }
                    }
                  }
                }
              }
            }
          }
        });
        console.log('✓ Created bank_statements collection');
      } else {
        console.log('✓ bank_statements collection already exists');
      }

      await this.createIndexes();
    } catch (error) {
      console.error('❌ Setup error:', error.message);
      throw error;
    }
  }

  async createIndexes() {
    const statements = this.db.collection('bank_statements');

    // Unique index to prevent duplicates
    await statements.createIndex(
      { accountNumber: 1, statementDate: 1 },
      { unique: true, name: 'unique_statement_idx' }
    );

    // Index for bank queries
    await statements.createIndex(
      { bankName: 1, statementDate: -1 },
      { name: 'bank_date_idx' }
    );

    // Index for account holder
    await statements.createIndex(
      { accountHolder: 1 },
      { name: 'account_holder_idx' }
    );

    // Index for date range queries
    await statements.createIndex(
      { statementDate: -1 },
      { name: 'statement_date_idx' }
    );

    // Index for transactions
    await statements.createIndex(
      { 'transactions.date': 1 },
      { name: 'transaction_date_idx' }
    );

    // Text index for searching descriptions
    await statements.createIndex(
      { 'transactions.description': 'text' },
      { name: 'transaction_text_idx' }
    );

    console.log('✓ All indexes created successfully');
  }

  async close() {
    if (this.client) {
      await this.client.close();
      console.log('✓ MongoDB connection closed');
    }
  }
}

module.exports = { BankFusionDB };