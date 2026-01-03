import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { flaskApi, Statement } from '@/lib/api/flask-api';
import { safeFormatDate } from '@/lib/utils';
import { 
  FileText, 
  Search, 
  Building2, 
  ChevronRight, 
  Upload,
  Trash2,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useToast } from '@/hooks/use-toast';

const bankColors: Record<string, string> = {
  'HDFC': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'ICICI': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  'SBI': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  'AXIS': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  'BOI': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  'CBI': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  'UNION': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  'Default': 'bg-secondary text-secondary-foreground',
};

interface DisplayStatement {
  id: string;
  bank_name: string;
  file_name: string;
  upload_date: string;
  status: string;
  transactionCount?: number;
}

export default function Statements() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [statements, setStatements] = useState<DisplayStatement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (user) {
      fetchStatements();
    }
  }, [user]);

  const fetchStatements = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await flaskApi.getStatements();
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch statements');
      }

      const transformed = (result.data || []).map(s => ({
        id: s._id || '',
        bank_name: s.bankType || 'Unknown',
        file_name: s.fileName || 'Untitled',
        upload_date: s.uploadDate || '',
        status: 'processed',
        transactionCount: s.transactionCount,
      }));
      
      setStatements(transformed);
    } catch (err: any) {
      console.error('Error fetching statements:', err);
      setError(err.message || 'Failed to load statements');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    
    setDeleting(true);
    try {
      const result = await flaskApi.deleteStatement(deleteId);
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to delete statement');
      }

      setStatements((prev) => prev.filter((s) => s.id !== deleteId));
      toast({
        title: 'Statement deleted',
        description: 'The statement has been successfully deleted.',
      });
    } catch (err: any) {
      toast({
        title: 'Delete failed',
        description: err.message || 'Failed to delete statement',
        variant: 'destructive',
      });
    } finally {
      setDeleting(false);
      setDeleteId(null);
    }
  };

  const getBankColor = (bankName: string | undefined) => {
    if (!bankName) return bankColors['Default'];
    const bank = Object.keys(bankColors).find((key) =>
      bankName.toUpperCase().includes(key)
    );
    return bankColors[bank || 'Default'];
  };

  const filteredStatements = statements.filter((s) => {
    const fileName = (s.file_name || '').toLowerCase();
    const bankName = (s.bank_name || '').toLowerCase();
    const searchTerm = search.toLowerCase();
    return fileName.includes(searchTerm) || bankName.includes(searchTerm);
  });

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold text-foreground">All Statements</h1>
            <p className="text-muted-foreground">
              {statements.length} statement{statements.length !== 1 ? 's' : ''} uploaded
            </p>
          </div>
          <Link to="/upload">
            <Button>
              <Upload className="w-4 h-4 mr-2" />
              Upload New
            </Button>
          </Link>
        </div>

        {/* Error state */}
        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-destructive/10 text-destructive">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <div>
              <p className="font-medium">Connection Error</p>
              <p className="text-sm opacity-80">{error}</p>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="relative max-w-md animate-slide-up">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search statements..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Statements list */}
        {filteredStatements.length === 0 ? (
          <div className="rounded-2xl border bg-card p-12 text-center">
            <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {search ? 'No statements found' : 'No statements yet'}
            </h3>
            <p className="text-muted-foreground mb-6">
              {search
                ? 'Try a different search term'
                : 'Upload your first bank statement to get started'}
            </p>
            {!search && (
              <Link to="/upload">
                <Button>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload Statement
                </Button>
              </Link>
            )}
          </div>
        ) : (
          <div className="rounded-2xl border bg-card overflow-hidden divide-y divide-border">
            {filteredStatements.map((statement) => (
              <div
                key={statement.id}
                className="flex items-center gap-4 p-4 hover:bg-secondary/50 transition-colors"
              >
                <Link
                  to={`/statements/${statement.id}`}
                  className="flex items-center gap-4 flex-1 min-w-0"
                >
                  <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-secondary">
                    <Building2 className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground truncate">
                      {statement.file_name || 'Untitled'}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary" className={cn("text-xs", getBankColor(statement.bank_name))}>
                        {statement.bank_name || 'Unknown'}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {safeFormatDate(statement.upload_date, 'dd MMM yyyy, hh:mm a')}
                      </span>
                      {statement.transactionCount && (
                        <span className="text-xs text-muted-foreground">
                          • {statement.transactionCount} transactions
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
                <Badge
                  variant="outline"
                  className="bg-success/10 text-success border-success/20 capitalize"
                >
                  {statement.status}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-muted-foreground hover:text-destructive"
                  onClick={() => setDeleteId(statement.id)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
                <Link to={`/statements/${statement.id}`}>
                  <Button variant="ghost" size="icon">
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Statement</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this statement? This action cannot be undone.
              All associated transactions will also be deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </DashboardLayout>
  );
}
