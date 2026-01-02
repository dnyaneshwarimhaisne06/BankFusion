import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Download, Copy, Check } from 'lucide-react';
import { ProcessedFile } from '@/contexts/UploadContext';
import { useState } from 'react';
import { toast } from 'sonner';

interface JsonPreviewDialogProps {
  file: ProcessedFile | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function JsonPreviewDialog({ file, open, onOpenChange }: JsonPreviewDialogProps) {
  const [copied, setCopied] = useState(false);

  if (!file || !file.jsonData) return null;

  const jsonString = JSON.stringify(file.jsonData, null, 2);

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${file.name.replace('.pdf', '')}_normalized.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('JSON file downloaded');
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(jsonString);
    setCopied(true);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Extracted JSON Data
          </DialogTitle>
          <DialogDescription>
            {file.name} • {file.bank?.toUpperCase()} Bank
          </DialogDescription>
        </DialogHeader>

        <div className="flex gap-2 mb-4">
          <Button onClick={handleDownload} className="gradient-primary">
            <Download className="w-4 h-4 mr-2" />
            Download JSON
          </Button>
          <Button variant="outline" onClick={handleCopy}>
            {copied ? (
              <>
                <Check className="w-4 h-4 mr-2" />
                Copied
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 mr-2" />
                Copy
              </>
            )}
          </Button>
        </div>

        <ScrollArea className="flex-1 rounded-lg border border-border bg-muted/30">
          <pre className="p-4 text-sm font-mono text-foreground whitespace-pre-wrap break-words">
            {jsonString}
          </pre>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
