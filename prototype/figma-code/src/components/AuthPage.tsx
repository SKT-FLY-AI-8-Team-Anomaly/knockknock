import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Home } from 'lucide-react';

interface AuthPageProps {
  onAuthSuccess: (accessToken: string, userId: string) => void;
}

export function AuthPage({ onAuthSuccess }: AuthPageProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        // Login
        const { createClient } = await import('@supabase/supabase-js');
        const { projectId, publicAnonKey } = await import('../utils/supabase/info');
        
        const supabase = createClient(
          `https://${projectId}.supabase.co`,
          publicAnonKey
        );

        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) {
          setError(error.message);
        } else if (data.session) {
          console.log('Login successful, access_token:', data.session.access_token.substring(0, 50) + '...');
          console.log('User ID:', data.user.id);
          onAuthSuccess(data.session.access_token, data.user.id);
        }
      } else {
        // Sign up
        const { projectId, publicAnonKey } = await import('../utils/supabase/info');
        
        const response = await fetch(
          `https://${projectId}.supabase.co/functions/v1/make-server-a03ea467/signup`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${publicAnonKey}`,
            },
            body: JSON.stringify({ email, password, name }),
          }
        );

        const result = await response.json();

        if (!response.ok) {
          setError(result.error || '회원가입에 실패했습니다');
        } else {
          // Auto login after signup
          const { createClient } = await import('@supabase/supabase-js');
          const supabase = createClient(
            `https://${projectId}.supabase.co`,
            publicAnonKey
          );

          const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password,
          });

          if (error) {
            setError(error.message);
          } else if (data.session) {
            console.log('Signup + Login successful, access_token:', data.session.access_token.substring(0, 50) + '...');
            console.log('User ID:', data.user.id);
            onAuthSuccess(data.session.access_token, data.user.id);
          }
        }
      }
    } catch (err) {
      console.error('Auth error:', err);
      setError('인증 중 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4">
            <Home className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">부동산 매니저</h1>
          <p className="text-gray-600 mt-2">내 집 마련의 든든한 파트너</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{isLogin ? '로그인' : '회원가입'}</CardTitle>
            <CardDescription>
              {isLogin
                ? '계정에 로그인하여 시작하세요'
                : '새 계정을 만들어 시작하세요'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <div className="space-y-2">
                  <Label htmlFor="name">이름</Label>
                  <Input
                    id="name"
                    type="text"
                    placeholder="홍길동"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required={!isLogin}
                  />
                </div>
              )}
              
              <div className="space-y-2">
                <Label htmlFor="email">이메일</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="example@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">비밀번호</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? '처리중...' : isLogin ? '로그인' : '회원가입'}
              </Button>
            </form>

            <div className="mt-4 text-center">
              <button
                type="button"
                onClick={() => {
                  setIsLogin(!isLogin);
                  setError('');
                }}
                className="text-sm text-blue-600 hover:underline"
              >
                {isLogin
                  ? '계정이 없으신가요? 회원가입'
                  : '이미 계정이 있으신가요? 로그인'}
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}