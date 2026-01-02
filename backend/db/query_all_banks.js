// File: backend/db/query_all_banks.js
// Query data from separate bank collections

const { MongoClient } = require('mongodb');

const MONGO_URI = 'mongodb://localhost:27017';
const DB_NAME = 'bankfusion_db';

const BANK_COLLECTIONS = {
  'AXIS Bank': 'axis_bank_statements',
  'Bank of India': 'boi_statements',
  'HDFC Bank': 'hdfc_statements',
  'Central Bank': 'central_bank_statements',
  'Union Bank': 'union_bank_statements',
  'SBI': 'sbi_statements'
};

class MultiBankQueries {
  constructor() {
    this.client = null;
    this.db = null;
  }

  async connect() {
    try {
      this.client = new MongoClient(MONGO_URI);
      await this.client.connect();
      this.db = this.client.db(DB_NAME);
      console.log('✓ Connected to MongoDB\n');
      return this.db;
    } catch (error) {
      console.error('❌ Connection error:', error.message);
      throw error;
    }
  }

  // Get statistics for all banks
  async getAllBanksStatistics() {
    console.log('='.repeat(70));
    console.log('📊 ALL BANKS STATISTICS');
    console.log('='.repeat(70) + '\n');

    const bankStats = [];
    let totalStatements = 0;
    let totalTransactions = 0;

    for (const [bankName, collectionName] of Object.entries(BANK_COLLECTIONS)) {
      try {
        const collection = this.db.collection(collectionName);
        
        const count = await collection.countDocuments();
        
        if (count === 0) continue;

        const stats = await collection.aggregate([
          {
            $facet: {
              totalTransactions: [
                { $unwind: '$transactions' },
                { $count: 'count' }
              ],
              financialSummary: [
                {
                  $group: {
                    _id: null,
                    totalBalance: { $sum: '$closingBalance' },
                    totalCredits: { $sum: '$totalCredits' },
                    totalDebits: { $sum: '$totalDebits' }
                  }
                }
              ],
              accountHolders: [
                { $group: { _id: '$accountHolder' } },
                { $count: 'count' }
              ]
            }
          }
        ]).toArray();

        const result = stats[0];
        
        bankStats.push({
          bankName,
          collectionName,
          statements: count,
          transactions: result.totalTransactions[0]?.count || 0,
          accountHolders: result.accountHolders[0]?.count || 0,
          financial: result.financialSummary[0] || {}
        });

        totalStatements += count;
        totalTransactions += result.totalTransactions[0]?.count || 0;

      } catch (error) {
        console.log(`⚠ Collection ${collectionName} not found or empty`);
      }
    }

    console.log(`📈 Overall Summary:`);
    console.log(`   Total Banks: ${bankStats.length}`);
    console.log(`   Total Statements: ${totalStatements}`);
    console.log(`   Total Transactions: ${totalTransactions}\n`);

    console.log('🏦 Bank-wise Breakdown:\n');
    bankStats.forEach(stat => {
      console.log(`📁 ${stat.bankName} (${stat.collectionName})`);
      console.log(`   Statements: ${stat.statements}`);
      console.log(`   Transactions: ${stat.transactions}`);
      console.log(`   Account Holders: ${stat.accountHolders}`);
      if (stat.financial.totalBalance) {
        console.log(`   Total Balance: ₹${stat.financial.totalBalance.toLocaleString('en-IN')}`);
        console.log(`   Total Credits: ₹${stat.financial.totalCredits.toLocaleString('en-IN')}`);
        console.log(`   Total Debits: ₹${stat.financial.totalDebits.toLocaleString('en-IN')}`);
      }
      console.log();
    });

    console.log('='.repeat(70) + '\n');
    return bankStats;
  }

  // Query specific bank
  async queryBank(bankName, limit = 10) {
    const collectionName = BANK_COLLECTIONS[bankName];
    
    if (!collectionName) {
      console.log(`❌ Unknown bank: ${bankName}`);
      console.log(`Available banks: ${Object.keys(BANK_COLLECTIONS).join(', ')}`);
      return [];
    }

    console.log(`\n🔍 Querying ${bankName}`);
    console.log(`📁 Collection: ${collectionName}`);
    console.log('-'.repeat(70));

    try {
      const collection = this.db.collection(collectionName);
      const statements = await collection
        .find({})
        .sort({ statementDate: -1 })
        .limit(limit)
        .toArray();

      console.log(`\nFound ${statements.length} statements:\n`);
      
      statements.forEach((stmt, idx) => {
        console.log(`${idx + 1}. ${stmt.accountHolder}`);
        console.log(`   Account: ${stmt.accountNumber}`);
        console.log(`   Date: ${new Date(stmt.statementDate).toLocaleDateString()}`);
        console.log(`   Balance: ₹${stmt.closingBalance.toLocaleString('en-IN')}`);
        console.log(`   Transactions: ${stmt.transactions.length}`);
        console.log();
      });

      return statements;
    } catch (error) {
      console.error(`❌ Query error: ${error.message}`);
      return [];
    }
  }

  // Search across all banks
  async searchAccountHolder(name) {
    console.log(`\n🔍 Searching for account holder: "${name}"`);
    console.log('='.repeat(70) + '\n');

    const results = [];

    for (const [bankName, collectionName] of Object.entries(BANK_COLLECTIONS)) {
      try {
        const collection = this.db.collection(collectionName);
        const statements = await collection
          .find({ accountHolder: new RegExp(name, 'i') })
          .toArray();

        if (statements.length > 0) {
          results.push({ bankName, statements });
        }
      } catch (error) {
        // Collection doesn't exist, skip
      }
    }

    if (results.length === 0) {
      console.log('❌ No results found\n');
      return [];
    }

    results.forEach(result => {
      console.log(`🏦 ${result.bankName}: ${result.statements.length} statements`);
      result.statements.forEach(stmt => {
        console.log(`   - ${stmt.accountHolder} (${stmt.accountNumber})`);
        console.log(`     Date: ${new Date(stmt.statementDate).toLocaleDateString()}`);
        console.log(`     Balance: ₹${stmt.closingBalance.toLocaleString('en-IN')}`);
      });
      console.log();
    });

    return results;
  }

  // Find large transactions across all banks
  async findLargeTransactions(minAmount = 50000, limit = 20) {
    console.log(`\n💰 Finding transactions above ₹${minAmount.toLocaleString('en-IN')} across all banks`);
    console.log('='.repeat(70) + '\n');

    const allTransactions = [];

    for (const [bankName, collectionName] of Object.entries(BANK_COLLECTIONS)) {
      try {
        const collection = this.db.collection(collectionName);
        const results = await collection.aggregate([
          { $unwind: '$transactions' },
          {
            $match: {
              $or: [
                { 'transactions.amount': { $gte: minAmount } },
                { 'transactions.amount': { $lte: -minAmount } }
              ]
            }
          },
          {
            $project: {
              accountHolder: 1,
              bankName: { $literal: bankName },
              transaction: '$transactions',
              absAmount: { $abs: '$transactions.amount' }
            }
          },
          { $sort: { absAmount: -1 } }
        ]).toArray();

        allTransactions.push(...results);
      } catch (error) {
        // Collection doesn't exist, skip
      }
    }

    // Sort all transactions by amount
    allTransactions.sort((a, b) => b.absAmount - a.absAmount);
    const topTransactions = allTransactions.slice(0, limit);

    console.log(`Found ${topTransactions.length} large transactions:\n`);
    
    topTransactions.forEach((r, idx) => {
      const tx = r.transaction;
      console.log(`${idx + 1}. ₹${Math.abs(tx.amount).toLocaleString('en-IN')} (${tx.type})`);
      console.log(`   Bank: ${r.bankName}`);
      console.log(`   Account: ${r.accountHolder}`);
      console.log(`   Date: ${new Date(tx.date).toLocaleDateString()}`);
      console.log(`   Description: ${tx.description.substring(0, 60)}...`);
      console.log();
    });

    return topTransactions;
  }

  // Compare account holders across banks
  async compareAccountHolder(name) {
    console.log(`\n📊 Comparing ${name} across banks`);
    console.log('='.repeat(70) + '\n');

    const comparison = [];

    for (const [bankName, collectionName] of Object.entries(BANK_COLLECTIONS)) {
      try {
        const collection = this.db.collection(collectionName);
        const summary = await collection.aggregate([
          { $match: { accountHolder: new RegExp(name, 'i') } },
          { $unwind: '$transactions' },
          {
            $group: {
              _id: null,
              bankName: { $first: { $literal: bankName } },
              statements: { $addToSet: '$_id' },
              totalTransactions: { $sum: 1 },
              totalCredits: {
                $sum: {
                  $cond: [{ $gte: ['$transactions.amount', 0] }, '$transactions.amount', 0]
                }
              },
              totalDebits: {
                $sum: {
                  $cond: [{ $lt: ['$transactions.amount', 0] }, { $abs: '$transactions.amount' }, 0]
                }
              }
            }
          }
        ]).toArray();

        if (summary.length > 0) {
          comparison.push(summary[0]);
        }
      } catch (error) {
        // Skip
      }
    }

    if (comparison.length === 0) {
      console.log('❌ No data found for this account holder\n');
      return [];
    }

    comparison.forEach(bank => {
      console.log(`🏦 ${bank.bankName}`);
      console.log(`   Statements: ${bank.statements.length}`);
      console.log(`   Transactions: ${bank.totalTransactions}`);
      console.log(`   Total Credits: ₹${bank.totalCredits.toLocaleString('en-IN')}`);
      console.log(`   Total Debits: ₹${bank.totalDebits.toLocaleString('en-IN')}`);
      console.log();
    });

    return comparison;
  }

  async close() {
    if (this.client) {
      await this.client.close();
      console.log('✓ Connection closed\n');
    }
  }
}

// Example queries
async function main() {
  const queries = new MultiBankQueries();

  try {
    console.log('\n🚀 BankFusion - Multi-Bank Query Examples\n');
    
    await queries.connect();

    // 1. Get statistics for all banks
    await queries.getAllBanksStatistics();

    // 2. Query specific bank
    await queries.queryBank('AXIS Bank', 5);
    await queries.queryBank('Bank of India', 5);

    // 3. Find large transactions across all banks
    await queries.findLargeTransactions(50000, 10);

    // 4. Search for account holder (uncomment and replace with actual name)
    // await queries.searchAccountHolder('AARAV');

    // 5. Compare account holder across banks (uncomment and replace with actual name)
    // await queries.compareAccountHolder('AARAV MEHTA');

    console.log('✅ All queries completed!\n');

  } catch (error) {
    console.error('❌ Query execution failed:', error.message);
    process.exit(1);
  } finally {
    await queries.close();
  }
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = { MultiBankQueries };