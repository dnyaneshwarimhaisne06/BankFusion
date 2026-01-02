import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Transaction } from '@/types';
import { categoryColors, bankLogos } from '@/lib/mockData';
import { ArrowUpRight, ArrowDownLeft } from 'lucide-react';

interface RecentTransactionsProps {
  transactions: Transaction[];
}

export function RecentTransactions({ transactions }: RecentTransactionsProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold">Recent Transactions</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border">
          {transactions.slice(0, 6).map((tx) => (
            <div 
              key={tx.id} 
              className="flex items-center gap-4 px-6 py-4 hover:bg-muted/50 transition-colors"
            >
              <div 
                className="w-10 h-10 rounded-full flex items-center justify-center"
                style={{ backgroundColor: `${categoryColors[tx.category]}20` }}
              >
                {tx.type === 'credit' ? (
                  <ArrowDownLeft 
                    className="w-5 h-5" 
                    style={{ color: categoryColors[tx.category] }}
                  />
                ) : (
                  <ArrowUpRight 
                    className="w-5 h-5" 
                    style={{ color: categoryColors[tx.category] }}
                  />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-card-foreground truncate">{tx.description}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                  <span className="capitalize">{tx.category}</span>
                  <span>•</span>
                  <span>{bankLogos[tx.bank].name}</span>
                  <span>•</span>
                  <span>{tx.date}</span>
                </div>
              </div>
              <p className={`font-semibold ${tx.type === 'credit' ? 'text-success' : 'text-foreground'}`}>
                {tx.type === 'credit' ? '+' : '-'}₹{tx.amount.toLocaleString('en-IN')}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
