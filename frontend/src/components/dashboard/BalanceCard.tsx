import { cn } from '@/lib/utils';
import { Wallet } from 'lucide-react';

interface BalanceCardProps {
  title: string;
  balance: string;
  subtitle?: string;
  className?: string;
}

export function BalanceCard({ title, balance, subtitle, className }: BalanceCardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/10 via-primary/5 to-background p-6 transition-all duration-300 hover:shadow-xl hover:shadow-primary/10",
        className
      )}
    >
      <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full -translate-y-1/2 translate-x-1/2" />
      <div className="relative flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="text-3xl font-bold text-foreground tracking-tight">{balance}</p>
          {subtitle && (
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          )}
        </div>
        <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/20 text-primary">
          <Wallet className="w-7 h-7" />
        </div>
      </div>
    </div>
  );
}
