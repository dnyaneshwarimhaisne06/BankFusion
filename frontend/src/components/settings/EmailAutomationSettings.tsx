import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { flaskApi } from '@/lib/api/flask-api';
import { useToast } from '@/hooks/use-toast';
import { CheckCircle2, Mail } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export function EmailAutomationSettings() {
  const [email, setEmail] = useState('');
  const [isConsentGiven, setIsConsentGiven] = useState(false);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'active' | 'inactive' | 'loading'>('loading');
  const { toast } = useToast();

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await flaskApi.getEmailConsentStatus();
      if (response.success && response.data?.isActive) {
        setStatus('active');
        setEmail(response.data.email);
        setIsConsentGiven(true);
      } else {
        setStatus('inactive');
      }
    } catch (error) {
      console.error('Failed to fetch email status', error);
      setStatus('inactive');
    }
  };

  const handleSave = async () => {
    if (!email || !isConsentGiven) {
      toast({
        title: "Error",
        description: "Please provide an email and grant consent.",
        variant: "destructive"
      });
      return;
    }

    setLoading(true);
    try {
      const response = await flaskApi.saveEmailConsent(email);
      if (response.success) {
        toast({
          title: "Success",
          description: "Email automation enabled successfully.",
        });
      } else {
        toast({
          title: "Error",
          description: response.error || "Failed to save settings.",
          variant: "destructive"
        });
      }
    } catch (error: any) {
      console.error("Error in handleSave:", error);
      toast({
        title: "Error",
        description: error?.message || "An unexpected error occurred.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async () => {
    setLoading(true);
    try {
      const response = await flaskApi.revokeEmailConsent();
      if (response.success) {
        setStatus('inactive');
        setEmail('');
        setIsConsentGiven(false);
        toast({
          title: "Revoked",
          description: "Email automation disabled.",
        });
      } else {
        toast({
          title: "Error",
          description: response.error || "Failed to revoke consent.",
          variant: "destructive"
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "An unexpected error occurred.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-5 w-5" />
          Connect Bank Statements via Email
        </CardTitle>
        <CardDescription>
          Automatically process bank statements sent to our secure inbox.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status === 'active' ? (
          <Alert className="bg-green-50 border-green-200">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertTitle className="text-green-800">Active</AlertTitle>
            <AlertDescription className="text-green-700">
              We are monitoring emails from <strong>{email}</strong>.
            </AlertDescription>
            <Button 
              variant="destructive" 
              size="sm" 
              className="mt-4" 
              onClick={handleRevoke}
              disabled={loading}
            >
              {loading ? 'Revoking...' : 'Revoke Access'}
            </Button>
          </Alert>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                placeholder="mybankstatements@gmail.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />
              <p className="text-sm text-muted-foreground">
                Enter the email address you will forward statements from.
              </p>
            </div>

            <div className="flex items-start space-x-2 pt-2">
              <Checkbox 
                id="consent" 
                checked={isConsentGiven} 
                onCheckedChange={(checked) => setIsConsentGiven(checked as boolean)}
                disabled={loading}
              />
              <div className="grid gap-1.5 leading-none">
                <Label
                  htmlFor="consent"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  I authorize BankFusion to access only bank statement emails sent to/from this address for automated processing.
                </Label>
              </div>
            </div>

            <Button 
              onClick={handleSave} 
              disabled={loading || !email || !isConsentGiven}
              className="w-full sm:w-auto"
            >
              {loading ? 'Saving...' : 'Enable Email Automation'}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
