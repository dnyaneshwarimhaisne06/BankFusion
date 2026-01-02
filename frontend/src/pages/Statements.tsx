import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/integrations/supabase/client';
import { format } from 'date-fns';
import { 
  FileText, 
  Search, 
  Building2, 
  ChevronRight, 
  Upload,
  Trash2,
  Loader2
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

interface Statement {
  id: string;
  bank_name: string;
  file_name: string;
  upload_date: string;
  status: string;
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

export default function Statements() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [statements, setStatements] = useState<Statement[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (user) {
      fetchStatements();
    }
  }, [user]);

  const fetchStatements = async () => {
    try {
      const { data, error } = await supabase
        .from('bank_statements')
        .select('*')
        .order('upload_date', { ascending: false });

      if (error) throw error;
      setStatements(data || []);
    } catch (error) {
      console.error('Error fetching statements:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    
    setDeleting(true);
    try {
      const { error } = await supabase
        .from('bank_statements')
        .delete()
        .eq('id', deleteId);

      if (error) throw error;

      setStatements((prev) => prev.filter((s) => s.id !== deleteId));
      toast({
        title: 'Statement deleted',
        description: 'The statement has been successfully deleted.',
      });
    } catch (error: any) {
      toast({
        title: 'Delete failed',
        description: error.message || 'Failed to delete statement',
        variant: 'destructive',
      });
    } finally {
      setDeleting(false);
      setDeleteId(null);
    }
  };

  const getBankColor = (bankName: string) => {
    const bank = Object.keys(bankColors).find((key) =>
      bankName.toLowerCase().includes(key.toLowerCase())
    );
    return bankColors[bank || 'Default'];
  };

  const filteredStatements = statements.filter((s) =>
    s.file_name.toLowerCase().includes(search.toLowerCase()) ||
    s.bank_name.toLowerCase().includes(search.toLowerCase())
  );

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
                      {statement.file_name}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary" className={cn("text-xs", getBankColor(statement.bank_name))}>
                        {statement.bank_name}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {format(new Date(statement.upload_date), 'dd MMM yyyy, hh:mm a')}
                      </span>
                    </div>
                  </div>
                </Link>
                <Badge
                  variant="outline"
                  className={cn("capitalize", statusColors[statement.status] || statusColors['processing'])}
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
