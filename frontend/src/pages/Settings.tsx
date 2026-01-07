import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useAuth } from '@/contexts/AuthContext';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog';
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { User, Mail, Calendar, Shield, Loader2 } from 'lucide-react';
import { safeFormatDate } from '@/lib/utils';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

export default function Settings() {
  const { user, updatePassword, deleteAccount } = useAuth();
  const navigate = useNavigate();
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const [deleteAccountOpen, setDeleteAccountOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

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
                  {safeFormatDate(user?.created_at, 'dd MMM yyyy', 'N/A')}
                </p>
                <p className="text-sm text-muted-foreground">Member Since</p>
              </div>
            </div>
          </div>
        </Card>

        {/* Email Automation Section */}
        <EmailAutomationSettings />

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
                <Button variant="outline" size="sm" onClick={() => setChangePasswordOpen(true)}>
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
            <Button 
              variant="outline" 
              size="sm" 
              className="text-destructive hover:bg-destructive/10" 
              onClick={() => setDeleteAccountOpen(true)}
            >
              Delete Account
            </Button>
          </div>
        </Card>

        {/* Change Password Dialog */}
        <Dialog open={changePasswordOpen} onOpenChange={setChangePasswordOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Change Password</DialogTitle>
              <DialogDescription>
                Enter your new password. It must be at least 8 characters long.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="newPassword">New Password</Label>
                <Input
                  id="newPassword"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  disabled={loading}
                />
              </div>
            </div>
            <DialogFooter>
              <Button 
                variant="outline" 
                onClick={() => {
                  setChangePasswordOpen(false);
                  setNewPassword('');
                  setConfirmPassword('');
                }}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button 
                onClick={async () => {
                  if (!newPassword || newPassword.length < 8) {
                    toast.error('Password must be at least 8 characters');
                    return;
                  }
                  if (newPassword !== confirmPassword) {
                    toast.error('Passwords do not match');
                    return;
                  }
                  
                  setLoading(true);
                  const { error } = await updatePassword(newPassword);
                  
                  if (error) {
                    toast.error(error.message || 'Failed to update password');
                  } else {
                    toast.success('Password updated successfully');
                    setChangePasswordOpen(false);
                    setNewPassword('');
                    setConfirmPassword('');
                  }
                  setLoading(false);
                }}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Updating...
                  </>
                ) : (
                  'Update Password'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Account Dialog */}
        <AlertDialog open={deleteAccountOpen} onOpenChange={setDeleteAccountOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently delete your account
                and remove all your data including bank statements and transactions from our servers.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={loading}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={async () => {
                  setLoading(true);
                  const { error } = await deleteAccount();
                  
                  if (error) {
                    toast.error(error.message || 'Failed to delete account');
                    setLoading(false);
                    setDeleteAccountOpen(false);
                  } else {
                    toast.success('Account deleted successfully. You will be redirected to login.');
                    // Small delay to show success message
                    setTimeout(() => {
                      navigate('/auth', { replace: true });
                      // Force page reload to clear all state
                      window.location.href = '/auth';
                    }, 1500);
                  }
                }}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  'Delete Account'
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </DashboardLayout>
  );
}
