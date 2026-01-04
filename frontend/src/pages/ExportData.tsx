import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useAuth } from '@/contexts/AuthContext';
import { flaskApi, Statement as ApiStatement, Transaction as ApiTransaction } from '@/lib/api/flask-api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { 
  Loader2, 
  Download, 
  FileJson, 
  FileText, 
  Building2,
  Calendar,
  FileDown,
  Sparkles
} from 'lucide-react';
import { format } from 'date-fns';
import { safeFormatDate } from '@/lib/utils';
import { formatINR } from '@/lib/currency';
import { toast } from 'sonner';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

interface Statement {
  id: string;
  bank_name: string;
  file_name: string;
  upload_date: string;
}

interface Transaction {
  id: string;
  date: string;
  description: string;
  debit: number | null;
  credit: number | null;
  balance: number | null;
  category: string | null;
}

export default function ExportData() {
  const { user } = useAuth();
  const [statements, setStatements] = useState<Statement[]>([]);
  const [selectedStatement, setSelectedStatement] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);

  useEffect(() => {
      fetchStatements();
  }, []);

  const fetchStatements = async () => {
    try {
      const result = await flaskApi.getStatements();
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch statements');
      }

      const transformed = (result.data || []).map(s => ({
        id: s._id,
        bank_name: s.bankType || 'Unknown',
        file_name: s.fileName || 'Untitled',
        upload_date: s.uploadDate || s.createdAt || '',
      }));
      
      setStatements(transformed);
      if (transformed.length > 0) {
        setSelectedStatement(transformed[0].id);
      }
    } catch (error: any) {
      console.error('Error fetching statements:', error);
      toast.error(error.message || 'Failed to load statements');
    } finally {
      setLoading(false);
    }
  };

  const fetchTransactionsForStatement = async (statementId: string): Promise<Transaction[]> => {
    const result = await flaskApi.getTransactionsByStatement(statementId);
    
    if (!result.success) {
      throw new Error(result.error || 'Failed to fetch transactions');
    }

    const apiTransactions = result.data || [];
    
    // Convert MongoDB format (amount + direction) to debit/credit
    return apiTransactions.map((tx: ApiTransaction) => {
      let debit: number | null = null;
      let credit: number | null = null;
      
      if (tx.amount !== undefined && tx.direction) {
        const amount = Number(tx.amount) || 0;
        const direction = tx.direction.toLowerCase();
        if (direction === 'debit') {
          debit = amount;
        } else {
          credit = amount;
        }
      } else {
        debit = tx.debit !== undefined && tx.debit !== null ? Number(tx.debit) : null;
        credit = tx.credit !== undefined && tx.credit !== null ? Number(tx.credit) : null;
      }
      
      return {
        id: tx._id,
        date: tx.date,
        description: tx.description || '',
        debit,
        credit,
        balance: tx.balance,
        category: tx.category,
      };
    });
  };

  const downloadJSON = (data: object, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExportNormalizedJSON = async () => {
    if (!selectedStatement) return;
    
    setExporting('normalized');
    try {
      const statement = statements.find(s => s.id === selectedStatement);
      const transactions = await fetchTransactionsForStatement(selectedStatement);
      
      const normalizedData = {
        statement: {
          id: statement?.id,
          bank_name: statement?.bank_name,
          file_name: statement?.file_name,
          upload_date: statement?.upload_date,
        },
        transactions: transactions.map(t => ({
          date: t.date,
          description: t.description,
          debit: t.debit || 0,
          credit: t.credit || 0,
          balance: t.balance || 0,
        })),
        metadata: {
          exported_at: new Date().toISOString(),
          total_transactions: transactions.length,
        }
      };

      downloadJSON(normalizedData, `${statement?.bank_name}_normalized_${format(new Date(), 'yyyy-MM-dd')}.json`);
      toast.success('Normalized JSON exported successfully');
    } catch (error) {
      console.error('Error exporting:', error);
      toast.error('Failed to export data');
    } finally {
      setExporting(null);
    }
  };

  const handleExportCategorizedJSON = async () => {
    if (!selectedStatement) return;
    
    setExporting('categorized');
    try {
      const statement = statements.find(s => s.id === selectedStatement);
      const transactions = await fetchTransactionsForStatement(selectedStatement);
      
      // Group by category
      const categoryMap = new Map<string, Transaction[]>();
      transactions.forEach(t => {
        const category = t.category || 'Uncategorized';
        if (!categoryMap.has(category)) {
          categoryMap.set(category, []);
        }
        categoryMap.get(category)!.push(t);
      });

      const categorizedData = {
        statement: {
          id: statement?.id,
          bank_name: statement?.bank_name,
          file_name: statement?.file_name,
          upload_date: statement?.upload_date,
        },
        categories: Object.fromEntries(
          Array.from(categoryMap.entries()).map(([category, txns]) => [
            category,
            {
              transactions: txns.map(t => ({
                date: t.date,
                description: t.description,
                debit: t.debit || 0,
                credit: t.credit || 0,
                balance: t.balance || 0,
              })),
              summary: {
                total_debit: txns.reduce((sum, t) => sum + (Number(t.debit) || 0), 0),
                total_credit: txns.reduce((sum, t) => sum + (Number(t.credit) || 0), 0),
                count: txns.length,
              }
            }
          ])
        ),
        metadata: {
          exported_at: new Date().toISOString(),
          total_transactions: transactions.length,
          total_categories: categoryMap.size,
        }
      };

      downloadJSON(categorizedData, `${statement?.bank_name}_categorized_${format(new Date(), 'yyyy-MM-dd')}.json`);
      toast.success('Categorized JSON exported successfully');
    } catch (error) {
      console.error('Error exporting:', error);
      toast.error('Failed to export data');
    } finally {
      setExporting(null);
    }
  };

  const handleExportSummaryReport = async () => {
    if (!selectedStatement) return;
    
    setExporting('summary');
    try {
      const statement = statements.find(s => s.id === selectedStatement);
      const transactions = await fetchTransactionsForStatement(selectedStatement);
      
      // Calculate stats
      const totalDebit = transactions.reduce((sum, t) => sum + (Number(t.debit) || 0), 0);
      const totalCredit = transactions.reduce((sum, t) => sum + (Number(t.credit) || 0), 0);
      const lastBalance = transactions.length > 0 ? Number(transactions[transactions.length - 1].balance) || 0 : 0;

      // Calculate category totals
      const categoryTotals = new Map<string, { debit: number; credit: number; count: number }>();
      transactions.forEach(t => {
        const category = t.category || 'Uncategorized';
        const existing = categoryTotals.get(category) || { debit: 0, credit: 0, count: 0 };
        categoryTotals.set(category, {
          debit: existing.debit + (Number(t.debit) || 0),
          credit: existing.credit + (Number(t.credit) || 0),
          count: existing.count + 1,
        });
      });

      const summaryReport = {
        report_title: 'Bank Statement Summary Report',
        generated_at: new Date().toISOString(),
        bank_details: {
          bank_name: statement?.bank_name,
          file_name: statement?.file_name,
          upload_date: statement?.upload_date,
        },
        financial_summary: {
          total_credit: totalCredit,
          total_credit_formatted: formatINR(totalCredit),
          total_debit: totalDebit,
          total_debit_formatted: formatINR(totalDebit),
          final_balance: lastBalance,
          final_balance_formatted: formatINR(lastBalance),
          net_flow: totalCredit - totalDebit,
          net_flow_formatted: formatINR(totalCredit - totalDebit),
        },
        category_breakdown: Array.from(categoryTotals.entries())
          .sort((a, b) => b[1].debit - a[1].debit)
          .map(([category, data]) => ({
            category,
            total_debit: data.debit,
            total_debit_formatted: formatINR(data.debit),
            total_credit: data.credit,
            total_credit_formatted: formatINR(data.credit),
            transaction_count: data.count,
          })),
        transactions_summary: {
          total_count: transactions.length,
          date_range: transactions.length > 0 ? {
            from: transactions[0].date,
            to: transactions[transactions.length - 1].date,
          } : null,
        },
        all_transactions: transactions.map(t => ({
          date: t.date,
          description: t.description,
          category: t.category || 'Uncategorized',
          debit: Number(t.debit) || 0,
          debit_formatted: formatINR(Number(t.debit) || 0),
          credit: Number(t.credit) || 0,
          credit_formatted: formatINR(Number(t.credit) || 0),
          balance: Number(t.balance) || 0,
          balance_formatted: formatINR(Number(t.balance) || 0),
        })),
      };

      downloadJSON(summaryReport, `${statement?.bank_name}_summary_report_${format(new Date(), 'yyyy-MM-dd')}.json`);
      toast.success('Summary report exported successfully');
    } catch (error) {
      console.error('Error exporting:', error);
      toast.error('Failed to export data');
    } finally {
      setExporting(null);
    }
  };

  const handleExportAISummary = async () => {
    if (!selectedStatement) return;
    
    setExporting('ai-summary');
    try {
      const statement = statements.find(s => s.id === selectedStatement);
      
      if (!statement) {
        throw new Error('Statement not found');
      }
      
      console.log('Fetching AI summary for statement:', selectedStatement);
      
      // Fetch AI summary from backend
      const result = await flaskApi.getAISummary(selectedStatement);
      
      console.log('AI Summary result:', result);
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to generate AI summary');
      }

      const summaryData = result.data;
      const summary = summaryData.summary || summaryData.fallback_summary;
      const metadata = summaryData.metadata || {};

      // Create comprehensive AI summary report
      const aiReport = {
        report_title: 'AI-Powered Expense Summary Report',
        generated_at: new Date().toISOString(),
        generated_by: 'OpenAI GPT-4',
        bank_details: {
          bank_name: statement?.bank_name,
          file_name: statement?.file_name,
          upload_date: statement?.upload_date,
        },
        ai_summary: {
          executive_summary: summary.executive_summary || '',
          spending_analysis: summary.spending_analysis || '',
          category_insights: summary.category_insights || '',
          trends_patterns: summary.trends_patterns || '',
          recommendations: summary.recommendations || '',
          key_highlights: summary.key_highlights || [],
        },
        financial_metadata: {
          total_credit: metadata.total_credit || 0,
          total_credit_formatted: formatINR(metadata.total_credit || 0),
          total_debit: metadata.total_debit || 0,
          total_debit_formatted: formatINR(metadata.total_debit || 0),
          net_flow: metadata.net_flow || 0,
          net_flow_formatted: formatINR(metadata.net_flow || 0),
          transaction_count: metadata.transaction_count || 0,
          top_categories: metadata.top_categories || [],
        },
        note: summaryData.success 
          ? 'This report was generated using AI analysis of your transaction data.'
          : 'AI summary unavailable. This is a basic summary report.',
      };

      downloadJSON(aiReport, `${statement?.bank_name}_ai_summary_${format(new Date(), 'yyyy-MM-dd')}.json`);
      toast.success('AI summary report exported successfully');
    } catch (error: any) {
      console.error('Error exporting AI summary:', error);
      const errorMessage = error.message || 'Failed to generate AI summary';
      toast.error(errorMessage);
      
      // Show more detailed error in console
      if (errorMessage.includes('Network error') || errorMessage.includes('fetch')) {
        console.error('Make sure your backend server is running on http://localhost:5000');
        console.error('Check browser console for CORS errors');
      }
    } finally {
      setExporting(null);
    }
  };

  const handleExportPDFReport = async () => {
    if (!selectedStatement) return;
    
    setExporting('pdf');
    try {
      const statement = statements.find(s => s.id === selectedStatement);
      const transactions = await fetchTransactionsForStatement(selectedStatement);
      
      // Calculate stats
      const totalDebit = transactions.reduce((sum, t) => sum + (Number(t.debit) || 0), 0);
      const totalCredit = transactions.reduce((sum, t) => sum + (Number(t.credit) || 0), 0);
      const lastBalance = transactions.length > 0 ? Number(transactions[transactions.length - 1].balance) || 0 : 0;

      // Calculate category totals
      const categoryTotals = new Map<string, { debit: number; count: number }>();
      transactions.forEach(t => {
        const category = t.category || 'Uncategorized';
        const existing = categoryTotals.get(category) || { debit: 0, count: 0 };
        categoryTotals.set(category, {
          debit: existing.debit + (Number(t.debit) || 0),
          count: existing.count + 1,
        });
      });

      // Create PDF
      const doc = new jsPDF();
      const pageWidth = doc.internal.pageSize.getWidth();
      
      // Header
      doc.setFontSize(20);
      doc.setFont('helvetica', 'bold');
      doc.text('Bank Statement Summary Report', pageWidth / 2, 20, { align: 'center' });
      
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      doc.text(`Generated: ${format(new Date(), 'dd MMM yyyy, HH:mm')}`, pageWidth / 2, 28, { align: 'center' });
      
      // Bank Details
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('Bank Details', 14, 42);
      
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      doc.text(`Bank: ${statement?.bank_name}`, 14, 50);
      doc.text(`File: ${statement?.file_name}`, 14, 56);
      doc.text(`Uploaded: ${safeFormatDate(statement?.upload_date, 'dd MMM yyyy', 'Unknown')}`, 14, 62);
      
      // Financial Summary
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('Financial Summary', 14, 76);
      
      autoTable(doc, {
        startY: 80,
        head: [['Metric', 'Amount (₹)']],
        body: [
          ['Total Credit', formatINR(totalCredit)],
          ['Total Debit', formatINR(totalDebit)],
          ['Net Flow', formatINR(totalCredit - totalDebit)],
          ['Final Balance', formatINR(lastBalance)],
        ],
        theme: 'striped',
        headStyles: { fillColor: [59, 130, 246] },
        margin: { left: 14, right: 14 },
        tableWidth: 'auto',
      });

      // Category Breakdown
      const categoryY = (doc as any).lastAutoTable.finalY + 15;
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('Category Breakdown', 14, categoryY);

      const categoryData = Array.from(categoryTotals.entries())
        .sort((a, b) => b[1].debit - a[1].debit)
        .map(([category, data]) => [category, data.count.toString(), formatINR(data.debit)]);

      autoTable(doc, {
        startY: categoryY + 4,
        head: [['Category', 'Transactions', 'Total Spending']],
        body: categoryData,
        theme: 'striped',
        headStyles: { fillColor: [59, 130, 246] },
        margin: { left: 14, right: 14 },
      });

      // Transactions Table
      const txY = (doc as any).lastAutoTable.finalY + 15;
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('All Transactions', 14, txY);

      const txData = transactions.map(t => [
        t.date,
        t.description.substring(0, 30) + (t.description.length > 30 ? '...' : ''),
        t.category || 'Uncategorized',
        formatINR(Number(t.debit) || 0),
        formatINR(Number(t.credit) || 0),
        formatINR(Number(t.balance) || 0),
      ]);

      autoTable(doc, {
        startY: txY + 4,
        head: [['Date', 'Description', 'Category', 'Debit', 'Credit', 'Balance']],
        body: txData,
        theme: 'striped',
        headStyles: { fillColor: [59, 130, 246] },
        margin: { left: 14, right: 14 },
        styles: { fontSize: 8 },
        columnStyles: {
          0: { cellWidth: 22 },
          1: { cellWidth: 45 },
          2: { cellWidth: 30 },
          3: { cellWidth: 25 },
          4: { cellWidth: 25 },
          5: { cellWidth: 28 },
        },
      });

      // Footer
      const pageCount = doc.internal.pages.length - 1;
      for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setFont('helvetica', 'normal');
        doc.text(
          `Page ${i} of ${pageCount} | BankFusion Report`,
          pageWidth / 2,
          doc.internal.pageSize.getHeight() - 10,
          { align: 'center' }
        );
      }

      doc.save(`${statement?.bank_name}_report_${format(new Date(), 'yyyy-MM-dd')}.pdf`);
      toast.success('PDF report exported successfully');
    } catch (error) {
      console.error('Error exporting PDF:', error);
      toast.error('Failed to export PDF report');
    } finally {
      setExporting(null);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  const selectedStatementData = statements.find(s => s.id === selectedStatement);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">Export & Reports</h1>
          <p className="text-muted-foreground">
            Download your bank statement data in various formats
          </p>
        </div>

        {statements.length === 0 ? (
          <Card className="p-8 text-center">
            <Download className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-foreground mb-2">No Statements Available</h2>
            <p className="text-muted-foreground">
              Upload a bank statement first to export data.
            </p>
          </Card>
        ) : (
          <>
            {/* Statement selector */}
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4">Select Statement</h2>
              <Select value={selectedStatement} onValueChange={setSelectedStatement}>
                <SelectTrigger className="w-full max-w-md">
                  <SelectValue placeholder="Select a statement" />
                </SelectTrigger>
                <SelectContent>
                  {statements.map((statement) => (
                    <SelectItem key={statement.id} value={statement.id}>
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4" />
                        <span>{statement.bank_name}</span>
                        <span className="text-muted-foreground">- {statement.file_name}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {selectedStatementData && (
                <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
                  <Calendar className="w-4 h-4" />
                  <span>Uploaded on {safeFormatDate(selectedStatementData.upload_date, 'dd MMM yyyy')}</span>
                </div>
              )}
            </Card>

            {/* Export options */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card className="p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-info/10 text-info">
                    <FileJson className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">Normalized JSON</h3>
                    <p className="text-sm text-muted-foreground">Raw transaction data</p>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground mb-4">
                  Export all transactions in a clean, normalized format suitable for data analysis.
                </p>
                <Button 
                  className="w-full" 
                  variant="outline"
                  onClick={handleExportNormalizedJSON}
                  disabled={exporting !== null || !selectedStatement}
                >
                  {exporting === 'normalized' ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 mr-2" />
                  )}
                  Download JSON
                </Button>
              </Card>

              <Card className="p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-success/10 text-success">
                    <FileJson className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">Categorized JSON</h3>
                    <p className="text-sm text-muted-foreground">Grouped by category</p>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground mb-4">
                  Transactions organized by spending categories with summary totals.
                </p>
                <Button 
                  className="w-full" 
                  variant="outline"
                  onClick={handleExportCategorizedJSON}
                  disabled={exporting !== null || !selectedStatement}
                >
                  {exporting === 'categorized' ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 mr-2" />
                  )}
                  Download JSON
                </Button>
              </Card>

              <Card className="p-6 hover:shadow-lg transition-shadow border-2 border-primary/20">
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 text-primary">
                    <FileDown className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">PDF Report</h3>
                    <p className="text-sm text-muted-foreground">Printable document</p>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground mb-4">
                  Professional PDF report with bank details, financial summary, category breakdown, and transactions table.
                </p>
                <Button 
                  className="w-full"
                  onClick={handleExportPDFReport}
                  disabled={exporting !== null || !selectedStatement}
                >
                  {exporting === 'pdf' ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <FileDown className="w-4 h-4 mr-2" />
                  )}
                  Download PDF
                </Button>
              </Card>

              <Card className="p-6 hover:shadow-lg transition-shadow border-2 border-purple-500/20 bg-gradient-to-br from-purple-50/50 to-blue-50/50 dark:from-purple-950/20 dark:to-blue-950/20">
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 text-purple-600 dark:text-purple-400">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">AI Summary Report</h3>
                    <p className="text-sm text-muted-foreground">AI-powered insights</p>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground mb-4">
                  Get comprehensive AI-generated expense analysis with spending patterns, category insights, trends, and actionable recommendations.
                </p>
                <Button 
                  className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                  onClick={handleExportAISummary}
                  disabled={exporting !== null || !selectedStatement}
                >
                  {exporting === 'ai-summary' ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4 mr-2" />
                  )}
                  Generate AI Summary
                </Button>
              </Card>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
