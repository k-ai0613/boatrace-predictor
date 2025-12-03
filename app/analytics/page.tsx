'use client'

import { useState } from 'react'
import Sidebar from '@/components/analytics/Sidebar'
import SecondMenu from '@/components/analytics/SecondMenu'
import HeaderTabs from '@/components/analytics/HeaderTabs'
import PermissionForm from '@/components/analytics/PermissionForm'
import BoatStatistics from '@/components/analytics/BoatStatistics'
import TopRacers from '@/components/analytics/TopRacers'
import CourseAnalysis from '@/components/analytics/CourseAnalysis'
import RaceSelector from '@/components/analytics/RaceSelector'
import RacePrediction from '@/components/analytics/RacePrediction'
import RecommendedBetsDisplay from '@/components/analytics/RecommendedBetsDisplay'

export default function AnalyticsPage() {
  const [selectedMenu, setSelectedMenu] = useState('player-data')
  const [selectedSecondItem, setSelectedSecondItem] = useState('comprehensive-analysis')
  const [activeTab, setActiveTab] = useState('race-prediction')
  const [selectedRace, setSelectedRace] = useState<{
    venueId: number
    date: string
    raceNumber: number
  } | null>(null)

  const tabs = [
    { id: 'race-prediction', label: 'レース予測' },
    { id: 'boat-data', label: '艇別データ' },
    { id: 'player-ranking', label: '選手ランキング' },
    { id: 'course-analysis', label: 'コース分析' }
  ]

  const handleFormSubmit = async (data: { period: string; reason: string }) => {
    console.log('フォーム送信データ:', data)
    // ここで API 呼び出しなどを実装できます
  }

  const handleRaceSelect = (venueId: number, date: string, raceNumber: number) => {
    setSelectedRace({ venueId, date, raceNumber })
  }

  // タブに応じたコンテンツをレンダリング
  const renderContent = () => {
    switch (activeTab) {
      case 'race-prediction':
        return (
          <div className="p-6 space-y-6">
            <RaceSelector onRaceSelect={handleRaceSelect} />
            {selectedRace && (
              <>
                <RacePrediction
                  venueId={selectedRace.venueId}
                  date={selectedRace.date}
                  raceNumber={selectedRace.raceNumber}
                />
                {/* <RecommendedBetsDisplay raceId={selectedRace.raceId} /> */}
              </>
            )}
          </div>
        )
      case 'boat-data':
        return <BoatStatistics />
      case 'player-ranking':
        return <TopRacers />
      case 'course-analysis':
        return <CourseAnalysis />
      default:
        return (
          <div className="flex items-center justify-center p-6 min-h-full">
            <PermissionForm onSubmit={handleFormSubmit} />
          </div>
        )
    }
  }

  return (
    <div className="bg-white relative w-full h-screen flex overflow-hidden">
      {/* 左サイドバー */}
      <Sidebar selectedMenu={selectedMenu} onMenuSelect={setSelectedMenu} />

      {/* 縦区切り線 */}
      <div className="w-px h-full bg-[#e4e5e6]"></div>

      {/* 第二メニュー */}
      <SecondMenu selectedItem={selectedSecondItem} onItemSelect={setSelectedSecondItem} />

      {/* メインコンテンツエリア */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* トップヘッダー */}
        <HeaderTabs
          title="選手データ分析"
          tabs={tabs}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />

        {/* コンテンツエリア */}
        <div className="flex-1 overflow-y-auto bg-gray-50">
          {renderContent()}
        </div>
      </div>
    </div>
  )
}
