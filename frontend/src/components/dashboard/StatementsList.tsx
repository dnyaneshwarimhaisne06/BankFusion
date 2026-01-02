import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { FileText, ChevronRight, Building2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface Statement {
  id: string;
  bank_name: string;
  file_name: string;
  upload_date: string;
  status: string;
}

interface StatementsListProps {
  statements: Statement[];
  loading?: boolean;
}

const bankColors: Record<string, string> = {
  'HDFC': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'ICICI': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  'SBI': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  'Axis': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  'Kotak': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  'Default': 'bg-secondary text-secondary-foreground',
};

const statusColors: Record<string, string> = {
  'processed': 'bg-success/10 text-success border-success/20',
  'processing': 'bg-warning/10 text-warning border-warning/20',
  'failed': 'bg-destructive/10 text-destructive border-destructive/20',
};

export function StatementsList({ statements, loading }: StatementsListProps) {
  if (loading) {
    return (
      <div className="rounded-2xl border bg-card p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-pulse text-muted-foreground">Loading statements...</div>
        </div>
      </div>
    );
  }

  if (!statements || statements.length === 0) {
    return (
      <div className="rounded-2xl border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">Uploaded Statements</h3>
        <div className="flex flex-col items-center justify-center py-12">
          <FileText className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No statements uploaded yet</p>
          <Link
            to="/upload"
            className="mt-4 text-primary hover:underline font-medium"
          >
            Upload your first statement →
          </Link>
        </div>
      </div>
    );
  }

  const getBankColor = (bankName: string) => {
    const bank = Object.keys(bankColors).find((key) =>
      bankName.toLowerCase().includes(key.toLowerCase())
    );
    return bankColors[bank || 'Default'];
  };

  return (
    <div className="rounded-2xl border bg-card overflow-hidden">
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Uploaded Statements</h3>
          <Link
            to="/statements"
            className="text-sm text-primary hover:underline font-medium"
          >
            View all →
          </Link>
        </div>
      </div>
      <div className="divide-y divide-border">
        {statements.slice(0, 5).map((statement) => (
          <Link
            key={statement.id}
            to={`/statements/${statement.id}`}
            className="flex items-center gap-4 p-4 hover:bg-secondary/50 transition-colors"
          >
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-secondary">
              <Building2 className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-foreground truncate">
                {statement.file_name}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="secondary" className={cn("text-xs", getBankColor(statement.bank_name))}>
                  {statement.bank_name}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {format(new Date(statement.upload_date), 'dd MMM yyyy')}
                </span>
              </div>
            </div>
            <Badge
              variant="outline"
              className={cn("capitalize", statusColors[statement.status] || statusColors['processing'])}
            >
              {statement.status}
            </Badge>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </Link>
        ))}
      </div>
    </div>
  );
}
