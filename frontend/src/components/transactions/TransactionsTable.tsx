import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Search, Filter, ArrowUpRight, ArrowDownLeft, Edit2, Check, X } from 'lucide-react';
import { Transaction, TransactionCategory, BankType } from '@/types';
import { mockTransactions, categoryColors, bankLogos } from '@/lib/mockData';
import { toast } from 'sonner';

const categories: TransactionCategory[] = [
  'food', 'travel', 'rent', 'utilities', 'shopping', 
  'entertainment', 'healthcare', 'salary', 'transfer', 'investment', 'other'
];

export function TransactionsTable() {
  const [transactions, setTransactions] = useState<Transaction[]>(mockTransactions);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterBank, setFilterBank] = useState<string>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editCategory, setEditCategory] = useState<TransactionCategory>('other');

  const filteredTransactions = transactions.filter(tx => {
    const matchesSearch = tx.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesBank = filterBank === 'all' || tx.bank === filterBank;
    const matchesCategory = filterCategory === 'all' || tx.category === filterCategory;
    return matchesSearch && matchesBank && matchesCategory;
  });

  const handleEdit = (tx: Transaction) => {
    setEditingId(tx.id);
    setEditCategory(tx.category);
  };

  const handleSave = (id: string) => {
    setTransactions(prev => prev.map(tx => 
      tx.id === id ? { ...tx, category: editCategory, isEdited: true } : tx
    ));
    setEditingId(null);
    toast.success('Category updated! AI will learn from this correction.');
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Transactions</h1>
        <p className="text-muted-foreground mt-1">Unified view of all your bank transactions</p>
      </div>

      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input 
                placeholder="Search transactions..." 
                className="pl-10"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Select value={filterBank} onValueChange={setFilterBank}>
                <SelectTrigger className="w-[140px]">
                  <Filter className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Bank" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Banks</SelectItem>
                  {Object.entries(bankLogos).map(([key, value]) => (
                    <SelectItem key={key} value={key}>{value.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filterCategory} onValueChange={setFilterCategory}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {categories.map(cat => (
                    <SelectItem key={cat} value={cat} className="capitalize">{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Bank</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTransactions.map((tx) => (
                  <TableRow key={tx.id} className="group">
                    <TableCell className="text-muted-foreground">{tx.date}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div 
                          className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                          style={{ backgroundColor: `${categoryColors[tx.category]}20` }}
                        >
                          {tx.type === 'credit' ? (
                            <ArrowDownLeft className="w-4 h-4" style={{ color: categoryColors[tx.category] }} />
                          ) : (
                            <ArrowUpRight className="w-4 h-4" style={{ color: categoryColors[tx.category] }} />
                          )}
                        </div>
                        <span className="font-medium">{tx.description}</span>
                        {tx.isEdited && (
                          <Badge variant="secondary" className="text-xs">Corrected</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{bankLogos[tx.bank].name}</Badge>
                    </TableCell>
                    <TableCell>
                      {editingId === tx.id ? (
                        <Select value={editCategory} onValueChange={(v) => setEditCategory(v as TransactionCategory)}>
                          <SelectTrigger className="w-[120px] h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {categories.map(cat => (
                              <SelectItem key={cat} value={cat} className="capitalize">{cat}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <Badge 
                          className="capitalize"
                          style={{ 
                            backgroundColor: `${categoryColors[tx.category]}20`,
                            color: categoryColors[tx.category]
                          }}
                        >
                          {tx.category}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className={`text-right font-semibold ${tx.type === 'credit' ? 'text-success' : ''}`}>
                      {tx.type === 'credit' ? '+' : '-'}₹{tx.amount.toLocaleString('en-IN')}
                    </TableCell>
                    <TableCell className="text-right">
                      {editingId === tx.id ? (
                        <div className="flex items-center justify-end gap-1">
                          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => handleSave(tx.id)}>
                            <Check className="w-4 h-4 text-success" />
                          </Button>
                          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => setEditingId(null)}>
                            <X className="w-4 h-4 text-destructive" />
                          </Button>
                        </div>
                      ) : (
                        <Button 
                          size="icon" 
                          variant="ghost" 
                          className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={() => handleEdit(tx)}
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
