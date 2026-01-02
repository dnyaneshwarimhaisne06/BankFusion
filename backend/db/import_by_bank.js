// File: backend/db/import_by_bank.js
// Import normalized JSON data into separate collections per bank

const fs = require('fs').promises;
const path = require('path');
const { MongoClient } = require('mongodb');

const MONGO_URI = 'mongodb://localhost:27017';
const DB_NAME = 'bankfusion_db';

// Bank name mapping
const BANK_MAPPING = {
  'AXIS': 'axis_bank_statements',
  'BOI': 'boi_statements',
  'HDFC': 'hdfc_statements',
  'Central': 'central_bank_statements',
  'Union': 'union_bank_statements',
  'SBI': 'sbi_statements'
};

class BankWiseImporter {
  constructor() {
    this.client = null;
    this.db = null;
    this.stats = {
      total: 0,
      inserted: 0,
      duplicates: 0,
      errors: 0,
      byBank: {},
      errorDetails: []
    };
  }

  async connect() {
    try {
      this.client = new MongoClient(MONGO_URI);
      await this.client.connect();
      this.db = this.client.db(DB_NAME);
      console.log('✓ Connected to MongoDB');
      console.log(`✓ Database: ${DB_NAME}\n`);
      return this.db;
    } catch (error) {
      console.error('❌ MongoDB connection error:', error.message);
      throw error;
    }
  }

  // Detect bank from filename AND JSON data
  detectBank(filename, jsonData = null) {
    const upper = filename.toUpperCase();
    
    // Check filename first
    if (upper.includes('AXIS')) return 'AXIS';
    if (upper.includes('BOI_STATEMENT') || upper.includes('BOI')) return 'BOI';
    if (upper.includes('HDFC')) return 'HDFC';
    if (upper.includes('CENTRAL')) return 'Central';
    if (upper.includes('UNION')) return 'Union';
    if (upper.includes('SBI_STATEMENT') || upper.includes('SBI')) return 'SBI';
    
    // If no match in filename, check JSON data
    if (jsonData) {
      const bankName = (jsonData.bank_name || jsonData.bankName || '').toUpperCase();
      if (bankName.includes('AXIS')) return 'AXIS';
      if (bankName.includes('BOI') || bankName.includes('BANK OF INDIA')) return 'BOI';
      if (bankName.includes('HDFC')) return 'HDFC';
      if (bankName.includes('CENTRAL')) return 'Central';
      if (bankName.includes('UNION')) return 'Union';
      if (bankName.includes('SBI') || bankName.includes('STATE BANK')) return 'SBI';
    }
    
    return 'Unknown';
  }

  // Get collection name for bank
  getCollectionName(bank) {
    return BANK_MAPPING[bank] || 'unknown_bank_statements';
  }

  // Get full bank name
  getBankFullName(bank) {
    const names = {
      'AXIS': 'AXIS Bank',
      'BOI': 'Bank of India',
      'HDFC': 'HDFC Bank',
      'Central': 'Central Bank of India',
      'Union': 'Union Bank of India',
      'SBI': 'State Bank of India'
    };
    return names[bank] || 'Unknown Bank';
  }

  async setupCollection(collectionName, bankName) {
    try {
      const collections = await this.db.listCollections({ name: collectionName }).toArray();
      
      if (collections.length === 0) {
        await this.db.createCollection(collectionName);
        console.log(`✓ Created collection: ${collectionName}`);
      }

      const collection = this.db.collection(collectionName);

      // Drop existing indexes (except _id)
      try {
        const indexes = await collection.indexes();
        for (const index of indexes) {
          if (index.name !== '_id_') {
            await collection.dropIndex(index.name);
          }
        }
      } catch (error) {
        // Ignore if no indexes exist
      }

      // Create indexes
      await collection.createIndex(
        { accountNumber: 1, statementDate: 1 },
        { unique: true, name: 'unique_statement_idx' }
      );

      await collection.createIndex(
        { accountHolder: 1 },
        { name: 'account_holder_idx' }
      );

      await collection.createIndex(
        { statementDate: -1 },
        { name: 'date_idx' }
      );

      await collection.createIndex(
        { 'transactions.date': 1 },
        { name: 'transaction_date_idx' }
      );

      console.log(`✓ Indexes created for ${collectionName}\n`);
    } catch (error) {
      console.error(`❌ Setup error for ${collectionName}:`, error.message);
      throw error;
    }
  }

  // FIXED: Normalize transactions array
  normalizeTransactions(transactions) {
    if (!Array.isArray(transactions)) return [];

    return transactions.map(tx => {
      // Handle different field name variations
      const amount = parseFloat(
        tx.amount || 
        tx.withdrawl || 
        tx.withdrawal ||
        tx.deposit || 
        0
      );

      const txType = (
        tx.transaction_type || 
        tx.type || 
        tx.txType ||
        ''
      ).toUpperCase().trim();

      // Parse date safely
      let txDate;
      try {
        txDate = new Date(tx.date || tx.transaction_date || tx.txDate);
        if (isNaN(txDate.getTime())) {
          txDate = new Date();
        }
      } catch {
        txDate = new Date();
      }

      return {
        date: txDate,
        description: String(
          tx.description || 
          tx.particulars || 
          tx.narration || 
          tx.desc ||
          'No description'
        ).trim(),
        amount: amount,
        transaction_type: txType || (amount < 0 ? 'DEBIT' : 'CREDIT'),
        type: (txType || '').toLowerCase() || (amount < 0 ? 'debit' : 'credit'),
        balance: parseFloat(tx.balance || tx.running_balance || tx.runningBalance || 0),
        withdrawl: parseFloat(tx.withdrawl || tx.withdrawal || 0),
        deposit: parseFloat(tx.deposit || 0),
        reference: String(tx.reference || tx.chq_no || tx.ref_no || tx.refNo || '').trim(),
        category: tx.category || 'uncategorized'
      };
    });
  }

  normalizeStatement(data, filename) {
    // Parse JSON data to detect bank
    const detectedBank = this.detectBank(filename, data);
    const bankFullName = this.getBankFullName(detectedBank);

    // Parse dates safely
    const parseDate = (dateStr) => {
      if (!dateStr) return new Date();
      if (dateStr instanceof Date) return dateStr;
      try {
        const parsed = new Date(dateStr);
        return isNaN(parsed.getTime()) ? new Date() : parsed;
      } catch {
        return new Date();
      }
    };

    // Extract account holder - clean up any extra text
    let accountHolder = data.account_holder || data.accountHolder || data.holderName || data.holder_name;
    
    // If account holder contains "Interest Rate" or similar, clean it
    if (accountHolder && typeof accountHolder === 'string') {
      // Remove interest rate text like "Interest Rate(% p.a.) 3.25"
      accountHolder = accountHolder.replace(/Interest\s+Rate.*$/i, '').trim();
      // Remove trailing numbers and dots
      accountHolder = accountHolder.replace(/[\d.]+\s*$/, '').trim();
      // Remove Mr., Mrs., Miss. prefixes if needed
      accountHolder = accountHolder.replace(/^(Mr\.|Mrs\.|Miss\.)\s+/i, '').trim();
    }
    
    if (!accountHolder || accountHolder === '') {
      // Try to extract from filename
      const holderMatch = filename.match(/Statement_([A-Z_]+)_/);
      accountHolder = holderMatch ? holderMatch[1].replace(/_/g, ' ').trim() : 'Unknown';
    }

    // Process transactions - FIXED: Call the correct method
    const transactions = this.normalizeTransactions(data.transactions || []);

    // Calculate total credits and debits from transactions
    let totalCredits = 0;
    let totalDebits = 0;
    
    transactions.forEach(tx => {
      const txType = String(tx.transaction_type || '').toUpperCase().trim();
      const amount = Math.abs(parseFloat(tx.amount || 0));
      
      if (txType === 'CREDIT') {
        totalCredits += amount;
      } else if (txType === 'DEBIT') {
        totalDebits += amount;
      }
    });

    // Round to 2 decimal places
    totalCredits = Math.round(totalCredits * 100) / 100;
    totalDebits = Math.round(totalDebits * 100) / 100;

    console.log(`   📊 ${filename}: Credits=₹${totalCredits.toLocaleString('en-IN')}, Debits=₹${totalDebits.toLocaleString('en-IN')}`);

    // Extract account number with multiple fallbacks
    const accountNumber = String(
      data.account_number || 
      data.accountNumber || 
      data.accountNo ||
      data.account_no ||
      'UNKNOWN'
    ).trim();

    return {
      accountNumber: accountNumber,
      bankName: bankFullName,
      accountHolder: accountHolder,
      statementDate: parseDate(data.statement_date || data.statementDate),
      statementPeriod: data.statement_period || {
        from: parseDate(data.periodFrom || data.period_from || data.startDate || data.start_date),
        to: parseDate(data.periodTo || data.period_to || data.endDate || data.end_date)
      },
      openingBalance: parseFloat(data.openingBalance || data.opening_balance || 0),
      closingBalance: parseFloat(data.closingBalance || data.closing_balance || 0),
      totalCredits: totalCredits,
      totalDebits: totalDebits,
      currency: data.currency || 'INR',
      transactions: transactions,
      metadata: {
        importedAt: new Date(),
        sourceFile: filename,
        originalFileName: filename,
        totalTransactions: transactions.length,
        detectedBank: detectedBank
      }
    };
  }

  async importFile(filePath, filename, bank, collectionName) {
    try {
      const content = await fs.readFile(filePath, 'utf8');
      const jsonData = JSON.parse(content);
      
      const normalized = this.normalizeStatement(jsonData, filename);
      
      const collection = this.db.collection(collectionName);
      await collection.insertOne(normalized);
      
      this.stats.inserted++;
      
      if (!this.stats.byBank[bank]) {
        this.stats.byBank[bank] = 0;
      }
      this.stats.byBank[bank]++;
      
      console.log(`✓ ${this.stats.inserted}. [${bank}] ${filename}`);
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
        return { success: false, reason: 'error' };
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
        console.log('❌ No JSON files found!');
        return;
      }

      // Group files by bank - READ JSON to detect bank
      const filesByBank = {};
      for (const file of jsonFiles) {
        try {
          const filePath = path.join(dirPath, file);
          const content = await fs.readFile(filePath, 'utf8');
          const jsonData = JSON.parse(content);
          const bank = this.detectBank(file, jsonData);
          
          if (!filesByBank[bank]) {
            filesByBank[bank] = [];
          }
          filesByBank[bank].push(file);
        } catch (error) {
          console.log(`⚠ Error reading ${file}: ${error.message}`);
        }
      }

      console.log('📊 Files grouped by bank:');
      for (const [bank, files] of Object.entries(filesByBank)) {
        console.log(`   ${bank}: ${files.length} files`);
      }
      console.log();

      // Setup collections for each bank
      for (const bank of Object.keys(filesByBank)) {
        const collectionName = this.getCollectionName(bank);
        const bankFullName = this.getBankFullName(bank);
        console.log(`🔧 Setting up collection: ${collectionName} (${bankFullName})`);
        await this.setupCollection(collectionName, bankFullName);
      }

      // Import files bank by bank
      for (const [bank, files] of Object.entries(filesByBank)) {
        const collectionName = this.getCollectionName(bank);
        const bankFullName = this.getBankFullName(bank);
        
        console.log(`\n${'='.repeat(70)}`);
        console.log(`📥 Importing ${bank} - ${bankFullName}`);
        console.log(`📁 Collection: ${collectionName}`);
        console.log('='.repeat(70) + '\n');

        for (const file of files) {
          const filePath = path.join(dirPath, file);
          await this.importFile(filePath, file, bank, collectionName);
        }
      }

      this.printSummary();
    } catch (error) {
      console.error('❌ Import error:', error.message);
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
    
    console.log(`\n🏦 Documents by Bank (Collection):`);
    for (const [bank, count] of Object.entries(this.stats.byBank)) {
      const collectionName = this.getCollectionName(bank);
      const bankFullName = this.getBankFullName(bank);
      console.log(`   ${bankFullName} → ${collectionName}: ${count} documents`);
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

async function main() {
  const importer = new BankWiseImporter();
  
  try {
    console.log('\n🚀 BankFusion - Import to Separate Bank Collections\n');
    
    await importer.connect();

    // Path to normalized_json folder
    const normalizedPath = path.join(__dirname, '..', '..', 'data', 'normalized_json');
    
    console.log(`📁 Data folder: ${normalizedPath}\n`);
    
    // Check if directory exists
    try {
      await fs.access(normalizedPath);
    } catch (error) {
      console.error(`❌ Directory not found: ${normalizedPath}`);
      console.log('\n💡 Trying alternative paths...\n');
      
      // Try alternative paths
      const altPaths = [
        path.join(__dirname, '..', 'data', 'normalized_json'),
        path.join(__dirname, '..', '..', '..', 'data', 'normalized_json'),
        path.join(process.cwd(), 'data', 'normalized_json')
      ];
      
      let foundPath = null;
      for (const altPath of altPaths) {
        try {
          await fs.access(altPath);
          foundPath = altPath;
          console.log(`✓ Found data at: ${altPath}\n`);
          break;
        } catch {
          // Continue trying
        }
      }
      
      if (!foundPath) {
        console.error('❌ Could not find normalized_json folder');
        console.log('\n📁 Current directory:', __dirname);
        console.log('📁 Working directory:', process.cwd());
        process.exit(1);
      }
      
      await importer.importFromDirectory(foundPath);
      await importer.close();
      return;
    }

    await importer.importFromDirectory(normalizedPath);

    console.log('✅ Import completed successfully!\n');
    console.log('💡 You can now see data in MongoDB Compass:');
    console.log('   - axis_bank_statements');
    console.log('   - boi_statements');
    console.log('   - hdfc_statements');
    console.log('   - central_bank_statements');
    console.log('   - union_bank_statements');
    console.log('   - sbi_statements\n');

  } catch (error) {
    console.error('❌ Import failed:', error.message);
    console.error(error.stack);
    process.exit(1);
  } finally {
    await importer.close();
  }
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = { BankWiseImporter };
