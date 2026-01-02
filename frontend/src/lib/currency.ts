// Indian currency formatting utilities

export function formatINR(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return '₹0.00';
  
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatINRCompact(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return '₹0';
  
  const absAmount = Math.abs(amount);
  const sign = amount < 0 ? '-' : '';
  
  if (absAmount >= 10000000) {
    return `${sign}₹${(absAmount / 10000000).toFixed(2)}Cr`;
  } else if (absAmount >= 100000) {
    return `${sign}₹${(absAmount / 100000).toFixed(2)}L`;
  } else if (absAmount >= 1000) {
    return `${sign}₹${(absAmount / 1000).toFixed(2)}K`;
  }
  
  return formatINR(amount);
}

export function parseINR(value: string): number {
  const cleaned = value.replace(/[₹,\s]/g, '');
  return parseFloat(cleaned) || 0;
}
