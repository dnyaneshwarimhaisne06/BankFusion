const { BankFusionDB } = require('./schema');

class BankStatementQueries {
  constructor(db) {
    this.db = db;
    this.statements = db.db.collection('bank_statements');
  }

  // Get database statistics
  async getStats() {
    const stats = await this.statements.aggregate([
      {
        $facet: {
          total: [{ $count: 'count' }],
          byBank: [
            { $group: { _id: '$bankName', count: { $sum: 1 } } },
            { $sort: { count: -1 } }
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
          ]
        }
      }
    ]).toArray();

    return stats[0];
  }

  // Query by bank
  async getByBank(bankName, limit = 50) {
    return await this.statements
      .find({ bankName: new RegExp(bankName, 'i') })
      .sort({ statementDate: -1 })
      .limit(limit)
      .toArray();
  }

  // Query by account number
  async getByAccount(accountNumber) {
    return await this.statements
      .find({ accountNumber: accountNumber })
      .sort({ statementDate: -1 })
      .toArray();
  }

  // Query by date range
  async getByDateRange(startDate, endDate) {
    return await this.statements
      .find({
        statementDate: {
          $gte: new Date(startDate),
          $lte: new Date(endDate)
        }
      })
      .sort({ statementDate: -1 })
      .toArray();
  }

  // Find transactions by amount
  async getTransactionsByAmount(minAmount, maxAmount, options = {}) {
    const pipeline = [
      { $unwind: '$transactions' },
      {
        $match: {
          'transactions.amount': {
            $gte: minAmount,
            $lte: maxAmount
          }
        }
      }
    ];

    if (options.bankName) {
      pipeline.unshift({ 
        $match: { bankName: new RegExp(options.bankName, 'i') } 
      });
    }

    pipeline.push(
      {
        $project: {
          accountNumber: 1,
          accountHolder: 1,
          bankName: 1,
          transaction: '$transactions'
        }
      },
      { $sort: { 'transaction.amount': -1 } }
    );

    if (options.limit) {
      pipeline.push({ $limit: options.limit });
    }

    return await this.statements.aggregate(pipeline).toArray();
  }

  // Search transactions by description
  async searchTransactions(searchTerm, limit = 20) {
    return await this.statements.aggregate([
      { $unwind: '$transactions' },
      {
        $match: {
          'transactions.description': new RegExp(searchTerm, 'i')
        }
      },
      {
        $project: {
          accountNumber: 1,
          accountHolder: 1,
          bankName: 1,
          transaction: '$transactions'
        }
      },
      { $limit: limit }
    ]).toArray();
  }

  // Get account summary
  async getAccountSummary(accountNumber) {
    const result = await this.statements.aggregate([
      { $match: { accountNumber: accountNumber } },
      { $unwind: '$transactions' },
      {
        $group: {
          _id: '$accountNumber',
          accountHolder: { $first: '$accountHolder' },
          bankName: { $first: '$bankName' },
          totalStatements: { $addToSet: '$_id' },
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
          maxTransaction: { $max: { $abs: '$transactions.amount' } },
          firstTransaction: { $min: '$transactions.date' },
          lastTransaction: { $max: '$transactions.date' }
        }
      },
      {
        $project: {
          accountNumber: '$_id',
          accountHolder: 1,
          bankName: 1,
          totalStatements: { $size: '$totalStatements' },
          totalTransactions: 1,
          totalCredits: { $round: ['$totalCredits', 2] },
          totalDebits: { $round: ['$totalDebits', 2] },
          avgTransaction: { $round: ['$avgTransaction', 2] },
          maxTransaction: { $round: ['$maxTransaction', 2] },
          firstTransaction: 1,
          lastTransaction: 1,
          _id: 0
        }
      }
    ]).toArray();

    return result[0];
  }
}

// Example queries
async function runExampleQueries() {
  const db = new BankFusionDB();

  try {
    await db.connect();
    const query = new BankStatementQueries(db);

    console.log('\n🔍 Running Example Queries...\n');

    // 1. Database statistics
    console.log('='.repeat(60));
    console.log('📊 DATABASE STATISTICS');
    console.log('='.repeat(60));
    const stats = await query.getStats();
    console.log(`Total Statements: ${stats.total[0]?.count || 0}`);
    console.log(`Total Transactions: ${stats.totalTransactions[0]?.count || 0}`);
    console.log(`\nBy Bank:`);
    stats.byBank.forEach(b => console.log(`  ${b._id}: ${b.count}`));
    if (stats.dateRange[0]) {
      console.log(`\nDate Range:`);
      console.log(`  ${stats.dateRange[0].earliest} to ${stats.dateRange[0].latest}`);
    }
    console.log('='.repeat(60) + '\n');

    // 2. Query AXIS Bank statements
    const axisStatements = await query.getByBank('AXIS', 5);
    console.log(`Found ${axisStatements.length} AXIS Bank statements\n`);

    // 3. Large transactions
    const largeTransactions = await query.getTransactionsByAmount(10000, 1000000, { limit: 5 });
    console.log(`Found ${largeTransactions.length} large transactions\n`);

  } catch (error) {
    console.error('❌ Query error:', error.message);
  } finally {
    await db.close();
  }
}

if (require.main === module) {
  runExampleQueries();
}

module.exports = { BankStatementQueries };