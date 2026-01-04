import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, XCircle, Loader2, Mail } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { supabase } from '@/integrations/supabase/client';

/**
 * Email Verification Success Page
 * 
 * This page is shown after user clicks the email confirmation link.
 * It verifies the email and asks the user to log in manually.
 */
export default function EmailVerified() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Verifying your email...');

  useEffect(() => {
    const handleEmailVerification = async () => {
      try {
        // Extract token and type from URL hash (Supabase uses hash fragments)
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');
        const type = hashParams.get('type');
        const error = hashParams.get('error');
        const errorDescription = hashParams.get('error_description');

        // Get error_code first
        const error_code = hashParams.get('error_code');
        
        // Check for errors in URL
        if (error) {
          setStatus('error');
          let errorMsg = errorDescription || error || 'Email verification failed';
          
          // Handle specific error cases
          if (error === 'access_denied' || error_code === 'otp_expired') {
            errorMsg = 'This confirmation link has expired. Please request a new confirmation email from the login page.';
          } else if (error === 'invalid_token' || error_code === 'invalid_token') {
            errorMsg = 'Invalid confirmation link. Please request a new confirmation email.';
          }
          
          setMessage(errorMsg);
          return;
        }

        // If we have tokens, verify the email by setting the session
        // Accept both 'signup' and 'email' types
        if (accessToken && refreshToken && (type === 'signup' || type === 'email' || type === 'recovery')) {
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
              setMessage('Email verified successfully! You can now log in.');
              return;
            } else {
              // Wait a moment and check again
              await new Promise(resolve => setTimeout(resolve, 1000));
              const { data: { user: updatedUser } } = await supabase.auth.getUser();
              
              if (updatedUser?.email_confirmed_at) {
                await supabase.auth.signOut();
                setStatus('success');
                setMessage('Email verified successfully! You can now log in.');
                return;
              } else {
                setStatus('error');
                setMessage('Email verification is processing. Please wait a moment and try logging in.');
                return;
              }
            }
          }
        }

        // If no tokens, check if we can verify from current session
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.user?.email_confirmed_at) {
          await supabase.auth.signOut();
          setStatus('success');
          setMessage('Email verified successfully! You can now log in.');
          return;
        }

        // If we get here, verification failed
        setStatus('error');
        setMessage('Invalid verification link. Please request a new confirmation email.');
      } catch (err: any) {
        console.error('Email verification error:', err);
        setStatus('error');
        setMessage(err.message || 'An unexpected error occurred');
      }
    };

    handleEmailVerification();
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md p-8 text-center space-y-6">
        {status === 'loading' && (
          <>
            <Loader2 className="w-16 h-16 animate-spin text-primary mx-auto" />
            <h1 className="text-2xl font-bold">Verifying Email</h1>
            <p className="text-muted-foreground">{message}</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="w-16 h-16 mx-auto rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
              <CheckCircle2 className="w-10 h-10 text-green-600 dark:text-green-400" />
            </div>
            <h1 className="text-2xl font-bold text-green-600 dark:text-green-400">Email Verified!</h1>
            <p className="text-muted-foreground">{message}</p>
            <div className="pt-4">
              <Button onClick={() => navigate('/auth', { replace: true })} className="w-full">
                Go to Login
              </Button>
            </div>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="w-16 h-16 mx-auto rounded-full bg-destructive/10 flex items-center justify-center">
              <XCircle className="w-10 h-10 text-destructive" />
            </div>
            <h1 className="text-2xl font-bold text-destructive">Verification Failed</h1>
            <p className="text-muted-foreground">{message}</p>
            <div className="space-y-3 pt-4">
              <div className="flex gap-3 justify-center">
                <Button variant="outline" onClick={() => navigate('/auth')}>
                  Go to Login
                </Button>
                <Button onClick={async () => {
                  // Try to resend confirmation email
                  const hashParams = new URLSearchParams(window.location.hash.substring(1));
                  // Extract email from URL if possible, or ask user to go to login
                  navigate('/auth', { state: { resendConfirmation: true } });
                }}>
                  Request New Link
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                If the link expired, go to login page and click "Resend confirmation email"
              </p>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

