import React, { useState, useEffect } from 'react';
import { MessageCircle, MapPin, FileText, FileSignature, Home, User } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { MyPage } from './MyPage';
import { ChatbotPage } from './ChatbotPage';

interface MainPageProps {
  accessToken: string;
  userId: string;
  onLogout: () => void;
}

type TabType = 'chatbot' | 'inspection' | 'documents' | 'contract' | 'my';

export function MainPage({ accessToken, userId, onLogout }: MainPageProps) {
  const [activeTab, setActiveTab] = useState<TabType>('inspection');
  const [preferences, setPreferences] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      const { projectId, publicAnonKey } = await import('../utils/supabase/info');
      
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-a03ea467/preferences?userId=${userId}`,
        {
          headers: {
            'Authorization': `Bearer ${publicAnonKey}`,
          },
        }
      );

      const result = await response.json();
      if (response.ok) {
        setPreferences(result.preferences);
      }
    } catch (err) {
      console.error('Error loading preferences:', err);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'inspection' as TabType, icon: MapPin, label: '임장' },
    { id: 'documents' as TabType, icon: FileText, label: '서류' },
    { id: 'chatbot' as TabType, icon: MessageCircle, label: '챗봇' },
    { id: 'contract' as TabType, icon: FileSignature, label: '계약' },
    { id: 'my' as TabType, icon: User, label: '마이' },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'inspection':
        return (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>매물 임장 관리</CardTitle>
                <CardDescription>
                  방문한 매물 정보를 기록하세요
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
                  <p className="text-gray-500">임장 기능이 곧 추가됩니다</p>
                </div>
              </CardContent>
            </Card>
          </div>
        );
      case 'documents':
        return (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>서류 관리</CardTitle>
                <CardDescription>
                  필요한 서류를 확인하고 관리하세요
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
                  <p className="text-gray-500">서류 기능이 곧 추가됩니다</p>
                </div>
              </CardContent>
            </Card>
          </div>
        );
      case 'chatbot':
        return <ChatbotPage userId={userId} />;
      case 'contract':
        return (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>계약 관리</CardTitle>
                <CardDescription>
                  계약 진행 상황을 관리하세요
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
                  <p className="text-gray-500">계약 기능이 곧 추가됩니다</p>
                </div>
              </CardContent>
            </Card>
          </div>
        );
      case 'my':
        return (
          <MyPage
            accessToken={accessToken}
            userId={userId}
            onLogout={onLogout}
            preferences={preferences}
            onPreferencesUpdate={loadPreferences}
          />
        );
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">로딩 중...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header - hide when My tab is active */}
      {activeTab !== 'my' && (
        <>
          <div className="bg-white border-b sticky top-0 z-10">
            <div className="max-w-md mx-auto px-4 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <Home className="w-5 h-5 text-white" />
                </div>
                <h1 className="text-lg font-bold">부동산 매니저</h1>
              </div>
            </div>
          </div>

          {/* User Preferences Summary */}
          {preferences && (
            <div className="max-w-md mx-auto px-4 py-4">
              <Card className="bg-blue-50 border-blue-200">
                <CardContent className="pt-4">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                      <MapPin className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">
                        {preferences.contractTypes?.join(', ') || preferences.contractType || '-'} | {preferences.location}
                      </p>
                      {preferences.houseTypes && preferences.houseTypes.length > 0 && (
                        <p className="text-sm text-gray-600 mt-1">
                          {preferences.houseTypes.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}

      {/* Main Content */}
      <div className={activeTab !== 'my' ? 'max-w-md mx-auto px-4' : ''}>
        {renderContent()}
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t">
        <div className="max-w-md mx-auto px-4">
          <div className="grid grid-cols-5 gap-1 py-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex flex-col items-center gap-1 py-2 px-1 rounded-lg transition-colors ${
                    isActive
                      ? 'text-blue-600 bg-blue-50'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="w-6 h-6" />
                  <span className="text-xs font-medium">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}