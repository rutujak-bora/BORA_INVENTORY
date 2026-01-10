import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Building2, Lock, User, ArrowLeft } from 'lucide-react';
import { useToast } from '../hooks/use-toast';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchParams] = useSearchParams();
  const section = searchParams.get('section') || 'all_companies';
  const { login } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const sectionInfo = {
    all_companies: {
      title: 'All Companies Documentary',
      color: 'from-cyan-500 to-blue-600',
      hoverColor: 'hover:from-cyan-600 hover:to-blue-700',
    },
    dns: {
      title: 'DNS Documentary',
      color: 'from-emerald-500 to-teal-600',
      hoverColor: 'hover:from-emerald-600 hover:to-teal-700',
    },
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await login(username, password);
      
      console.log('Logged in user:', user);
      console.log('Selected section:', section);
      console.log('User section:', user.section);
      
      // Check if user belongs to the selected section
      if (user.section !== section) {
        toast({
          title: 'Access Denied',
          description: `This account belongs to ${user.section === 'dns' ? 'DNS Documentary' : 'All Companies Documentary'}. Please select the correct section.`,
          variant: 'destructive',
        });
        // Logout the user since they accessed wrong section
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setLoading(false);
        return;
      }
      
      toast({
        title: 'Success',
        description: 'Logged in successfully',
      });
      navigate('/dashboard');
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Login failed',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Back Button */}
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-slate-300 hover:text-white mb-6 transition-colors"
          data-testid="back-to-landing"
        >
          <ArrowLeft size={20} />
          Back to sections
        </button>

        {/* Logo & Title */}
        <div className="text-center mb-8">
          <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br ${sectionInfo[section].color} mb-4 shadow-lg`}>
            <Building2 size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">{sectionInfo[section].title}</h1>
          <p className="text-slate-400">Bora Mobility LLP</p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">Sign In</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="username" className="text-slate-700">
                Username
              </Label>
              <div className="relative mt-1">
                <User
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  size={18}
                />
                <Input
                  id="username"
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10"
                  required
                  data-testid="username-input"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="password" className="text-slate-700">
                Password
              </Label>
              <div className="relative mt-1">
                <Lock
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  size={18}
                />
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10"
                  required
                  data-testid="password-input"
                />
              </div>
            </div>

            <Button
              type="submit"
              className={`w-full bg-gradient-to-r ${sectionInfo[section].color} ${sectionInfo[section].hoverColor} text-white font-medium py-3 shadow-lg`}
              disabled={loading}
              data-testid="login-submit-btn"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-slate-600 text-sm">
              Use your predefined credentials to access the system
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
