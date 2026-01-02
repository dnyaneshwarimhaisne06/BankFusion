import { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  variant?: 'default' | 'primary' | 'accent';
  className?: string;
}

export function StatCard({ 
  title, 
  value, 
  subtitle, 
  icon, 
  trend, 
  variant = 'default',
  className 
}: StatCardProps) {
  return (
    <Card className={cn(
      "relative overflow-hidden transition-all duration-300 hover:shadow-lg",
      variant === 'primary' && "gradient-primary text-primary-foreground",
      variant === 'accent' && "gradient-accent text-accent-foreground",
      className
    )}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className={cn(
              "text-sm font-medium",
              variant === 'default' ? "text-muted-foreground" : "opacity-90"
            )}>
              {title}
            </p>
            <p className="text-3xl font-bold tracking-tight">{value}</p>
            {subtitle && (
              <p className={cn(
                "text-sm",
                variant === 'default' ? "text-muted-foreground" : "opacity-80"
              )}>
                {subtitle}
              </p>
            )}
            {trend && (
              <div className={cn(
                "inline-flex items-center gap-1 text-sm font-medium",
                trend.isPositive ? "text-success" : "text-destructive"
              )}>
                <span>{trend.isPositive ? '↑' : '↓'}</span>
                <span>{Math.abs(trend.value)}%</span>
                <span className="text-muted-foreground font-normal">vs last month</span>
              </div>
            )}
          </div>
          <div className={cn(
            "p-3 rounded-xl",
            variant === 'default' ? "bg-secondary" : "bg-background/20"
          )}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
