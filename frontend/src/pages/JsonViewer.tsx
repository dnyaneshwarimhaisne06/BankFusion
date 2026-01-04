import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { flaskApi } from '@/lib/api/flask-api';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { Download, FileJson, ChevronRight, ChevronDown, Loader2, AlertCircle } from 'lucide-react';
import { formatINR } from '@/lib/currency';

interface DisplayStatement {
  id: string;
  bank_name: string;
  file_name: string;
  upload_date: string;
}

interface CollapsibleJsonProps {
  data: any;
  level?: number;
}

function CollapsibleJson({ data, level = 0 }: CollapsibleJsonProps) {
  const [expanded, setExpanded] = useState(level < 2);
  
  if (data === null || data === undefined) {
    return <span className="text-muted-foreground">{data === null ? 'null' : 'undefined'}</span>;
  }
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
  const [statements, setStatements] = useState<DisplayStatement[]>([]);
  const [selectedStatementId, setSelectedStatementId] = useState<string>('');
  const [normalizedData, setNormalizedData] = useState<any>(null);
  const [categorizedData, setCategorizedData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();
  const { toast } = useToast();

  useEffect(() => {
    if (user) fetchStatements();
  }, [user]);

  useEffect(() => {
    if (selectedStatementId) {
      fetchJsonData(selectedStatementId);
    }
  }, [selectedStatementId]);

  const fetchStatements = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await flaskApi.getStatements();
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch statements');
      }

      const transformed = (result.data || []).map(s => ({
        id: s._id,
        bank_name: s.bankType || 'Unknown',
        file_name: s.fileName || 'Untitled',
        upload_date: s.uploadDate || s.createdAt || new Date().toISOString(),
      }));
      
      setStatements(transformed);
      
      if (transformed.length > 0) {
        setSelectedStatementId(transformed[0].id);
      }
    } catch (err: any) {
      console.error('Error fetching statements:', err);
      setError(err.message || 'Failed to load statements');
    } finally {
      setLoading(false);
    }
  };

  const fetchJsonData = async (statementId: string) => {
    setLoadingData(true);
    try {
      const [normalizedResult, categorizedResult] = await Promise.all([
        flaskApi.getNormalizedJson(statementId),
        flaskApi.getCategorizedJson(statementId),
      ]);

      if (normalizedResult.success) {
        setNormalizedData(normalizedResult.data);
      }
      
      if (categorizedResult.success) {
        setCategorizedData(categorizedResult.data);
      }
    } catch (err: any) {
      console.error('Error fetching JSON data:', err);
    } finally {
      setLoadingData(false);
    }
  };

  const downloadJson = (type: 'normalized' | 'categorized') => {
    const data = type === 'normalized' ? normalizedData : categorizedData;
    if (!data) return;
    
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
              {statements.map((statement) => {
                let dateDisplay = 'Invalid Date';
                try {
                  const date = new Date(statement.upload_date);
                  if (!isNaN(date.getTime())) {
                    dateDisplay = date.toLocaleDateString();
                  }
                } catch (e) {
                  // Keep "Invalid Date" if parsing fails
                }
                return (
                <SelectItem key={statement.id} value={statement.id}>
                    {statement.bank_name} - {dateDisplay}
                </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
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
                  <Button onClick={() => downloadJson('normalized')} size="sm" disabled={!normalizedData}>
                    <Download className="w-4 h-4 mr-2" />
                    Download JSON
                  </Button>
                </div>
                
                {loadingData ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : normalizedData ? (
                  <div className="bg-secondary/30 rounded-lg p-4 overflow-auto max-h-[500px] font-mono text-sm">
                    <CollapsibleJson data={normalizedData} />
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    No data available
                  </div>
                )}
              </Card>
            </TabsContent>

            <TabsContent value="categorized" className="space-y-4">
              <Card className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold">Categorized Transaction Data</h3>
                  <Button onClick={() => downloadJson('categorized')} size="sm" disabled={!categorizedData}>
                    <Download className="w-4 h-4 mr-2" />
                    Download JSON
                  </Button>
                </div>
                
                {loadingData ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : categorizedData ? (
                  <div className="bg-secondary/30 rounded-lg p-4 overflow-auto max-h-[500px] font-mono text-sm">
                    <CollapsibleJson data={categorizedData} />
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    No data available
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
