// File: backend/db/import_normalized.js
// Import normalized JSON data from ../data/normalized_json into MongoDB

const fs = require('fs').promises;
const path = require('path');
const { MongoClient } = require('mongodb');

// MongoDB Configuration
const MONGO_URI = 'mongodb://localhost:27017';
const DB_NAME = 'bankfusion_db';
const COLLECTION_NAME = 'bank_statements';

class NormalizedDataImporter {
  constructor() {
    this.client = null;
    this.db = null;
    this.collection = null;
    this.stats = {
      total: 0,
      inserted: 0,
      duplicates: 0,
      errors: 0,
      errorDetails: [],
      byBank: {}
    };
  }

  async connect() {
    try {
      this.client = new MongoClient(MONGO_URI);
      await this.client.connect();
      this.db = this.client.db(DB_NAME);
      this.collection = this.db.collection(COLLECTION_NAME);
      console.log('✓ Connected to MongoDB');
      console.log(`✓ Database: ${DB_NAME}`);
      console.log(`✓ Collection: ${COLLECTION_NAME}\n`);
      return this.db;
    } catch (error) {
      console.error('❌ MongoDB connection error:', error.message);
      throw error;
    }
  }

  async setupCollection() {
    try {
      const collections = await this.db.listCollections().toArray();
      const collectionNames = collections.map(c => c.name);

      if (!collectionNames.includes(COLLECTION_NAME)) {
        await this.db.createCollection(COLLECTION_NAME);
        console.log(`✓ Created collection: ${COLLECTION_NAME}`);
      }

      // Create indexes for fast queries
      await this.createIndexes();
    } catch (error) {
      console.error('❌ Setup error:', error.message);
      throw error;
    }
  }

  async createIndexes() {
    // Unique index to prevent duplicate statements
    await this.collection.createIndex(
      { accountNumber: 1, statementDate: 1 },
      { unique: true, name: 'unique_statement_idx' }
    );

    // Index for bank name queries
    await this.collection.createIndex(
      { bankName: 1, statementDate: -1 },
      { name: 'bank_date_idx' }
    );

    // Index for account holder
    await this.collection.createIndex(
      { accountHolder: 1 },
      { name: 'account_holder_idx' }
    );

    // Index for date queries
    await this.collection.createIndex(
      { statementDate: -1 },
      { name: 'date_idx' }
    );

    // Index for transaction dates
    await this.collection.createIndex(
      { 'transactions.date': 1 },
      { name: 'transaction_date_idx' }
    );

    console.log('✓ All indexes created\n');
  }

  normalizeData(data, filename) {
    // Parse dates safely
    const parseDate = (dateStr) => {
      if (!dateStr) return new Date();
      try {
        const date = new Date(dateStr);
        return isNaN(date.getTime()) ? new Date() : date;
      } catch {
        return new Date();
      }
    };

    // Extract bank name from filename
    let bankName = 'Unknown Bank';
    if (filename.includes('BOI_Statement') || filename.includes('boi_')) {
      bankName = 'Bank of India';
    } else if (filename.includes('AXIS_Statement') || filename.includes('axis_')) {
      bankName = 'AXIS Bank';
    } else if (filename.includes('HDFC') || filename.includes('hdfc')) {
      bankName = 'HDFC Bank';
    } else if (filename.includes('Central') || filename.includes('central')) {
      bankName = 'Central Bank';
    } else if (filename.includes('Union') || filename.includes('union')) {
      bankName = 'Union Bank';
    }

    // Extract account holder from filename
    const holderMatch = filename.match(/Statement_([A-Z_]+)_\d+/);
    const accountHolder = holderMatch ? 
      holderMatch[1].replace(/_/g, ' ').trim() : 
      data.accountHolder || 'Unknown';

    // Process transactions
    const transactions = this.processTransactions(data.transactions || []);

    // Build normalized document
    return {
      accountNumber: String(data.accountNumber || data.account_number || 'UNKNOWN'),
      bankName: bankName,
      accountHolder: accountHolder,
      statementDate: parseDate(data.statementDate || data.statement_date),
      statementPeriod: {
        from: parseDate(data.periodFrom || data.period_from || data.startDate),
        to: parseDate(data.periodTo || data.period_to || data.endDate)
      },
      openingBalance: parseFloat(data.openingBalance || data.opening_balance || 0),
      closingBalance: parseFloat(data.closingBalance || data.closing_balance || 0),
      totalCredits: parseFloat(data.totalCredits || data.total_credits || 0),
      totalDebits: parseFloat(data.totalDebits || data.total_debits || 0),
      currency: data.currency || 'INR',
      transactions: transactions,
      metadata: {
        importedAt: new Date(),
        sourceFile: filename,
        totalTransactions: transactions.length,
        dataSource: 'normalized_json'
      }
    };
  }

  processTransactions(transactions) {
    if (!Array.isArray(transactions)) return [];

    return transactions.map(tx => {
      const amount = parseFloat(tx.amount || tx.withdrawl || tx.deposit || 0);
      
      return {
        date: new Date(tx.date || tx.transaction_date || new Date()),
        description: String(tx.description || tx.particulars || tx.narration || 'No description'),
        amount: amount,
        type: (tx.type || '').toLowerCase() || (amount < 0 ? 'debit' : 'credit'),
        balance: parseFloat(tx.balance || tx.running_balance || 0),
        withdrawl: parseFloat(tx.withdrawl || 0),
        deposit: parseFloat(tx.deposit || 0),
        reference: String(tx.reference || tx.chq_no || tx.ref_no || ''),
        category: tx.category || 'uncategorized'
      };
    }).filter(tx => tx.amount !== 0 || tx.description !== 'No description');
  }

  async importFile(filePath, filename) {
    try {
      const content = await fs.readFile(filePath, 'utf8');
      const jsonData = JSON.parse(content);
      
      const normalized = this.normalizeData(jsonData, filename);
      
      await this.collection.insertOne(normalized);
      
      this.stats.inserted++;
      
      // Track by bank
      if (!this.stats.byBank[normalized.bankName]) {
        this.stats.byBank[normalized.bankName] = 0;
      }
      this.stats.byBank[normalized.bankName]++;
      
      console.log(`✓ ${this.stats.inserted}. Imported: ${filename}`);
      return { success: true };
    } catch (error) {
      if (error.code === 11000) {
        this.stats.duplicates++;
        console.log(`⚠ Duplicate: ${filename}`);
        return { success: false, reason: 'duplicate' };
      } else {
        this.stats.errors++;
        this.stats.errorDetails.push({
          file: filename,
          error: error.message
        });
        console.log(`✗ Error: ${filename} - ${error.message}`);
        return { success: false, reason: 'error', error: error.message };
      }
    }
  }

  async importFromDirectory(dirPath) {
    console.log('='.repeat(70));
    console.log(`📂 Importing from: ${dirPath}`);
    console.log('='.repeat(70) + '\n');

    try {
      const files = await fs.readdir(dirPath);
      const jsonFiles = files.filter(f => f.endsWith('.json'));

      this.stats.total = jsonFiles.length;
      console.log(`📄 Found ${jsonFiles.length} JSON files\n`);

      if (jsonFiles.length === 0) {
        console.log('❌ No JSON files found in directory!');
        return;
      }

      // Import files one by one
      for (const file of jsonFiles) {
        const filePath = path.join(dirPath, file);
        await this.importFile(filePath, file);
      }

      this.printSummary();
    } catch (error) {
      console.error('❌ Directory read error:', error.message);
      throw error;
    }
  }

  printSummary() {
    console.log('\n' + '='.repeat(70));
    console.log('📊 IMPORT SUMMARY');
    console.log('='.repeat(70));
    console.log(`Total files:             ${this.stats.total}`);
    console.log(`✓ Successfully inserted: ${this.stats.inserted}`);
    console.log(`⚠ Duplicates skipped:    ${this.stats.duplicates}`);
    console.log(`✗ Errors:                ${this.stats.errors}`);
    
    if (Object.keys(this.stats.byBank).length > 0) {
      console.log(`\n🏦 Statements by Bank:`);
      for (const [bank, count] of Object.entries(this.stats.byBank)) {
        console.log(`   ${bank}: ${count} statements`);
      }
    }

    if (this.stats.errorDetails.length > 0) {
      console.log(`\n❌ Error Details:`);
      this.stats.errorDetails.forEach(err => {
        console.log(`   - ${err.file}: ${err.error}`);
      });
    }
    console.log('='.repeat(70) + '\n');
  }

  async close() {
    if (this.client) {
      await this.client.close();
      console.log('✓ MongoDB connection closed\n');
    }
  }
}

// Main execution
async function main() {
  const importer = new NormalizedDataImporter();
  
  try {
    console.log('\n🚀 BankFusion - Normalized Data Import\n');
    
    // Connect to MongoDB
    await importer.connect();
    await importer.setupCollection();

    // Path to normalized_json folder (relative to this file)
    const normalizedPath = path.join(__dirname, '..', '..', 'data', 'normalized_json');
    
    console.log(`📁 Data folder: ${normalizedPath}\n`);
    
    // Check if directory exists
    try {
      await fs.access(normalizedPath);
    } catch (error) {
      console.error(`❌ Directory not found: ${normalizedPath}`);
      console.error('Please verify the path to your normalized_json folder');
      process.exit(1);
    }

    // Import all files
    await importer.importFromDirectory(normalizedPath);

    console.log('✅ Import completed successfully!\n');

  } catch (error) {
    console.error('❌ Import failed:', error.message);
    process.exit(1);
  } finally {
    await importer.close();
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { NormalizedDataImporter };