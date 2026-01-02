import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { Building2, ArrowRight, BarChart3, Shield, Zap } from 'lucide-react';

export default function Index() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary text-primary-foreground">
              <Building2 className="w-5 h-5" />
            </div>
            <span className="text-lg font-bold">BankFusion</span>
          </div>
          <Link to={user ? '/dashboard' : '/auth'}>
            <Button>
              {user ? 'Go to Dashboard' : 'Get Started'}
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-32 pb-20 px-4">
        <div className="container mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6 animate-fade-in">
            <Zap className="w-4 h-4" />
            AI-Powered Bank Statement Analysis
          </div>
          <h1 className="text-4xl md:text-6xl font-bold text-foreground mb-6 leading-tight animate-fade-in">
            Transform your{' '}
            <span className="gradient-text">bank statements</span> into
            actionable insights
          </h1>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto animate-fade-in">
            Upload your bank statement PDFs and get instant categorization, spending analysis, 
            and beautiful visualizations. Support for all major Indian banks.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center animate-fade-in">
            <Link to={user ? '/dashboard' : '/auth'}>
              <Button size="lg" className="w-full sm:w-auto hover-scale">
                {user ? 'Go to Dashboard' : 'Start Analyzing'}
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4 bg-secondary/30">
        <div className="container mx-auto max-w-6xl">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground mb-4">
              Everything you need to understand your finances
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Our platform provides comprehensive analysis tools designed specifically 
              for Indian banking formats.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="rounded-2xl bg-card border p-8 hover:shadow-lg transition-all duration-300 hover-scale">
              <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 text-primary mb-4">
                <BarChart3 className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-3">
                Visual Analytics
              </h3>
              <p className="text-muted-foreground">
                Beautiful charts showing category-wise spending, monthly trends, 
                and credit vs debit analysis.
              </p>
            </div>
            <div className="rounded-2xl bg-card border p-8 hover:shadow-lg transition-all duration-300 hover-scale">
              <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-success/10 text-success mb-4">
                <Shield className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-3">
                Bank-Grade Security
              </h3>
              <p className="text-muted-foreground">
                Your data is encrypted and stored securely. We never share 
                your financial information with anyone.
              </p>
            </div>
            <div className="rounded-2xl bg-card border p-8 hover:shadow-lg transition-all duration-300 hover-scale">
              <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-warning/10 text-warning mb-4">
                <Zap className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-3">
                Instant Processing
              </h3>
              <p className="text-muted-foreground">
                Upload your PDF and get results in seconds. AI-powered 
                categorization for accurate insights.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4">
        <div className="container mx-auto max-w-4xl">
          <div className="rounded-3xl bg-gradient-to-br from-primary to-info p-12 text-center">
            <h2 className="text-3xl font-bold text-primary-foreground mb-4">
              Ready to take control of your finances?
            </h2>
            <p className="text-primary-foreground/80 mb-8 max-w-xl mx-auto">
              Join thousands of users who are already making smarter financial 
              decisions with BankFusion.
            </p>
            <Link to={user ? '/dashboard' : '/auth'}>
              <Button size="lg" variant="secondary" className="hover-scale">
                {user ? 'Go to Dashboard' : 'Get Started for Free'}
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t border-border">
        <div className="container mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground">
              <Building2 className="w-4 h-4" />
            </div>
            <span className="font-semibold">BankFusion</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © 2024 BankFusion. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
