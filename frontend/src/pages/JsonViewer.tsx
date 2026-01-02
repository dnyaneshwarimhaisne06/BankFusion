import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { Download, FileJson, ChevronRight, ChevronDown, Loader2 } from 'lucide-react';
import { formatINR } from '@/lib/currency';

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

interface CollapsibleJsonProps {
  data: any;
  level?: number;
}

function CollapsibleJson({ data, level = 0 }: CollapsibleJsonProps) {
  const [expanded, setExpanded] = useState(level < 2);
  
  if (data === null) return <span className="text-muted-foreground">null</span>;
  if (typeof data === 'boolean') return <span className="text-primary">{data.toString()}</span>;
  if (typeof data === 'number') return <span className="text-success">{data}</span>;
  if (typeof data === 'string') return <span className="text-warning">"{data}"</span>;
  
  if (Array.isArray(data)) {
    if (data.length === 0) return <span className="text-muted-foreground">[]</span>;
    
    return (
      <div className="ml-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <span className="text-xs">Array [{data.length}]</span>
        </button>
        {expanded && (
          <div className="border-l border-border pl-4 mt-1 space-y-1">
            {data.map((item, index) => (
              <div key={index}>
                <span className="text-muted-foreground text-xs">{index}: </span>
                <CollapsibleJson data={item} level={level + 1} />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  
  if (typeof data === 'object') {
    const keys = Object.keys(data);
    if (keys.length === 0) return <span className="text-muted-foreground">{'{}'}</span>;
    
    return (
      <div className="ml-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <span className="text-xs">Object {'{'}...{'}'}</span>
        </button>
        {expanded && (
          <div className="border-l border-border pl-4 mt-1 space-y-1">
            {keys.map((key) => (
              <div key={key}>
                <span className="text-primary text-xs font-medium">"{key}"</span>
                <span className="text-muted-foreground">: </span>
                <CollapsibleJson data={data[key]} level={level + 1} />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  
  return <span>{String(data)}</span>;
}

export default function JsonViewer() {
  const [statements, setStatements] = useState<Statement[]>([]);
  const [selectedStatementId, setSelectedStatementId] = useState<string>('');
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const { user } = useAuth();
  const { toast } = useToast();

  useEffect(() => {
    if (user) fetchStatements();
  }, [user]);

  useEffect(() => {
    if (selectedStatementId) {
      fetchTransactions(selectedStatementId);
    }
  }, [selectedStatementId]);

  const fetchStatements = async () => {
    try {
      const { data, error } = await supabase
        .from('bank_statements')
        .select('id, bank_name, file_name, upload_date')
        .eq('user_id', user?.id)
        .eq('status', 'completed')
        .order('upload_date', { ascending: false });

      if (error) throw error;
      setStatements(data || []);
      if (data && data.length > 0) {
        setSelectedStatementId(data[0].id);
      }
    } catch (error: any) {
      console.error('Error fetching statements:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTransactions = async (statementId: string) => {
    setLoadingData(true);
    try {
      const { data, error } = await supabase
        .from('transactions')
        .select('*')
        .eq('statement_id', statementId)
        .order('date', { ascending: true });

      if (error) throw error;
      setTransactions(data || []);
    } catch (error: any) {
      console.error('Error fetching transactions:', error);
    } finally {
      setLoadingData(false);
    }
  };

  const getNormalizedJson = () => {
    const statement = statements.find(s => s.id === selectedStatementId);
    return {
      statement: {
        id: selectedStatementId,
        bank_name: statement?.bank_name,
        file_name: statement?.file_name,
        upload_date: statement?.upload_date,
      },
      transactions: transactions.map(tx => ({
        date: tx.date,
        description: tx.description,
        debit: tx.debit,
        credit: tx.credit,
        balance: tx.balance,
      })),
      summary: {
        total_transactions: transactions.length,
        total_debit: transactions.reduce((sum, tx) => sum + (tx.debit || 0), 0),
        total_credit: transactions.reduce((sum, tx) => sum + (tx.credit || 0), 0),
        final_balance: transactions.length > 0 ? transactions[transactions.length - 1].balance : 0,
      },
    };
  };

  const getCategorizedJson = () => {
    const statement = statements.find(s => s.id === selectedStatementId);
    const grouped: Record<string, any[]> = {};
    
    transactions.forEach(tx => {
      const category = tx.category || 'Uncategorized';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push({
        date: tx.date,
        description: tx.description,
        debit: tx.debit,
        credit: tx.credit,
        balance: tx.balance,
      });
    });

    const categorySummary = Object.entries(grouped).map(([category, txs]) => ({
      category,
      transaction_count: txs.length,
      total_debit: txs.reduce((sum, tx) => sum + (tx.debit || 0), 0),
      total_credit: txs.reduce((sum, tx) => sum + (tx.credit || 0), 0),
    }));

    return {
      statement: {
        id: selectedStatementId,
        bank_name: statement?.bank_name,
        file_name: statement?.file_name,
      },
      categories: grouped,
      category_summary: categorySummary,
    };
  };

  const downloadJson = (type: 'normalized' | 'categorized') => {
    const data = type === 'normalized' ? getNormalizedJson() : getCategorizedJson();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${type}_transactions_${selectedStatementId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast({
      title: 'Download started',
      description: `${type.charAt(0).toUpperCase() + type.slice(1)} JSON downloaded successfully`,
    });
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">JSON Viewer</h1>
            <p className="text-muted-foreground">View and export transaction data in JSON format</p>
          </div>
          
          <Select value={selectedStatementId} onValueChange={setSelectedStatementId}>
            <SelectTrigger className="w-64">
              <SelectValue placeholder="Select statement" />
            </SelectTrigger>
            <SelectContent>
              {statements.map((statement) => (
                <SelectItem key={statement.id} value={statement.id}>
                  {statement.bank_name} - {new Date(statement.upload_date).toLocaleDateString()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {statements.length === 0 ? (
          <Card className="p-12 text-center">
            <FileJson className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No processed statements</h3>
            <p className="text-muted-foreground">Upload and process a statement to view JSON data</p>
          </Card>
        ) : (
          <Tabs defaultValue="normalized" className="space-y-4">
            <TabsList className="grid w-full max-w-md grid-cols-2">
              <TabsTrigger value="normalized">Normalized JSON</TabsTrigger>
              <TabsTrigger value="categorized">Categorized JSON</TabsTrigger>
            </TabsList>

            <TabsContent value="normalized" className="space-y-4">
              <Card className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold">Normalized Transaction Data</h3>
                  <Button onClick={() => downloadJson('normalized')} size="sm">
                    <Download className="w-4 h-4 mr-2" />
                    Download JSON
                  </Button>
                </div>
                
                {loadingData ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : (
                  <div className="bg-secondary/30 rounded-lg p-4 overflow-auto max-h-[500px] font-mono text-sm">
                    <CollapsibleJson data={getNormalizedJson()} />
                  </div>
                )}
              </Card>
            </TabsContent>

            <TabsContent value="categorized" className="space-y-4">
              <Card className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold">Categorized Transaction Data</h3>
                  <Button onClick={() => downloadJson('categorized')} size="sm">
                    <Download className="w-4 h-4 mr-2" />
                    Download JSON
                  </Button>
                </div>
                
                {loadingData ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : (
                  <div className="bg-secondary/30 rounded-lg p-4 overflow-auto max-h-[500px] font-mono text-sm">
                    <CollapsibleJson data={getCategorizedJson()} />
                  </div>
                )}
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </DashboardLayout>
  );
}
