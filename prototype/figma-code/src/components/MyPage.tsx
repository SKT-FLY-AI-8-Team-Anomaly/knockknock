import React, { useState } from 'react';
import { User, Heart, Settings, LogOut, ChevronRight, Edit } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { PreferencesPage } from './PreferencesPage';

interface MyPageProps {
  accessToken: string;
  userId: string;
  onLogout: () => void;
  preferences: any;
  onPreferencesUpdate: () => void;
}

export function MyPage({ accessToken, userId, onLogout, preferences, onPreferencesUpdate }: MyPageProps) {
  const [isEditingPreferences, setIsEditingPreferences] = useState(false);

  const handlePreferencesComplete = () => {
    setIsEditingPreferences(false);
    onPreferencesUpdate();
  };

  if (isEditingPreferences) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-md mx-auto px-4 py-4 flex items-center">
            <button
              onClick={() => setIsEditingPreferences(false)}
              className="text-blue-600 font-medium"
            >
              취소
            </button>
            <h1 className="flex-1 text-center text-lg font-bold">선호도 수정</h1>
            <div className="w-12"></div>
          </div>
        </div>
        <PreferencesPage
          onComplete={handlePreferencesComplete}
          accessToken={accessToken}
          userId={userId}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <div className="max-w-md mx-auto px-4 py-6 space-y-4">
        {/* 프로필 섹션 */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                <User className="w-8 h-8 text-blue-600" />
              </div>
              <div className="flex-1">
                <h2 className="text-lg font-bold text-gray-900">사용자</h2>
                <p className="text-sm text-gray-600">ID: {userId.substring(0, 8)}...</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 선호도 설정 */}
        <Card>
          <CardHeader>
            <CardTitle>나의 선호도</CardTitle>
            <CardDescription>매물 찾기에 활용됩니다</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {preferences ? (
              <>
                <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">계약 종류</span>
                    <span className="text-sm text-gray-900">
                      {preferences.contractTypes?.join(', ') || preferences.contractType || '-'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">선호 지역</span>
                    <span className="text-sm text-gray-900">{preferences.location || '-'}</span>
                  </div>
                  {preferences.houseTypes && preferences.houseTypes.length > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">집 형태</span>
                      <span className="text-sm text-gray-900">{preferences.houseTypes.join(', ')}</span>
                    </div>
                  )}
                  {preferences.elevator && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">엘리베이터</span>
                      <span className="text-sm text-gray-900">{preferences.elevator}</span>
                    </div>
                  )}
                  {preferences.infrastructure && preferences.infrastructure.length > 0 && (
                    <div className="flex items-start justify-between">
                      <span className="text-sm font-medium text-gray-700">주변 인프라</span>
                      <span className="text-sm text-gray-900 text-right">
                        {preferences.infrastructure.join(', ')}
                      </span>
                    </div>
                  )}
                </div>
                <Button
                  onClick={() => setIsEditingPreferences(true)}
                  variant="outline"
                  className="w-full"
                >
                  <Edit className="w-4 h-4 mr-2" />
                  선호도 수정
                </Button>
              </>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-gray-500 mb-3">아직 설정된 선호도가 없습니다</p>
                <Button
                  onClick={() => setIsEditingPreferences(true)}
                  className="w-full"
                >
                  선호도 설정하기
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 저장된 매물 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Heart className="w-5 h-5" />
              저장한 매물
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <Heart className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">저장한 매물이 없습니다</p>
            </div>
          </CardContent>
        </Card>

        {/* 설정 메뉴 */}
        <Card>
          <CardHeader>
            <CardTitle>설정</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <button className="w-full flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors">
              <div className="flex items-center gap-3">
                <Settings className="w-5 h-5 text-gray-600" />
                <span className="text-sm font-medium">계정 설정</span>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-400" />
            </button>
            <button
              onClick={onLogout}
              className="w-full flex items-center justify-between p-3 hover:bg-red-50 rounded-lg transition-colors"
            >
              <div className="flex items-center gap-3">
                <LogOut className="w-5 h-5 text-red-600" />
                <span className="text-sm font-medium text-red-600">로그아웃</span>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-400" />
            </button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
