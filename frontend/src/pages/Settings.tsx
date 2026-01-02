import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useAuth } from '@/contexts/AuthContext';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { User, Mail, Calendar, Shield } from 'lucide-react';
import { format } from 'date-fns';

export default function Settings() {
  const { user } = useAuth();

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        {/* Page header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">Settings</h1>
          <p className="text-muted-foreground">
            Manage your account settings and preferences
          </p>
        </div>

        {/* Profile section */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <User className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Profile</h2>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 rounded-xl bg-secondary/50">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 text-primary text-lg font-bold">
                {user?.email?.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="font-medium text-foreground">{user?.email}</p>
                <p className="text-sm text-muted-foreground">Account Email</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 rounded-xl bg-secondary/50">
              <Mail className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="font-medium text-foreground">{user?.email}</p>
                <p className="text-sm text-muted-foreground">Email Address</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 rounded-xl bg-secondary/50">
              <Calendar className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="font-medium text-foreground">
                  {user?.created_at 
                    ? format(new Date(user.created_at), 'dd MMM yyyy') 
                    : 'N/A'}
                </p>
                <p className="text-sm text-muted-foreground">Member Since</p>
              </div>
            </div>
          </div>
        </Card>

        {/* Security section */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <Shield className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Security</h2>
          </div>
          
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-secondary/50">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-foreground">Password</p>
                  <p className="text-sm text-muted-foreground">Last updated: Never</p>
                </div>
                <Button variant="outline" size="sm" disabled>
                  Change Password
                </Button>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-success/5 border border-success/20">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-success" />
                <p className="text-sm font-medium text-success">Account Secure</p>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Your account is protected with email authentication
              </p>
            </div>
          </div>
        </Card>

        {/* Data section */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-foreground mb-4">Data & Privacy</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Your bank statements and transaction data are securely stored and only accessible by you.
          </p>
          <div className="flex gap-3">
            <Button variant="outline" size="sm" disabled>
              Export All Data
            </Button>
            <Button variant="outline" size="sm" className="text-destructive hover:bg-destructive/10" disabled>
              Delete Account
            </Button>
          </div>
        </Card>
      </div>
    </DashboardLayout>
  );
}
