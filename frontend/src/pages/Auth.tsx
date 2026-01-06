import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { Building2, Eye, EyeOff, Loader2, Mail, Lock } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { z } from 'zod';

const emailSchema = z.string().email('Please enter a valid email address');
const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[0-9]/, 'Password must contain at least one number')
  .regex(/[^a-zA-Z0-9]/, 'Password must contain at least one special character');

export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const { signIn, signUp, user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/dashboard';
  const emailVerified = (location.state as any)?.emailVerified;
  const resendConfirmation = (location.state as any)?.resendConfirmation;

  useEffect(() => {
    if (user) {
      navigate(from, { replace: true });
    }
  }, [user, navigate, from]);

  useEffect(() => {
    if (emailVerified) {
      toast({
        title: 'Email Verified!',
        description: 'Your email has been confirmed. You can now log in.',
      });
    }
  }, [emailVerified, toast]);

  useEffect(() => {
    if (resendConfirmation) {
      toast({
        title: 'Resend Confirmation Email',
        description: 'Please enter your email below and we will send a new confirmation link.',
      });
    }
  }, [resendConfirmation, toast]);

  useEffect(() => {
    const tryVerifyFromHash = async () => {
      try {
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');
        const type = hashParams.get('type');
        const error = hashParams.get('error');
        const errorDescription = hashParams.get('error_description');
        const errorCode = hashParams.get('error_code');
        if (error) {
          toast({
            title: 'Verification Failed',
            description:
              errorCode === 'otp_expired'
                ? 'This confirmation link has expired. Please request a new confirmation email.'
                : errorDescription || 'Invalid confirmation link.',
            variant: 'destructive',
          });
          return;
        }
        if (accessToken && refreshToken && (type === 'signup' || type === 'email' || type === 'recovery')) {
          const { data, error: sessionError } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });
          if (sessionError) {
            toast({
              title: 'Verification Failed',
              description: sessionError.message || 'Failed to verify email',
              variant: 'destructive',
            });
            return;
          }
          if (data.session && data.user) {
            if (data.user.email_confirmed_at) {
              await supabase.auth.signOut();
              toast({
                title: 'Email Verified!',
                description: 'Your email has been confirmed. You can now log in.',
              });
              // Clear hash to avoid re-processing
              history.replaceState(null, '', window.location.pathname);
            }
          }
        }
      } catch (_) {
        // ignore
      }
    };
    tryVerifyFromHash();
  }, [toast]);

  const handleResendConfirmation = async () => {
    if (!email) {
      toast({
        title: 'Email Required',
        description: 'Please enter your email address first.',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      // Use production URL from environment, or fallback to current origin if on deployed domain
      let baseUrl = import.meta.env.VITE_APP_URL;
      
      // If VITE_APP_URL not set, use current origin as fallback (but only if not localhost)
      if (!baseUrl) {
        const currentOrigin = window.location.origin;
        if (currentOrigin.includes('localhost') || currentOrigin.includes('127.0.0.1')) {
          toast({
            title: 'Configuration Error',
            description: 'VITE_APP_URL is not configured. Cannot send confirmation email.',
            variant: 'destructive',
          });
          setLoading(false);
          return;
        }
        baseUrl = currentOrigin;
      }

      const { error } = await supabase.auth.resend({
        type: 'signup',
        email: email.trim(),
        options: {
          emailRedirectTo: `${baseUrl}/auth`
        }
      });

      if (error) {
        toast({
          title: 'Failed to Resend',
          description: error.message || 'Could not send confirmation email. Please try again.',
          variant: 'destructive',
        });
      } else {
        toast({
          title: 'Confirmation Email Sent',
          description: 'Please check your email for the new confirmation link.',
        });
      }
    } catch (err: any) {
      toast({
        title: 'Error',
        description: err.message || 'Failed to resend confirmation email.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    try {
      emailSchema.parse(email);
    } catch (e) {
      if (e instanceof z.ZodError) {
        newErrors.email = e.errors[0].message;
      }
    }

    try {
      passwordSchema.parse(password);
    } catch (e) {
      if (e instanceof z.ZodError) {
        newErrors.password = e.errors[0].message;
      }
    }

    if (!isLogin && password !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setLoading(true);

    try {
      if (isLogin) {
        const { data, error } = await signIn(email, password);
        
        if (error) {
          console.error('Login error details:', error);
          
          // Extract error message
          const errorMsg = error.message || 'Login failed';
          let userFriendlyMessage = 'Login failed. Please try again.';
          
          // Map common Supabase errors to user-friendly messages
          if (errorMsg.toLowerCase().includes('invalid login credentials') || 
              errorMsg.toLowerCase().includes('invalid credentials') ||
              errorMsg.toLowerCase().includes('email or password')) {
            userFriendlyMessage = 'Invalid email or password. Please check your credentials and try again.';
          } else if (errorMsg.toLowerCase().includes('email not confirmed') || 
                     errorMsg.toLowerCase().includes('email_not_confirmed') ||
                     errorMsg.toLowerCase().includes('confirm')) {
            userFriendlyMessage = 'Please check your email and confirm your account before logging in.';
          } else if (errorMsg.toLowerCase().includes('user not found') ||
                     errorMsg.toLowerCase().includes('no user found')) {
            userFriendlyMessage = 'No account found with this email. Please sign up first.';
          } else if (errorMsg.toLowerCase().includes('too many requests')) {
            userFriendlyMessage = 'Too many login attempts. Please wait a moment and try again.';
          } else {
            userFriendlyMessage = errorMsg;
          }
          
            toast({
              title: 'Login Failed',
            description: userFriendlyMessage,
              variant: 'destructive',
            });
        } else if (data?.user || data?.session) {
          // Success - user is logged in
          toast({
            title: 'Welcome back!',
            description: 'You have successfully logged in.',
          });
          // Small delay to ensure state is updated
          setTimeout(() => {
          navigate(from, { replace: true });
          }, 100);
        } else {
          // No error but no user data - unexpected state
          toast({
            title: 'Login Failed',
            description: 'Unable to complete login. Please try again.',
            variant: 'destructive',
          });
        }
      } else {
        const { data, error } = await signUp(email, password);
        
        if (error) {
          console.error('Sign up error details:', error);
          
          const errorMsg = error.message || 'Sign up failed';
          let userFriendlyMessage = 'Sign up failed. Please try again.';
          
          if (errorMsg.toLowerCase().includes('already registered') || 
              errorMsg.toLowerCase().includes('user already registered') ||
              errorMsg.toLowerCase().includes('already exists')) {
            userFriendlyMessage = 'This email is already registered. Please log in instead.';
          } else if (errorMsg.toLowerCase().includes('password')) {
            userFriendlyMessage = errorMsg;
          } else if (errorMsg.toLowerCase().includes('email')) {
            userFriendlyMessage = errorMsg;
          } else {
            userFriendlyMessage = errorMsg;
          }
          
          toast({
            title: 'Sign Up Failed',
            description: userFriendlyMessage,
            variant: 'destructive',
          });
        } else if (data?.user) {
          // Check if email confirmation is required
          if (!data.session) {
            toast({
              title: 'Account created!',
              description: 'Please check your email to confirm your account before logging in.',
            });
            // Reset form after successful signup
            setEmail('');
            setPassword('');
            setConfirmPassword('');
            setIsLogin(true); // Switch to login mode
          } else {
            // User is automatically logged in (if email confirmation is disabled)
            toast({
              title: 'Account created!',
              description: 'Welcome to BankFusion. You are now logged in.',
            });
            setTimeout(() => {
              navigate(from, { replace: true });
            }, 100);
          }
        } else {
          toast({
            title: 'Sign Up Failed',
            description: 'Unable to create account. Please try again.',
            variant: 'destructive',
          });
        }
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary to-info opacity-90" />
        <div className="relative z-10 flex flex-col justify-center p-12">
          <div className="flex items-center gap-3 mb-8">
            <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-foreground/20 backdrop-blur">
              <Building2 className="w-7 h-7 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-primary-foreground">FinStatement</h1>
              <p className="text-primary-foreground/80">Bank Analytics Platform</p>
            </div>
          </div>
          <h2 className="text-4xl font-bold text-primary-foreground mb-4">
            Analyze your bank statements with AI-powered insights
          </h2>
          <p className="text-lg text-primary-foreground/80">
            Upload your bank statements, get categorized transactions, and visualize your spending patterns with beautiful charts.
          </p>
          <div className="mt-12 grid grid-cols-2 gap-6">
            <div className="p-4 rounded-xl bg-primary-foreground/10 backdrop-blur">
              <p className="text-3xl font-bold text-primary-foreground">₹10Cr+</p>
              <p className="text-primary-foreground/80">Transactions Analyzed</p>
            </div>
            <div className="p-4 rounded-xl bg-primary-foreground/10 backdrop-blur">
              <p className="text-3xl font-bold text-primary-foreground">50+</p>
              <p className="text-primary-foreground/80">Banks Supported</p>
            </div>
          </div>
        </div>
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-primary-foreground/10 rounded-full blur-3xl" />
        <div className="absolute -top-24 -left-24 w-72 h-72 bg-accent/20 rounded-full blur-3xl" />
      </div>

      {/* Right side - Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-3 mb-8 lg:hidden">
            <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary text-primary-foreground">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold">FinStatement</h1>
              <p className="text-sm text-muted-foreground">Bank Analytics</p>
            </div>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-foreground">
              {isLogin ? 'Welcome back' : 'Create your account'}
            </h2>
            <p className="text-muted-foreground mt-2">
              {isLogin
                ? 'Enter your credentials to access your dashboard'
                : 'Get started with your bank statement analytics'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10"
                  disabled={loading}
                />
              </div>
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 pr-10"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password}</p>
              )}
              {!isLogin && (
                <p className="text-xs text-muted-foreground">
                  Min 8 characters, 1 number, 1 special character
                </p>
              )}
            </div>

            {!isLogin && (
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="pl-10"
                    disabled={loading}
                  />
                </div>
                {errors.confirmPassword && (
                  <p className="text-sm text-destructive">{errors.confirmPassword}</p>
                )}
              </div>
            )}

            <Button type="submit" className="w-full" size="lg" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isLogin ? 'Signing in...' : 'Creating account...'}
                </>
              ) : (
                <>{isLogin ? 'Sign In' : 'Create Account'}</>
              )}
            </Button>
          </form>

          <div className="mt-6 space-y-3">
            <div className="text-center">
            <p className="text-muted-foreground">
              {isLogin ? "Don't have an account?" : 'Already have an account?'}
              <button
                type="button"
                onClick={() => {
                  setIsLogin(!isLogin);
                  setErrors({});
                }}
                className="ml-2 text-primary hover:underline font-medium"
              >
                {isLogin ? 'Sign up' : 'Sign in'}
              </button>
            </p>
            </div>
            {isLogin && (
              <div className="text-center">
                <button
                  type="button"
                  onClick={handleResendConfirmation}
                  disabled={loading || !email}
                  className="text-sm text-muted-foreground hover:text-primary hover:underline font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Resend confirmation email
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
