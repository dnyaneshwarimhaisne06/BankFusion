import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, CloudUpload } from 'lucide-react';
import { BankType, UploadedFile } from '@/types';
import { bankLogos } from '@/lib/mockData';
import { toast } from 'sonner';

export function UploadSection() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [selectedBank, setSelectedBank] = useState<BankType>('hdfc');
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    processFiles(droppedFiles);
  }, [selectedBank]);

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

    const newFiles: UploadedFile[] = pdfFiles.map(f => ({
      id: Math.random().toString(36).substr(2, 9),
      name: f.name,
      bank: selectedBank,
      uploadedAt: new Date().toISOString(),
      status: 'processing',
      transactionsExtracted: 0,
    }));

    setFiles(prev => [...newFiles, ...prev]);

    // Simulate processing
    newFiles.forEach((file, index) => {
      setTimeout(() => {
        setFiles(prev => prev.map(f => 
          f.id === file.id 
            ? { ...f, status: 'completed', transactionsExtracted: Math.floor(Math.random() * 50) + 10 }
            : f
        ));
        toast.success(`${file.name} processed successfully!`);
      }, (index + 1) * 2000);
    });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Upload Bank Statements</h1>
        <p className="text-muted-foreground mt-1">Upload PDF statements from your bank accounts</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Bank</CardTitle>
          <CardDescription>Choose the bank for your statement before uploading</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={selectedBank} onValueChange={(v) => setSelectedBank(v as BankType)}>
            <SelectTrigger className="w-full max-w-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(bankLogos).map(([key, value]) => (
                <SelectItem key={key} value={key}>
                  {value.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
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
              or click to browse files
            </p>
            <Button variant="outline">
              <Upload className="w-4 h-4 mr-2" />
              Choose Files
            </Button>
          </div>
        </CardContent>
      </Card>

      {files.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Uploaded Files</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {files.map((file) => (
                <div key={file.id} className="flex items-center gap-4 px-6 py-4">
                  <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                    <FileText className="w-5 h-5 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground truncate">{file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {bankLogos[file.bank].name} • {file.transactionsExtracted > 0 && `${file.transactionsExtracted} transactions`}
                    </p>
                  </div>
                  <div>
                    {file.status === 'processing' && (
                      <div className="flex items-center gap-2 text-warning">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="text-sm font-medium">Processing</span>
                      </div>
                    )}
                    {file.status === 'completed' && (
                      <div className="flex items-center gap-2 text-success">
                        <CheckCircle2 className="w-4 h-4" />
                        <span className="text-sm font-medium">Completed</span>
                      </div>
                    )}
                    {file.status === 'error' && (
                      <div className="flex items-center gap-2 text-destructive">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-sm font-medium">Error</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
