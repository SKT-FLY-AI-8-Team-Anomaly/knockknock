import React, { useState, useEffect } from 'react';
import { AuthPage } from './components/AuthPage';
import { PreferencesPage } from './components/PreferencesPage';
import { MainPage } from './components/MainPage';
import { createClient } from '@supabase/supabase-js';
import { projectId, publicAnonKey } from './utils/supabase/info';

type AppState = 'auth' | 'preferences' | 'main';

export default function App() {
  const [appState, setAppState] = useState<AppState>('auth');
  const [accessToken, setAccessToken] = useState<string>('');
  const [userId, setUserId] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkExistingSession();
  }, []);

  const checkExistingSession = async () => {
    try {
      const supabase = createClient(
        `https://${projectId}.supabase.co`,
        publicAnonKey
      );

      const { data: { session } } = await supabase.auth.getSession();

      if (session) {
        setAccessToken(session.access_token);
        setUserId(session.user.id);
        
        // Check if user has preferences
        const response = await fetch(
          `https://${projectId}.supabase.co/functions/v1/make-server-a03ea467/preferences?userId=${session.user.id}`,
          {
            headers: {
              'Authorization': `Bearer ${publicAnonKey}`,
            },
          }
        );

        const result = await response.json();
        
        if (response.ok && result.preferences) {
          setAppState('main');
        } else {
          setAppState('preferences');
        }
      } else {
        setAppState('auth');
      }
    } catch (err) {
      console.error('Error checking session:', err);
      setAppState('auth');
    } finally {
      setLoading(false);
    }
  };

  const handleAuthSuccess = async (token: string, uid: string) => {
    console.log('App.tsx - handleAuthSuccess called');
    console.log('Token received:', token.substring(0, 50) + '...');
    console.log('User ID:', uid);
    
    setAccessToken(token);
    setUserId(uid);
    
    // Check if user has preferences
    try {
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-a03ea467/preferences?userId=${uid}`,
        {
          headers: {
            'Authorization': `Bearer ${publicAnonKey}`,
          },
        }
      );

      const result = await response.json();
      console.log('Preferences check response:', result);
      
      if (response.ok && result.preferences) {
        setAppState('main');
      } else {
        setAppState('preferences');
      }
    } catch (err) {
      console.error('Error checking preferences:', err);
      setAppState('preferences');
    }
  };

  const handlePreferencesComplete = () => {
    setAppState('main');
  };

  const handleLogout = async () => {
    try {
      const supabase = createClient(
        `https://${projectId}.supabase.co`,
        publicAnonKey
      );

      await supabase.auth.signOut();
      setAccessToken('');
      setUserId('');
      setAppState('auth');
    } catch (err) {
      console.error('Error logging out:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {appState === 'auth' && <AuthPage onAuthSuccess={handleAuthSuccess} />}
      {appState === 'preferences' && (
        <PreferencesPage
          onComplete={handlePreferencesComplete}
          accessToken={accessToken}
          userId={userId}
        />
      )}
      {appState === 'main' && (
        <MainPage
          accessToken={accessToken}
          userId={userId}
          onLogout={handleLogout}
        />
      )}
    </div>
  );
}