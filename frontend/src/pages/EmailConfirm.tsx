import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { supabase } from '@/integrations/supabase/client';

/**
 * Email Confirmation Callback Handler
 * 
 * This page handles the redirect from Supabase email confirmation links.
 * It processes the confirmation token and redirects the user appropriately.
 */
export default function EmailConfirm() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Confirming your email...');

  useEffect(() => {
    const handleEmailConfirmation = async () => {
      try {
        // Extract token and type from URL hash (Supabase uses hash fragments)
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');
        const type = hashParams.get('type');
        const error = hashParams.get('error');
        const errorDescription = hashParams.get('error_description');

        // Check for errors in URL
        if (error) {
          setStatus('error');
          setMessage(errorDescription || error || 'Email confirmation failed');
          return;
        }

        // If we have tokens, exchange them for a session
        if (accessToken && refreshToken) {
          const { data, error: sessionError } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });

          if (sessionError) {
            setStatus('error');
            setMessage(sessionError.message || 'Failed to create session');
            return;
          }

          if (data.session) {
            setStatus('success');
            setMessage('Email confirmed successfully! Redirecting to dashboard...');
            
            // Wait a moment to show success message, then redirect
            setTimeout(() => {
              navigate('/dashboard', { replace: true });
            }, 2000);
            return;
          }
        }

        // Fallback: Check if user is already confirmed
        if (user?.email_confirmed_at) {
          setStatus('success');
          setMessage('Your email is already confirmed. Redirecting...');
          setTimeout(() => {
            navigate('/dashboard', { replace: true });
          }, 1500);
          return;
        }

        // If no tokens and user not confirmed, show error
        setStatus('error');
        setMessage('Invalid confirmation link. Please request a new confirmation email.');
      } catch (err: any) {
        console.error('Email confirmation error:', err);
        setStatus('error');
        setMessage(err.message || 'An unexpected error occurred');
      }
    };

    handleEmailConfirmation();
  }, [navigate, user]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md text-center space-y-6">
        {status === 'loading' && (
          <>
            <Loader2 className="w-16 h-16 animate-spin text-primary mx-auto" />
            <h1 className="text-2xl font-bold">Confirming Email</h1>
            <p className="text-muted-foreground">{message}</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto" />
            <h1 className="text-2xl font-bold text-green-600">Email Confirmed!</h1>
            <p className="text-muted-foreground">{message}</p>
            <Button onClick={() => navigate('/dashboard')} className="mt-4">
              Go to Dashboard
            </Button>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-16 h-16 text-destructive mx-auto" />
            <h1 className="text-2xl font-bold text-destructive">Confirmation Failed</h1>
            <p className="text-muted-foreground">{message}</p>
            <div className="flex gap-4 justify-center mt-6">
              <Button variant="outline" onClick={() => navigate('/auth')}>
                Go to Login
              </Button>
              <Button onClick={() => window.location.reload()}>
                Try Again
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

