const fs = require('fs').promises;
const path = require('path');
const { BankFusionDB } = require('./schema');

class StatementImporter {
  constructor(db) {
    this.db = db;
    this.stats = {
      total: 0,
      inserted: 0,
      duplicates: 0,
      errors: 0,
      errorDetails: [],
      byBank: {}
    };
  }

  // Normalize extracted JSON data
  normalizeStatement(data, filename) {
    // Extract bank name from filename
    const bankName = filename.includes('AXIS') ? 'AXIS Bank' : 
                     filename.includes('BOI') ? 'Bank of India' : 
                     'Unknown Bank';
    
    // Extract account holder name from filename
    const holderMatch = filename.match(/Statement_([A-Z_]+)_/);
    const accountHolder = holderMatch ? 
                         holderMatch[1].replace(/_/g, ' ') : 
                         'Unknown';

    // Parse dates safely
    const parseDate = (dateStr) => {
      if (!dateStr) return new Date();
      try {
        return new Date(dateStr);
      } catch {
        return new Date();
      }
    };

    // Extract account number
    const accountNumber = data.accountNumber || 
                         data.account_number || 
                         data.accountNo ||
                         filename.match(/\d{10,}/)?.[0] ||
                         'UNKNOWN';

    // Process transactions
    const transactions = this.normalizeTransactions(data.transactions || []);

    return {
      accountNumber: String(accountNumber),
      bankName: bankName,
      accountHolder: accountHolder,
      statementDate: parseDate(data.statementDate || data.date),
      statementPeriod: {
        from: parseDate(data.periodFrom || data.startDate),
        to: parseDate(data.periodTo || data.endDate)
      },
      openingBalance: parseFloat(data.openingBalance || 0),
      closingBalance: parseFloat(data.closingBalance || 0),
      totalCredits: parseFloat(data.totalCredits || 0),
      totalDebits: parseFloat(data.totalDebits || 0),
      currency: data.currency || 'INR',
      transactions: transactions,
      metadata: {
        importedAt: new Date(),
        sourceFile: filename,
        originalFileName: filename,
        totalTransactions: transactions.length
      }
    };
  }

  normalizeTransactions(transactions) {
    if (!Array.isArray(transactions)) return [];
    
    return transactions.map(tx => {
      const amount = parseFloat(tx.amount || tx.withdrawl || tx.deposit || 0);
      
      return {
        date: new Date(tx.date || tx.transaction_date || new Date()),
        description: String(tx.description || tx.particulars || tx.narration || 'No description'),
        amount: amount,
        type: tx.type || (amount < 0 ? 'debit' : 'credit'),
        balance: parseFloat(tx.balance || tx.running_balance || 0),
        withdrawl: parseFloat(tx.withdrawl || 0),
        deposit: parseFloat(tx.deposit || 0),
        reference: tx.reference || tx.chq_no || tx.ref_no || ''
      };
    });
  }

  async importStatement(jsonData, filename) {
    try {
      const normalized = this.normalizeStatement(jsonData, filename);
      const statements = this.db.db.collection('bank_statements');

      await statements.insertOne(normalized);
      
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
        return { success: false, reason: 'error' };
      }
    }
  }

  async importFromDirectory(dirPath) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`📂 Importing from: ${dirPath}`);
    console.log(`${'='.repeat(60)}\n`);

    try {
      const files = await fs.readdir(dirPath);
      const jsonFiles = files.filter(f => f.endsWith('.json'));

      this.stats.total = jsonFiles.length;
      console.log(`📄 Found ${jsonFiles.length} JSON files\n`);

      if (jsonFiles.length === 0) {
        console.log('❌ No JSON files found!');
        return;
      }

      // Process files
      for (const file of jsonFiles) {
        try {
          const filePath = path.join(dirPath, file);
          const content = await fs.readFile(filePath, 'utf8');
          const jsonData = JSON.parse(content);
          
          await this.importStatement(jsonData, file);
        } catch (error) {
          this.stats.errors++;
          console.log(`✗ Failed: ${file} - ${error.message}`);
        }
      }

      this.printSummary();
    } catch (error) {
      console.error('❌ Directory read error:', error.message);
      throw error;
    }
  }

  printSummary() {
    console.log(`\n${'='.repeat(60)}`);
    console.log('📊 IMPORT SUMMARY');
    console.log(`${'='.repeat(60)}`);
    console.log(`Total files:           ${this.stats.total}`);
    console.log(`✓ Successfully inserted: ${this.stats.inserted}`);
    console.log(`⚠ Duplicates skipped:   ${this.stats.duplicates}`);
    console.log(`✗ Errors:               ${this.stats.errors}`);
    
    console.log(`\n🏦 By Bank:`);
    for (const [bank, count] of Object.entries(this.stats.byBank)) {
      console.log(`   ${bank}: ${count} statements`);
    }

    if (this.stats.errorDetails.length > 0) {
      console.log(`\n❌ Error Details:`);
      this.stats.errorDetails.forEach(err => {
        console.log(`   - ${err.file}: ${err.error}`);
      });
    }
    console.log(`${'='.repeat(60)}\n`);
  }
}

// Main execution
async function main() {
  const db = new BankFusionDB();
  
  try {
    console.log('\n🚀 BankFusion MongoDB Import Script\n');
    
    await db.connect();
    await db.setupCollections();

    const importer = new StatementImporter(db);

    // Import from extracted_json folder
    const extractedPath = path.join(__dirname, '..', 'data', 'extracted_json');
    await importer.importFromDirectory(extractedPath);

  } catch (error) {
    console.error('❌ Import failed:', error.message);
    process.exit(1);
  } finally {
    await db.close();
  }
}

// Run import
if (require.main === module) {
  main();
}

module.exports = { StatementImporter };