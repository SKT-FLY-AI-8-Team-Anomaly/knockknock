import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';
import { Checkbox } from './ui/checkbox';
import { ChevronRight } from 'lucide-react';

interface PreferencesPageProps {
  onComplete: () => void;
  accessToken: string;
  userId: string;
}

export function PreferencesPage({ onComplete, accessToken, userId }: PreferencesPageProps) {
  // 계약 종류 (다중 선택)
  const [contractTypes, setContractTypes] = useState<string[]>([]);
  
  // 각 계약 종류별 금액 범위
  const [jeonseMin, setJeonseMin] = useState('');
  const [jeonseMax, setJeonseMax] = useState('');
  const [monthlyDeposit, setMonthlyDeposit] = useState('');
  const [monthlyRentMin, setMonthlyRentMin] = useState('');
  const [monthlyRentMax, setMonthlyRentMax] = useState('');
  const [saleMin, setSaleMin] = useState('');
  const [saleMax, setSaleMax] = useState('');
  
  // 기본 정보
  const [location, setLocation] = useState('');
  
  // 집 형태 (다중 선택)
  const [houseTypes, setHouseTypes] = useState<string[]>([]);
  
  // 엘리베이터
  const [elevator, setElevator] = useState<string>('상관없음');
  
  // 주변 인프라 (다중 선택)
  const [infrastructure, setInfrastructure] = useState<string[]>([]);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const toggleContractType = (type: string) => {
    setContractTypes(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const toggleHouseType = (type: string) => {
    setHouseTypes(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const toggleInfrastructure = (item: string) => {
    setInfrastructure(prev => 
      prev.includes(item) 
        ? prev.filter(i => i !== item)
        : [...prev, item]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    // 유효성 검사
    if (contractTypes.length === 0) {
      setError('최소 하나의 계약 종류를 선택해주세요');
      return;
    }
    
    setLoading(true);

    try {
      const { projectId, publicAnonKey } = await import('../utils/supabase/info');
      
      const preferences = {
        userId,
        contractTypes,
        location,
        priceRanges: {
          jeonse: contractTypes.includes('전세') ? {
            min: jeonseMin ? parseInt(jeonseMin) : null,
            max: jeonseMax ? parseInt(jeonseMax) : null,
          } : null,
          monthly: contractTypes.includes('월세') ? {
            deposit: monthlyDeposit ? parseInt(monthlyDeposit) : null,
            rentMin: monthlyRentMin ? parseInt(monthlyRentMin) : null,
            rentMax: monthlyRentMax ? parseInt(monthlyRentMax) : null,
          } : null,
          sale: contractTypes.includes('매매') ? {
            min: saleMin ? parseInt(saleMin) : null,
            max: saleMax ? parseInt(saleMax) : null,
          } : null,
        },
        houseTypes,
        elevator,
        infrastructure,
      };
      
      console.log('Saving preferences:', preferences);
      
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-a03ea467/preferences`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${publicAnonKey}`,
          },
          body: JSON.stringify(preferences),
        }
      );

      const result = await response.json();
      console.log('Preferences save response:', result);

      if (!response.ok) {
        console.error('Failed to save preferences:', result);
        setError(result.error || '선호도 저장에 실패했습니다');
      } else {
        console.log('Preferences saved successfully');
        onComplete();
      }
    } catch (err) {
      console.error('Error saving preferences:', err);
      setError('선호도 저장 중 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white p-4 pb-20">
      <div className="max-w-md mx-auto pt-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">선호도 설정</h1>
          <p className="text-gray-600 mt-1">원하시는 조건을 알려주세요</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 계약 종류 */}
          <Card>
            <CardHeader>
              <CardTitle>계약 종류</CardTitle>
              <CardDescription>중복 선택 가능합니다</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {['전세', '월세', '매매'].map((type) => (
                <div
                  key={type}
                  className={`flex items-center space-x-3 border rounded-lg p-3 transition-colors ${
                    contractTypes.includes(type) ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'
                  }`}
                >
                  <Checkbox
                    checked={contractTypes.includes(type)}
                    onCheckedChange={() => toggleContractType(type)}
                  />
                  <Label 
                    className="flex-1 cursor-pointer"
                    onClick={() => toggleContractType(type)}
                  >
                    {type}
                  </Label>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* 전세 금액 범위 */}
          {contractTypes.includes('전세') && (
            <Card>
              <CardHeader>
                <CardTitle>전세 예산 범위</CardTitle>
                <CardDescription>단위: 만원</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    type="number"
                    placeholder="최소 금액"
                    value={jeonseMin}
                    onChange={(e) => setJeonseMin(e.target.value)}
                  />
                  <Input
                    type="number"
                    placeholder="최대 금액"
                    value={jeonseMax}
                    onChange={(e) => setJeonseMax(e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {/* 월세 금액 범위 */}
          {contractTypes.includes('월세') && (
            <Card>
              <CardHeader>
                <CardTitle>월세 예산 범위</CardTitle>
                <CardDescription>단위: 만원</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <Label className="text-sm text-gray-600 mb-2 block">보증금</Label>
                  <Input
                    type="number"
                    placeholder="보증금"
                    value={monthlyDeposit}
                    onChange={(e) => setMonthlyDeposit(e.target.value)}
                  />
                </div>
                <div>
                  <Label className="text-sm text-gray-600 mb-2 block">월세</Label>
                  <div className="grid grid-cols-2 gap-3">
                    <Input
                      type="number"
                      placeholder="최소"
                      value={monthlyRentMin}
                      onChange={(e) => setMonthlyRentMin(e.target.value)}
                    />
                    <Input
                      type="number"
                      placeholder="최대"
                      value={monthlyRentMax}
                      onChange={(e) => setMonthlyRentMax(e.target.value)}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 매매 금액 범위 */}
          {contractTypes.includes('매매') && (
            <Card>
              <CardHeader>
                <CardTitle>매매 예산 범위</CardTitle>
                <CardDescription>단위: 만원</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    type="number"
                    placeholder="최소 금액"
                    value={saleMin}
                    onChange={(e) => setSaleMin(e.target.value)}
                  />
                  <Input
                    type="number"
                    placeholder="최대 금액"
                    value={saleMax}
                    onChange={(e) => setSaleMax(e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {/* 선호 지역 */}
          <Card>
            <CardHeader>
              <CardTitle>선호 지역</CardTitle>
            </CardHeader>
            <CardContent>
              <Input
                type="text"
                placeholder="예: 서울시 강남구"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                required
              />
            </CardContent>
          </Card>

          {/* 집 형태 */}
          <Card>
            <CardHeader>
              <CardTitle>집 형태</CardTitle>
              <CardDescription>중복 선택 가능합니다</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {['아파트', '빌라', '오피스텔', '단독/다가구', '원룸'].map((type) => (
                <div
                  key={type}
                  className={`flex items-center space-x-3 border rounded-lg p-3 transition-colors ${
                    houseTypes.includes(type) ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'
                  }`}
                >
                  <Checkbox
                    checked={houseTypes.includes(type)}
                    onCheckedChange={() => toggleHouseType(type)}
                  />
                  <Label 
                    className="flex-1 cursor-pointer"
                    onClick={() => toggleHouseType(type)}
                  >
                    {type}
                  </Label>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* 엘리베이터 */}
          <Card>
            <CardHeader>
              <CardTitle>엘리베이터</CardTitle>
            </CardHeader>
            <CardContent>
              <RadioGroup value={elevator} onValueChange={setElevator}>
                <div className="flex items-center space-x-2 border rounded-lg p-3 hover:bg-gray-50 cursor-pointer">
                  <RadioGroupItem value="필수" id="elevator-required" />
                  <Label htmlFor="elevator-required" className="flex-1 cursor-pointer">
                    필수
                  </Label>
                </div>
                <div className="flex items-center space-x-2 border rounded-lg p-3 hover:bg-gray-50 cursor-pointer">
                  <RadioGroupItem value="선호" id="elevator-preferred" />
                  <Label htmlFor="elevator-preferred" className="flex-1 cursor-pointer">
                    선호
                  </Label>
                </div>
                <div className="flex items-center space-x-2 border rounded-lg p-3 hover:bg-gray-50 cursor-pointer">
                  <RadioGroupItem value="상관없음" id="elevator-none" />
                  <Label htmlFor="elevator-none" className="flex-1 cursor-pointer">
                    상관없음
                  </Label>
                </div>
              </RadioGroup>
            </CardContent>
          </Card>

          {/* 주변 인프라 */}
          <Card>
            <CardHeader>
              <CardTitle>주변 인프라</CardTitle>
              <CardDescription>중복 선택 가능합니다</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {['지하철역', '편의점/마트', '학교', '병원', '공원', '주차장'].map((item) => (
                <div
                  key={item}
                  className={`flex items-center space-x-3 border rounded-lg p-3 transition-colors ${
                    infrastructure.includes(item) ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'
                  }`}
                >
                  <Checkbox
                    checked={infrastructure.includes(item)}
                    onCheckedChange={() => toggleInfrastructure(item)}
                  />
                  <Label 
                    className="flex-1 cursor-pointer"
                    onClick={() => toggleInfrastructure(item)}
                  >
                    {item}
                  </Label>
                </div>
              ))}
            </CardContent>
          </Card>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <Button type="submit" className="w-full sticky bottom-4" disabled={loading}>
            {loading ? '저장 중...' : '다음'}
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </form>
      </div>
    </div>
  );
}