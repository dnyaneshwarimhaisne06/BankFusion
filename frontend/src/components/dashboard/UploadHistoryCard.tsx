import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, CheckCircle2, AlertCircle, Loader2, ChevronRight } from 'lucide-react';
import { useUpload } from '@/contexts/UploadContext';
import { bankLogos } from '@/lib/mockData';
import { useNavigate } from 'react-router-dom';

export function UploadHistoryCard() {
  const { files } = useUpload();
  const navigate = useNavigate();
  const recentFiles = files.slice(0, 5);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-success/20 text-success border-success/30">Success</Badge>;
      case 'processing':
      case 'detecting':
      case 'uploading':
        return <Badge variant="secondary" className="bg-warning/20 text-warning border-warning/30">Processing</Badge>;
      case 'error':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return null;
    }
  };

  if (files.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Recent Uploads
            <Button variant="ghost" size="sm" onClick={() => navigate('/upload')}>
              Upload <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p>No statements uploaded yet</p>
            <Button variant="link" onClick={() => navigate('/upload')} className="mt-2">
              Upload your first statement
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Recent Uploads
          <Button variant="ghost" size="sm" onClick={() => navigate('/upload')}>
            View All <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border">
          {recentFiles.map((file) => (
            <div key={file.id} className="flex items-center gap-3 px-6 py-3">
              <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center shrink-0">
                <FileText className="w-4 h-4 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {file.bank && bankLogos[file.bank] && (
                    <span className="text-primary">{bankLogos[file.bank].name}</span>
                  )}
                  <span className="ml-2">{new Date(file.uploadedAt).toLocaleDateString()}</span>
                </p>
              </div>
              {getStatusBadge(file.status)}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
