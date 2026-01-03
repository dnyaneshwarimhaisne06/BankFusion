import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Safely format a date string or Date object
 * Returns a fallback string if the date is invalid
 */
export function safeFormatDate(
  date: string | Date | null | undefined,
  formatString: string,
  fallback: string = 'Date unavailable'
): string {
  if (!date) return fallback;
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    
    // Check if date is valid
    if (isNaN(dateObj.getTime())) {
      return fallback;
    }
    
    return format(dateObj, formatString);
  } catch (error) {
    console.warn('Date formatting error:', error);
    return fallback;
  }
}
