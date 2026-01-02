import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Download, FileJson, FileSpreadsheet, Copy, Check } from 'lucide-react';
import { toast } from 'sonner';

export function ExportSection() {
  const [format, setFormat] = useState('json');
  const [includeCategories, setIncludeCategories] = useState(true);
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [copied, setCopied] = useState(false);

  const sampleJson = `{
  "exportDate": "2024-01-15T10:30:00Z",
  "accounts": [
    {
      "bank": "HDFC",
      "accountNumber": "****4521",
      "transactions": [
        {
          "date": "2024-01-15",
          "description": "Swiggy Order",
          "amount": -450,
          "category": "food",
          "balance": 125450
        }
      ]
    }
  ],
  "summary": {
    "totalIncome": 100000,
    "totalExpense": 71100,
    "netSavings": 28900
  }
}`;

  const handleExport = () => {
    toast.success(`Exporting data as ${format.toUpperCase()}...`);
    // In real app, trigger download
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(sampleJson);
    setCopied(true);
    toast.success('JSON copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Export Data</h1>
        <p className="text-muted-foreground mt-1">Download your normalized financial data</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Export Settings</CardTitle>
            <CardDescription>Configure your export preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Format</label>
              <Select value={format} onValueChange={setFormat}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="json">
                    <div className="flex items-center gap-2">
                      <FileJson className="w-4 h-4" />
                      JSON
                    </div>
                  </SelectItem>
                  <SelectItem value="csv">
                    <div className="flex items-center gap-2">
                      <FileSpreadsheet className="w-4 h-4" />
                      CSV
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3">
              <label className="text-sm font-medium text-foreground">Include</label>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Checkbox 
                    id="categories" 
                    checked={includeCategories}
                    onCheckedChange={(c) => setIncludeCategories(c as boolean)}
                  />
                  <label htmlFor="categories" className="text-sm text-muted-foreground">
                    Category classifications
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <Checkbox 
                    id="metadata" 
                    checked={includeMetadata}
                    onCheckedChange={(c) => setIncludeMetadata(c as boolean)}
                  />
                  <label htmlFor="metadata" className="text-sm text-muted-foreground">
                    Account metadata
                  </label>
                </div>
              </div>
            </div>

            <Button onClick={handleExport} className="w-full gradient-primary text-primary-foreground">
              <Download className="w-4 h-4 mr-2" />
              Export Data
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>JSON Preview</CardTitle>
              <Button variant="outline" size="sm" onClick={handleCopy}>
                {copied ? <Check className="w-4 h-4 mr-1" /> : <Copy className="w-4 h-4 mr-1" />}
                {copied ? 'Copied!' : 'Copy'}
              </Button>
            </div>
            <CardDescription>Sample of the normalized output format</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="p-4 rounded-lg bg-muted text-sm font-mono overflow-x-auto text-muted-foreground">
              {sampleJson}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
