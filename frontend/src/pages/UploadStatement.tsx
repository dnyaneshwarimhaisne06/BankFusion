import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/integrations/supabase/client';
import { Upload, FileText, CheckCircle, Loader2, X, Building2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Progress } from '@/components/ui/progress';

interface UploadState {
  file: File | null;
  uploading: boolean;
  progress: number;
  detectedBank: string | null;
  statementId: string | null;
  error: string | null;
}

const bankPatterns: Record<string, RegExp> = {
  'HDFC Bank': /hdfc/i,
  'ICICI Bank': /icici/i,
  'State Bank of India': /sbi|state bank/i,
  'Axis Bank': /axis/i,
  'Kotak Mahindra': /kotak/i,
  'Punjab National Bank': /pnb|punjab national/i,
  'Bank of Baroda': /baroda|bob/i,
  'Yes Bank': /yes bank/i,
  'IndusInd Bank': /indusind/i,
  'IDBI Bank': /idbi/i,
};

function detectBankFromFileName(fileName: string): string {
  for (const [bankName, pattern] of Object.entries(bankPatterns)) {
    if (pattern.test(fileName)) {
      return bankName;
    }
  }
  return 'Unknown Bank';
}

export default function UploadStatement() {
  const [state, setState] = useState<UploadState>({
    file: null,
    uploading: false,
    progress: 0,
    detectedBank: null,
    statementId: null,
    error: null,
  });
  const [isDragging, setIsDragging] = useState(false);
  
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    const pdfFile = files.find((f) => f.type === 'application/pdf');
    
    if (pdfFile) {
      handleFileSelect(pdfFile);
    } else {
      toast({
        title: 'Invalid file type',
        description: 'Please upload a PDF file',
        variant: 'destructive',
      });
    }
  }, [toast]);

  const handleFileSelect = (file: File) => {
    if (file.type !== 'application/pdf') {
      toast({
        title: 'Invalid file type',
        description: 'Please upload a PDF file',
        variant: 'destructive',
      });
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      toast({
        title: 'File too large',
        description: 'Maximum file size is 10MB',
        variant: 'destructive',
      });
      return;
    }

    const detectedBank = detectBankFromFileName(file.name);
    
    setState({
      file,
      uploading: false,
      progress: 0,
      detectedBank,
      statementId: null,
      error: null,
    });
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleUpload = async () => {
    if (!state.file || !user) return;

    setState((prev) => ({ ...prev, uploading: true, progress: 10, error: null }));

    try {
      const fileExt = state.file.name.split('.').pop();
      const fileName = `${crypto.randomUUID()}.${fileExt}`;
      const filePath = `${user.id}/${fileName}`;

      setState((prev) => ({ ...prev, progress: 30 }));

      // Upload file to storage
      const { error: uploadError } = await supabase.storage
        .from('statements')
        .upload(filePath, state.file);

      if (uploadError) throw uploadError;

      setState((prev) => ({ ...prev, progress: 60 }));

      // Create statement record
      const { data: statementData, error: statementError } = await supabase
        .from('bank_statements')
        .insert({
          user_id: user.id,
          bank_name: state.detectedBank || 'Unknown Bank',
          file_path: filePath,
          file_name: state.file.name,
          status: 'processing',
        })
        .select()
        .single();

      if (statementError) throw statementError;

      setState((prev) => ({ 
        ...prev, 
        progress: 100, 
        statementId: statementData.id,
        uploading: false,
      }));

      toast({
        title: 'Upload successful!',
        description: `${state.detectedBank} statement uploaded and is being processed.`,
      });

      // Redirect after a short delay
      setTimeout(() => {
        navigate(`/statements/${statementData.id}`);
      }, 1500);

    } catch (error: any) {
      console.error('Upload error:', error);
      setState((prev) => ({
        ...prev,
        uploading: false,
        error: error.message || 'Failed to upload statement',
      }));
      toast({
        title: 'Upload failed',
        description: error.message || 'Failed to upload statement',
        variant: 'destructive',
      });
    }
  };

  const resetUpload = () => {
    setState({
      file: null,
      uploading: false,
      progress: 0,
      detectedBank: null,
      statementId: null,
      error: null,
    });
  };

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Page header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">Upload Statement</h1>
          <p className="text-muted-foreground">
            Upload a bank statement PDF to analyze transactions
          </p>
        </div>

        {/* Upload area */}
        <div className="animate-slide-up">
          {!state.file ? (
            <label
              className={cn(
                "flex flex-col items-center justify-center p-12 rounded-2xl border-2 border-dashed cursor-pointer transition-all duration-200",
                isDragging
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50 hover:bg-secondary/50"
              )}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input
                type="file"
                accept="application/pdf"
                onChange={handleInputChange}
                className="sr-only"
              />
              <div className="flex flex-col items-center text-center">
                <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 text-primary mb-4">
                  <Upload className="w-8 h-8" />
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  Drop your PDF here
                </h3>
                <p className="text-muted-foreground mb-4">
                  or click to browse from your computer
                </p>
                <p className="text-xs text-muted-foreground">
                  Supports PDF files up to 10MB
                </p>
              </div>
            </label>
          ) : (
            <div className="rounded-2xl border bg-card p-6 space-y-6">
              {/* File info */}
              <div className="flex items-start gap-4">
                <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 text-primary">
                  <FileText className="w-6 h-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-foreground truncate">
                    {state.file.name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {(state.file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                {!state.uploading && !state.statementId && (
                  <Button variant="ghost" size="icon" onClick={resetUpload}>
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </div>

              {/* Detected bank */}
              <div className="flex items-center gap-3 p-4 rounded-xl bg-secondary/50">
                <Building2 className="w-5 h-5 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Detected Bank</p>
                  <p className="font-medium text-foreground">{state.detectedBank}</p>
                </div>
              </div>

              {/* Progress */}
              {state.uploading && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Uploading...</span>
                    <span className="font-medium">{state.progress}%</span>
                  </div>
                  <Progress value={state.progress} className="h-2" />
                </div>
              )}

              {/* Success state */}
              {state.statementId && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-success/10 text-success">
                  <CheckCircle className="w-5 h-5" />
                  <div>
                    <p className="font-medium">Upload complete!</p>
                    <p className="text-sm opacity-80">Redirecting to statement...</p>
                  </div>
                </div>
              )}

              {/* Error state */}
              {state.error && (
                <div className="p-4 rounded-xl bg-destructive/10 text-destructive">
                  <p className="font-medium">Upload failed</p>
                  <p className="text-sm opacity-80">{state.error}</p>
                </div>
              )}

              {/* Actions */}
              {!state.statementId && (
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={resetUpload}
                    disabled={state.uploading}
                  >
                    Cancel
                  </Button>
                  <Button
                    className="flex-1"
                    onClick={handleUpload}
                    disabled={state.uploading}
                  >
                    {state.uploading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 mr-2" />
                        Upload Statement
                      </>
                    )}
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Supported banks */}
        <div className="rounded-2xl border bg-card p-6">
          <h3 className="font-semibold text-foreground mb-4">Supported Banks</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.keys(bankPatterns).map((bank) => (
              <div
                key={bank}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/50"
              >
                <Building2 className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm">{bank}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
