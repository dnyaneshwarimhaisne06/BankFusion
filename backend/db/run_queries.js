// File: backend/db/run_queries.js
// Query and analyze imported bank statement data

const { MongoClient } = require('mongodb');

const MONGO_URI = 'mongodb://localhost:27017';
const DB_NAME = 'bankfusion_db';
const COLLECTION_NAME = 'bank_statements';

class BankStatementQueries {
  constructor() {
    this.client = null;
    this.db = null;
    this.collection = null;
  }

  async connect() {
    try {
      this.client = new MongoClient(MONGO_URI);
      await this.client.connect();
      this.db = this.client.db(DB_NAME);
      this.collection = this.db.collection(COLLECTION_NAME);
      console.log('✓ Connected to MongoDB\n');
      return this.db;
    } catch (error) {
      console.error('❌ Connection error:', error.message);
      throw error;
    }
  }

  // Get overall database statistics
  async getStatistics() {
    console.log('='.repeat(70));
    console.log('📊 DATABASE STATISTICS');
    console.log('='.repeat(70));

    try {
      const stats = await this.collection.aggregate([
        {
          $facet: {
            totalStatements: [{ $count: 'count' }],
            byBank: [
              { $group: { _id: '$bankName', count: { $sum: 1 } } },
              { $sort: { count: -1 } }
            ],
            byAccountHolder: [
              { $group: { _id: '$accountHolder', count: { $sum: 1 } } },
              { $sort: { count: -1 } },
              { $limit: 10 }
            ],
            dateRange: [
              {
                $group: {
                  _id: null,
                  earliest: { $min: '$statementDate' },
                  latest: { $max: '$statementDate' }
                }
              }
            ],
            totalTransactions: [
              { $unwind: '$transactions' },
              { $count: 'count' }
            ],
            financialSummary: [
              {
                $group: {
                  _id: null,
                  totalOpeningBalance: { $sum: '$openingBalance' },
                  totalClosingBalance: { $sum: '$closingBalance' },
                  totalCredits: { $sum: '$totalCredits' },
                  totalDebits: { $sum: '$totalDebits' }
                }
              }
            ]
          }
        }
      ]).toArray();

      const result = stats[0];

      console.log(`\n📈 Overview:`);
      console.log(`   Total Statements: ${result.totalStatements[0]?.count || 0}`);
      console.log(`   Total Transactions: ${result.totalTransactions[0]?.count || 0}`);

      console.log(`\n🏦 Statements by Bank:`);
      result.byBank.forEach(b => {
        console.log(`   ${b._id}: ${b.count} statements`);
      });

      console.log(`\n👥 Top Account Holders:`);
      result.byAccountHolder.slice(0, 5).forEach((holder, idx) => {
        console.log(`   ${idx + 1}. ${holder._id}: ${holder.count} statements`);
      });

      if (result.dateRange[0]) {
        console.log(`\n📅 Date Range:`);
        console.log(`   From: ${new Date(result.dateRange[0].earliest).toLocaleDateString()}`);
        console.log(`   To:   ${new Date(result.dateRange[0].latest).toLocaleDateString()}`);
      }

      if (result.financialSummary[0]) {
        const fs = result.financialSummary[0];
        console.log(`\n💰 Financial Summary:`);
        console.log(`   Total Opening Balance: ₹${fs.totalOpeningBalance.toLocaleString('en-IN')}`);
        console.log(`   Total Closing Balance: ₹${fs.totalClosingBalance.toLocaleString('en-IN')}`);
        console.log(`   Total Credits: ₹${fs.totalCredits.toLocaleString('en-IN')}`);
        console.log(`   Total Debits: ₹${fs.totalDebits.toLocaleString('en-IN')}`);
      }

      console.log('='.repeat(70) + '\n');

      return result;
    } catch (error) {
      console.error('❌ Statistics error:', error.message);
      throw error;
    }
  }

  // Query by bank name
  async getByBank(bankName, limit = 10) {
    console.log(`\n🔍 Querying statements for: ${bankName}`);
    console.log('-'.repeat(70));

    try {
      const statements = await this.collection
        .find({ bankName: new RegExp(bankName, 'i') })
        .sort({ statementDate: -1 })
        .limit(limit)
        .toArray();

      console.log(`Found ${statements.length} statements:\n`);
      
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
      console.error('❌ Query error:', error.message);
      throw error;
    }
  }

  // Query by account holder
  async getByAccountHolder(holderName) {
    console.log(`\n🔍 Querying statements for: ${holderName}`);
    console.log('-'.repeat(70));

    try {
      const statements = await this.collection
        .find({ accountHolder: new RegExp(holderName, 'i') })
        .sort({ statementDate: -1 })
        .toArray();

      console.log(`Found ${statements.length} statements:\n`);
      
      statements.forEach((stmt, idx) => {
        console.log(`${idx + 1}. ${stmt.bankName}`);
        console.log(`   Date: ${new Date(stmt.statementDate).toLocaleDateString()}`);
        console.log(`   Opening: ₹${stmt.openingBalance.toLocaleString('en-IN')}`);
        console.log(`   Closing: ₹${stmt.closingBalance.toLocaleString('en-IN')}`);
        console.log(`   Transactions: ${stmt.transactions.length}`);
        console.log();
      });

      return statements;
    } catch (error) {
      console.error('❌ Query error:', error.message);
      throw error;
    }
  }

  // Find large transactions
  async getLargeTransactions(minAmount = 10000, limit = 20) {
    console.log(`\n💰 Finding transactions above ₹${minAmount.toLocaleString('en-IN')}`);
    console.log('-'.repeat(70));

    try {
      const results = await this.collection.aggregate([
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
            bankName: 1,
            transaction: '$transactions',
            absAmount: { $abs: '$transactions.amount' }
          }
        },
        { $sort: { absAmount: -1 } },
        { $limit: limit }
      ]).toArray();

      console.log(`Found ${results.length} large transactions:\n`);
      
      results.forEach((r, idx) => {
        const tx = r.transaction;
        console.log(`${idx + 1}. ₹${Math.abs(tx.amount).toLocaleString('en-IN')} (${tx.type})`);
        console.log(`   Account: ${r.accountHolder} - ${r.bankName}`);
        console.log(`   Date: ${new Date(tx.date).toLocaleDateString()}`);
        console.log(`   Description: ${tx.description.substring(0, 60)}...`);
        console.log();
      });

      return results;
    } catch (error) {
      console.error('❌ Query error:', error.message);
      throw error;
    }
  }

  // Search transactions by description
  async searchTransactions(keyword, limit = 15) {
    console.log(`\n🔍 Searching transactions for: "${keyword}"`);
    console.log('-'.repeat(70));

    try {
      const results = await this.collection.aggregate([
        { $unwind: '$transactions' },
        {
          $match: {
            'transactions.description': new RegExp(keyword, 'i')
          }
        },
        {
          $project: {
            accountHolder: 1,
            bankName: 1,
            transaction: '$transactions'
          }
        },
        { $limit: limit }
      ]).toArray();

      console.log(`Found ${results.length} matching transactions:\n`);
      
      results.forEach((r, idx) => {
        const tx = r.transaction;
        console.log(`${idx + 1}. ${tx.description}`);
        console.log(`   Amount: ₹${tx.amount.toLocaleString('en-IN')} (${tx.type})`);
        console.log(`   Account: ${r.accountHolder}`);
        console.log(`   Date: ${new Date(tx.date).toLocaleDateString()}`);
        console.log();
      });

      return results;
    } catch (error) {
      console.error('❌ Search error:', error.message);
      throw error;
    }
  }

  // Get account summary
  async getAccountSummary(accountNumber) {
    console.log(`\n📊 Account Summary: ${accountNumber}`);
    console.log('-'.repeat(70));

    try {
      const summary = await this.collection.aggregate([
        { $match: { accountNumber: accountNumber } },
        { $unwind: '$transactions' },
        {
          $group: {
            _id: '$accountNumber',
            accountHolder: { $first: '$accountHolder' },
            bankName: { $first: '$bankName' },
            statements: { $addToSet: '$_id' },
            totalTransactions: { $sum: 1 },
            totalCredits: {
              $sum: {
                $cond: [
                  { $gte: ['$transactions.amount', 0] },
                  '$transactions.amount',
                  0
                ]
              }
            },
            totalDebits: {
              $sum: {
                $cond: [
                  { $lt: ['$transactions.amount', 0] },
                  { $abs: '$transactions.amount' },
                  0
                ]
              }
            },
            avgTransaction: { $avg: { $abs: '$transactions.amount' } },
            maxTransaction: { $max: { $abs: '$transactions.amount' } }
          }
        }
      ]).toArray();

      if (summary.length === 0) {
        console.log('❌ Account not found\n');
        return null;
      }

      const s = summary[0];
      console.log(`\nAccount Holder: ${s.accountHolder}`);
      console.log(`Bank: ${s.bankName}`);
      console.log(`Total Statements: ${s.statements.length}`);
      console.log(`Total Transactions: ${s.totalTransactions}`);
      console.log(`Total Credits: ₹${s.totalCredits.toLocaleString('en-IN')}`);
      console.log(`Total Debits: ₹${s.totalDebits.toLocaleString('en-IN')}`);
      console.log(`Average Transaction: ₹${s.avgTransaction.toLocaleString('en-IN')}`);
      console.log(`Largest Transaction: ₹${s.maxTransaction.toLocaleString('en-IN')}`);
      console.log();

      return s;
    } catch (error) {
      console.error('❌ Summary error:', error.message);
      throw error;
    }
  }

  async close() {
    if (this.client) {
      await this.client.close();
      console.log('✓ Connection closed\n');
    }
  }
}

// Main execution - run example queries
async function main() {
  const queries = new BankStatementQueries();

  try {
    console.log('\n🚀 BankFusion - Query Examples\n');
    
    await queries.connect();

    // 1. Get overall statistics
    await queries.getStatistics();

    // 2. Query BOI statements
    await queries.getByBank('Bank of India', 5);

    // 3. Query AXIS statements
    await queries.getByBank('AXIS', 5);

    // 4. Find large transactions
    await queries.getLargeTransactions(50000, 10);

    // 5. Search for salary transactions
    await queries.searchTransactions('salary', 5);

    console.log('✅ All queries completed!\n');

  } catch (error) {
    console.error('❌ Query execution failed:', error.message);
    process.exit(1);
  } finally {
    await queries.close();
  }
}

// Run queries
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { BankStatementQueries };