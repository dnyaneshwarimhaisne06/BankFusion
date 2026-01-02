import { Card, CardContent } from '@/components/ui/card';
import { BankAccount } from '@/types';
import { bankLogos } from '@/lib/mockData';
import { Building2 } from 'lucide-react';

interface BankAccountCardProps {
  account: BankAccount;
}

export function BankAccountCard({ account }: BankAccountCardProps) {
  const bankInfo = bankLogos[account.bank];

  return (
    <Card className="group hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
      <CardContent className="p-5">
        <div className="flex items-center gap-4">
          <div 
            className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ backgroundColor: `${bankInfo.color}20` }}
          >
            <Building2 
              className="w-6 h-6" 
              style={{ color: bankInfo.color }}
            />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-card-foreground">{bankInfo.name}</h3>
              <span className="text-xs text-muted-foreground">{account.accountNumber}</span>
            </div>
            <p className="text-2xl font-bold text-card-foreground mt-1">
              ₹{account.balance.toLocaleString('en-IN')}
            </p>
            <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
              <span>{account.transactionCount} transactions</span>
              <span>•</span>
              <span>Updated {account.lastUpdated}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
