import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useAuth } from '@/contexts/AuthContext';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { User, Mail, Calendar, FileDown, Loader2 } from 'lucide-react';
import { safeFormatDate } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { flaskApi } from '@/lib/api/flask-api';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { format } from 'date-fns';
import { formatINR } from '@/lib/currency';

export default function Settings() {
  const { user } = useAuth();
  const { toast: showToast } = useToast();
  const [statements, setStatements] = useState<any[]>([]);
  const [selectedStatement, setSelectedStatement] = useState<string>('');
  const [loadingStatements, setLoadingStatements] = useState(false);
  const [exporting, setExporting] = useState<'pdf' | null>(null);

  // Load statements for PDF export
  const loadStatements = async () => {
    if (statements.length > 0) return; // Already loaded
    
    setLoadingStatements(true);
    try {
      const result = await flaskApi.getStatements();
      if (result.success && result.data) {
        // Transform statements to match expected format
        const transformed = result.data.map((s: any) => ({
          id: s._id || s.id,
          bank_name: s.bankType || 'Unknown',
          file_name: s.fileName || 'Untitled',
          upload_date: s.uploadDate || s.createdAt || '',
        }));
        setStatements(transformed);
      }
    } catch (error) {
      console.error('Error loading statements:', error);
    } finally {
      setLoadingStatements(false);
    }
  };

  const fetchTransactionsForStatement = async (statementId: string) => {
    try {
      const result = await flaskApi.getTransactionsByStatement(statementId);
      if (result.success && result.data) {
        // Convert API format to expected format
        return result.data.map((tx: any) => ({
          date: tx.date,
          description: tx.description || tx.reference || '',
          category: tx.category || 'Uncategorized',
          debit: tx.direction === 'debit' ? (tx.amount || 0) : null,
          credit: tx.direction === 'credit' ? (tx.amount || 0) : null,
          balance: tx.balance || 0,
        }));
      }
      return [];
    } catch (error) {
      console.error('Error fetching transactions:', error);
      return [];
    }
  };

  const handleExportPDFReport = async () => {
    if (!selectedStatement) {
      showToast({
        title: 'Error',
        description: 'Please select a statement',
        variant: 'destructive',
      });
      return;
    }

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

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        {/* Page header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">Settings</h1>
          <p className="text-muted-foreground">
            Manage your account settings and preferences
          </p>
        </div>

        {/* Profile section */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <User className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Profile</h2>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 rounded-xl bg-secondary/50">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 text-primary text-lg font-bold">
                {user?.email?.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="font-medium text-foreground">{user?.email}</p>
                <p className="text-sm text-muted-foreground">Account Email</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 rounded-xl bg-secondary/50">
              <Mail className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="font-medium text-foreground">{user?.email}</p>
                <p className="text-sm text-muted-foreground">Email Address</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 rounded-xl bg-secondary/50">
              <Calendar className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="font-medium text-foreground">
                  {safeFormatDate(user?.created_at, 'dd MMM yyyy', 'N/A')}
                </p>
                <p className="text-sm text-muted-foreground">Member Since</p>
              </div>
            </div>
          </div>
        </Card>

        {/* PDF Report Download */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <FileDown className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Download PDF Report</h2>
          </div>

          <div className="space-y-4">
            <div>
              <Label htmlFor="statement-select">Select Statement</Label>
              <Select
                value={selectedStatement}
                onValueChange={setSelectedStatement}
                onOpenChange={(open) => {
                  if (open && statements.length === 0) {
                    loadStatements();
                  }
                }}
              >
                <SelectTrigger id="statement-select" disabled={loadingStatements}>
                  <SelectValue placeholder={loadingStatements ? "Loading..." : "Select a statement"} />
                </SelectTrigger>
                <SelectContent>
                  {statements.map((stmt) => (
                    <SelectItem key={stmt.id} value={stmt.id}>
                      {stmt.bank_name} - {stmt.file_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              className="w-full"
              onClick={handleExportPDFReport}
              disabled={exporting !== null || !selectedStatement || loadingStatements}
            >
              {exporting === 'pdf' ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating PDF...
                </>
              ) : (
                <>
                  <FileDown className="w-4 h-4 mr-2" />
                  Download PDF Report
                </>
              )}
            </Button>
          </div>
        </Card>
      </div>
    </DashboardLayout>
  );
}
