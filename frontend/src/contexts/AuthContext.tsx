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
  updatePassword: (newPassword: string) => Promise<{ error: Error | null }>;
  deleteAccount: () => Promise<{ error: Error | null }>;
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
    try {
      // Trim email to avoid whitespace issues
      const trimmedEmail = email.trim();
      
      if (!trimmedEmail || !password) {
        return { 
          data: null, 
          error: new Error('Email and password are required') 
        };
      }

      // Use production URL from environment variable, or fallback to current origin if on deployed domain
      // Only fail if on localhost without VITE_APP_URL configured
      let baseUrl = import.meta.env.VITE_APP_URL;
      
      // If VITE_APP_URL not set, use current origin as fallback (but only if not localhost)
      if (!baseUrl) {
        const currentOrigin = window.location.origin;
        // Only allow fallback if we're on a deployed domain (not localhost)
        if (currentOrigin.includes('localhost') || currentOrigin.includes('127.0.0.1')) {
          console.error('VITE_APP_URL is not configured and running on localhost. Email confirmation will not work.');
          return { 
            data: null, 
            error: new Error('Email redirect URL not configured. Please set VITE_APP_URL in environment variables.') 
          };
        }
        // Use current origin as fallback for deployed domains
        baseUrl = currentOrigin;
        console.warn('VITE_APP_URL not set, using current origin as fallback:', baseUrl);
      }
      
      // Redirect to email verified page for clear confirmation UX
      const redirectUrl = `${baseUrl}/auth/verified`;
    
      const { data, error } = await supabase.auth.signUp({
        email: trimmedEmail,
      password,
      options: {
        emailRedirectTo: redirectUrl
      }
    });
    
      // If successful and session exists, update user state
      if (data?.session) {
        setSession(data.session);
        setUser(data.user);
      }
      
      // Convert Supabase error to Error object if present
      if (error) {
        console.error('Sign up error:', error);
        return { 
          data: null, 
          error: new Error(error.message || 'Sign up failed') 
        };
      }
      
      return { data, error: null };
    } catch (err: any) {
      console.error('Sign up exception:', err);
      return { 
        data: null, 
        error: new Error(err.message || 'An unexpected error occurred during sign up') 
      };
    }
  };

  const signIn = async (email: string, password: string) => {
    try {
      // Trim email to avoid whitespace issues
      const trimmedEmail = email.trim();
      
      if (!trimmedEmail || !password) {
        return { 
          data: null, 
          error: new Error('Email and password are required') 
        };
      }

      const { data, error } = await supabase.auth.signInWithPassword({
        email: trimmedEmail,
      password,
    });
    
      // Check if email is confirmed
      if (data?.user && !data.user.email_confirmed_at) {
        // Sign out immediately if email not confirmed
        await supabase.auth.signOut();
        return { 
          data: null, 
          error: new Error('Please verify your email before logging in. Check your inbox for the confirmation link.') 
        };
      }
      
      // If successful, update user state immediately
      if (data?.session) {
        setSession(data.session);
        setUser(data.user);
      }
      
      // Convert Supabase error to Error object if present
      if (error) {
        console.error('Sign in error:', error);
        return { 
          data: null, 
          error: new Error(error.message || 'Login failed') 
        };
      }
      
      return { data, error: null };
    } catch (err: any) {
      console.error('Sign in exception:', err);
      return { 
        data: null, 
        error: new Error(err.message || 'An unexpected error occurred during login') 
      };
    }
  };

  const signOut = async () => {
    try {
      await supabase.auth.signOut();
      setSession(null);
      setUser(null);
      // Clear all cached data on logout
      localStorage.clear();
      sessionStorage.clear();
    } catch (error) {
      console.error('Sign out error:', error);
      // Still clear local state even if signout fails
      setSession(null);
      setUser(null);
      localStorage.clear();
      sessionStorage.clear();
    }
  };

  const updatePassword = async (newPassword: string) => {
    try {
      if (!newPassword || newPassword.length < 8) {
        return { error: new Error('Password must be at least 8 characters') };
      }

      const { error } = await supabase.auth.updateUser({
        password: newPassword
      });

      if (error) {
        console.error('Update password error:', error);
        return { error: new Error(error.message || 'Failed to update password') };
      }

      return { error: null };
    } catch (err: any) {
      console.error('Update password exception:', err);
      return { error: new Error(err.message || 'An unexpected error occurred') };
    }
  };

  const deleteAccount = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session?.access_token) {
        return { error: new Error('No active session. Please log in again.') };
      }

      // Call backend to delete user data from MongoDB and Supabase
      // Use VITE_FLASK_API_URL which already includes /api prefix
      const apiBaseUrl = import.meta.env.VITE_FLASK_API_URL;
      if (!apiBaseUrl) {
        return { error: new Error('Backend API URL not configured') };
      }
      const response = await fetch(`${apiBaseUrl}/account/delete`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.error || `Failed to delete account (${response.status})`;
        console.error('Delete account failed:', errorMessage);
        return { error: new Error(errorMessage) };
      }

      // Clear local session immediately
      setSession(null);
      setUser(null);
      
      // Sign out from Supabase (account should already be deleted, but clear local storage)
      try {
    await supabase.auth.signOut();
      } catch (signOutError) {
        // Ignore sign out errors - account is already deleted
        console.log('Sign out after deletion (expected):', signOutError);
      }
      
      // Clear all local storage
      localStorage.clear();
      sessionStorage.clear();
      
      return { error: null };
    } catch (err: any) {
      console.error('Delete account error:', err);
      return { error: new Error(err.message || 'Failed to delete account') };
    }
  };

  return (
    <AuthContext.Provider value={{ user, session, loading, signUp, signIn, signOut, updatePassword, deleteAccount }}>
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
