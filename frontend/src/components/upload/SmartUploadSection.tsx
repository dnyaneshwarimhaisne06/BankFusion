import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileText, CheckCircle2, AlertCircle, Loader2, CloudUpload, Scan, Brain, Download } from 'lucide-react';
import { useUpload, ProcessedFile } from '@/contexts/UploadContext';
import { bankLogos } from '@/lib/mockData';
import { toast } from 'sonner';
import { JsonPreviewDialog } from './JsonPreviewDialog';

export function SmartUploadSection() {
  const { files, addFile } = useUpload();
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<ProcessedFile | null>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    processFiles(droppedFiles);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      processFiles(selectedFiles);
    }
  };

  const processFiles = (fileList: File[]) => {
    const pdfFiles = fileList.filter(f => f.type === 'application/pdf');
    
    if (pdfFiles.length === 0) {
      toast.error('Please upload PDF files only');
      return;
    }

    pdfFiles.forEach(file => {
      addFile(file);
      toast.info(`Processing ${file.name}...`);
    });
  };

  const getStatusDisplay = (file: ProcessedFile) => {
    switch (file.status) {
      case 'uploading':
        return (
          <div className="flex items-center gap-2 text-info">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm font-medium">Uploading...</span>
          </div>
        );
      case 'detecting':
        return (
          <div className="flex items-center gap-2 text-warning">
            <Scan className="w-4 h-4 animate-pulse" />
            <span className="text-sm font-medium">Detecting bank...</span>
          </div>
        );
      case 'processing':
        return (
          <div className="flex items-center gap-2 text-primary">
            <Brain className="w-4 h-4 animate-pulse" />
            <span className="text-sm font-medium">
              Processing • {file.bank && bankLogos[file.bank]?.name}
            </span>
          </div>
        );
      case 'completed':
        return (
          <div className="flex items-center gap-2 text-success">
            <CheckCircle2 className="w-4 h-4" />
            <span className="text-sm font-medium">Completed</span>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm font-medium">Error</span>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Upload Bank Statements</h1>
        <p className="text-muted-foreground mt-1">
          Drop your PDF statements — we'll automatically detect the bank
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary" />
            Smart Detection
          </CardTitle>
          <CardDescription>
            Our AI automatically identifies the bank format — no manual selection needed
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 ${
              isDragging 
                ? 'border-primary bg-primary/5 scale-[1.02]' 
                : 'border-border hover:border-primary/50 hover:bg-muted/50'
            }`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            <input
              type="file"
              accept=".pdf"
              multiple
              onChange={handleFileInput}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <CloudUpload className={`w-16 h-16 mx-auto mb-4 transition-colors ${isDragging ? 'text-primary' : 'text-muted-foreground'}`} />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              Drop your PDF statements here
            </h3>
            <p className="text-muted-foreground mb-4">
              Supports HDFC, ICICI, Axis, SBI, Kotak and more
            </p>
            <Button variant="outline">
              <CloudUpload className="w-4 h-4 mr-2" />
              Choose Files
            </Button>
          </div>
        </CardContent>
      </Card>

      {files.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Processing History</CardTitle>
            <CardDescription>
              {files.filter(f => f.status === 'completed').length} of {files.length} files processed
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {files.map((file) => (
                <div key={file.id} className="flex items-center gap-4 px-6 py-4 hover:bg-muted/30 transition-colors">
                  <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                    <FileText className="w-5 h-5 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground truncate">{file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {file.bank && bankLogos[file.bank] && (
                        <span className="text-primary font-medium">{bankLogos[file.bank].name}</span>
                      )}
                      {file.transactionsExtracted > 0 && (
                        <span> • {file.transactionsExtracted} transactions</span>
                      )}
                      <span className="ml-2">
                        {new Date(file.uploadedAt).toLocaleString()}
                      </span>
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {getStatusDisplay(file)}
                    {file.status === 'completed' && file.jsonData && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedFile(file)}
                        className="text-primary hover:text-primary"
                      >
                        <Download className="w-4 h-4 mr-1" />
                        JSON
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <JsonPreviewDialog
        file={selectedFile}
        open={!!selectedFile}
        onOpenChange={(open) => !open && setSelectedFile(null)}
      />
    </div>
  );
}
