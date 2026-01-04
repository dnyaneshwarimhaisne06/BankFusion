import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signUp: (email: string, password: string) => Promise<{ data: any; error: Error | null }>;
  signIn: (email: string, password: string) => Promise<{ data: any; error: Error | null }>;
  signOut: () => Promise<void>;
  changePassword: (newPassword: string) => Promise<{ error: Error | null }>;
  deleteAccount: () => Promise<{ error: Error | null }>;
  resendConfirmationEmail: (email: string) => Promise<{ error: Error | null }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      // Set up auth state listener FIRST
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        (event, session) => {
          console.log('Auth state changed:', event, session?.user?.email);
          setSession(session);
          setUser(session?.user ?? null);
          setLoading(false);
        }
      );

      // THEN check for existing session
      supabase.auth.getSession().then(({ data: { session } }) => {
        setSession(session);
        setUser(session?.user ?? null);
        setLoading(false);
      }).catch((error) => {
        console.warn('Failed to get session:', error);
        setLoading(false);
      });

      return () => subscription.unsubscribe();
    } catch (error) {
      console.error('Auth context initialization error:', error);
      setLoading(false);
    }
  }, []);

  const signUp = async (email: string, password: string) => {
    // Get the base URL from environment or use current origin
    // In production, this should be your deployed domain
    // In development, this will be localhost
    const baseUrl = import.meta.env.VITE_APP_URL || window.location.origin;
    // Use /auth/confirm as it's likely configured in Supabase dashboard
    // Both /auth/confirm and /auth/verify now work the same way
    const redirectUrl = `${baseUrl}/auth/confirm`;
    
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: redirectUrl
      }
    });
    
    // Don't auto-login after signup - user must verify email first
    // Session will be null until email is confirmed
    
    return { data, error: error as Error | null };
  };

  const signIn = async (email: string, password: string) => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      
      // If there's an error, return it
      if (error) {
        return { data: null, error: error as Error };
      }
      
      // If successful, verify email is confirmed
      if (data?.session && data?.user) {
        // Check if email is confirmed
        if (!data.user.email_confirmed_at) {
          // Sign out if email not confirmed
          await supabase.auth.signOut();
          setSession(null);
          setUser(null);
          return { 
            data: null, 
            error: new Error('Please check your email and confirm your account before logging in.') 
          };
        }
        
        // Email is confirmed, update state
        setSession(data.session);
        setUser(data.user);
      }
      
      return { data, error: null };
    } catch (err: any) {
      return { data: null, error: err as Error };
    }
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setSession(null);
    setUser(null);
  };

  const changePassword = async (newPassword: string) => {
    const { error } = await supabase.auth.updateUser({
      password: newPassword
    });
    return { error: error as Error | null };
  };

  const resendConfirmationEmail = async (email: string) => {
    try {
      const baseUrl = import.meta.env.VITE_APP_URL || window.location.origin;
      // Use /auth/confirm to match signup redirect
      const redirectUrl = `${baseUrl}/auth/confirm`;
      
      // Use the resend method - this works even if user is not logged in
      const { error } = await supabase.auth.resend({
        type: 'signup',
        email: email,
        options: {
          emailRedirectTo: redirectUrl
        }
      });
      
      if (error) {
        return { error: error as Error };
      }
      
      return { error: null };
    } catch (err: any) {
      return { error: err as Error };
    }
  };

  const deleteAccount = async () => {
    if (!user?.id) {
      return { error: new Error('No user found') };
    }

    try {
      // Get the current session token
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        return { error: new Error('No active session') };
      }

      // Call backend endpoint to delete account
      // Backend will handle Supabase user deletion and MongoDB data cleanup
      const backendUrl = import.meta.env.VITE_FLASK_API_URL || 'http://localhost:5000';
      const response = await fetch(`${backendUrl}/api/account/delete`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return { error: new Error(errorData.error || 'Failed to delete account') };
      }

      // Sign out after successful deletion
      await signOut();
      return { error: null };
    } catch (err: any) {
      return { error: err as Error };
    }
  };

  return (
    <AuthContext.Provider value={{ user, session, loading, signUp, signIn, signOut, changePassword, deleteAccount, resendConfirmationEmail }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
