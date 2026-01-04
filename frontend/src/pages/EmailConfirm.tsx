import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { supabase } from '@/integrations/supabase/client';

/**
 * Email Confirmation Callback Handler
 * 
 * This page handles the redirect from Supabase email confirmation links.
 * It verifies the email but does NOT auto-login the user.
 * User must manually log in after verification.
 */
export default function EmailConfirm() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Verifying your email...');

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
          setMessage(errorDescription || error || 'Email verification failed');
          return;
        }

        // If we have tokens, verify the email by exchanging tokens
        // But we'll immediately sign out to prevent auto-login
        if (accessToken && refreshToken) {
          const { data, error: sessionError } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });

          if (sessionError) {
            setStatus('error');
            setMessage(sessionError.message || 'Failed to verify email');
            return;
          }

          if (data.session && data.user) {
            // Verify that email is actually confirmed
            if (data.user.email_confirmed_at) {
              // Email is confirmed, now sign out so user must manually log in
              await supabase.auth.signOut();
              
              setStatus('success');
              setMessage('Email verified successfully. Please log in.');
              
              // Redirect to login page after showing success message
              setTimeout(() => {
                navigate('/auth', { replace: true, state: { emailVerified: true } });
              }, 2000);
              return;
            } else {
              // Email not confirmed yet, wait a bit and check again
              await new Promise(resolve => setTimeout(resolve, 1000));
              const { data: { user: updatedUser } } = await supabase.auth.getUser();
              
              if (updatedUser?.email_confirmed_at) {
                await supabase.auth.signOut();
                setStatus('success');
                setMessage('Email verified successfully. Please log in.');
                setTimeout(() => {
                  navigate('/auth', { replace: true, state: { emailVerified: true } });
                }, 2000);
                return;
              } else {
                setStatus('error');
                setMessage('Email verification is processing. Please wait a moment and try logging in.');
                setTimeout(() => {
                  navigate('/auth', { replace: true });
                }, 3000);
                return;
              }
            }
          }
        }

        // If no tokens, show error
        setStatus('error');
        setMessage('Invalid verification link. Please request a new confirmation email.');
      } catch (err: any) {
        console.error('Email verification error:', err);
        setStatus('error');
        setMessage(err.message || 'An unexpected error occurred');
      }
    };

    handleEmailConfirmation();
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md text-center space-y-6">
        {status === 'loading' && (
          <>
            <Loader2 className="w-16 h-16 animate-spin text-primary mx-auto" />
            <h1 className="text-2xl font-bold">Verifying Email</h1>
            <p className="text-muted-foreground">{message}</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto" />
            <h1 className="text-2xl font-bold text-green-600">Email Verified!</h1>
            <p className="text-muted-foreground">{message}</p>
            <Button onClick={() => navigate('/auth', { replace: true })} className="mt-4">
              Go to Login
            </Button>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-16 h-16 text-destructive mx-auto" />
            <h1 className="text-2xl font-bold text-destructive">Verification Failed</h1>
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

