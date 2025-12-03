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
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  const tabs = [
    { id: 'race-prediction', label: 'レース予測' },
    { id: 'boat-data', label: '艇別データ' },
    { id: 'player-ranking', label: '選手ランキング' },
    { id: 'course-analysis', label: 'コース分析' }
  ]

  const handleFormSubmit = async (data: { period: string; reason: string }) => {
    console.log('フォーム送信データ:', data)
  }

  const handleRaceSelect = (venueId: number, date: string, raceNumber: number) => {
    setSelectedRace({ venueId, date, raceNumber })
  }

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId)
    setIsMobileMenuOpen(false)
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'race-prediction':
        return (
          <div className="p-4 md:p-6 space-y-4 md:space-y-6">
            <RaceSelector onRaceSelect={handleRaceSelect} />
            {selectedRace && (
              <>
                <RacePrediction
                  venueId={selectedRace.venueId}
                  date={selectedRace.date}
                  raceNumber={selectedRace.raceNumber}
                />
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
    <div className="bg-white relative w-full min-h-[calc(100vh-120px)] md:h-screen flex flex-col md:flex-row overflow-hidden -mx-4 -my-4 md:-my-6">
      {/* モバイル用タブナビゲーション */}
      <div className="md:hidden bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="flex overflow-x-auto scrollbar-hide">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`flex-shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition-colors min-h-[44px] ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600 bg-blue-50'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* デスクトップ: 左サイドバー */}
      <div className="hidden md:block">
        <Sidebar selectedMenu={selectedMenu} onMenuSelect={setSelectedMenu} />
      </div>

      {/* デスクトップ: 縦区切り線 */}
      <div className="hidden md:block w-px h-full bg-[#e4e5e6]"></div>

      {/* デスクトップ: 第二メニュー */}
      <div className="hidden md:block">
        <SecondMenu selectedItem={selectedSecondItem} onItemSelect={setSelectedSecondItem} />
      </div>

      {/* メインコンテンツエリア */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* デスクトップ: トップヘッダー */}
        <div className="hidden md:block">
          <HeaderTabs
            title="選手データ分析"
            tabs={tabs}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />
        </div>

        {/* コンテンツエリア */}
        <div className="flex-1 overflow-y-auto bg-gray-50">
          {renderContent()}
        </div>
      </div>
    </div>
  )
}
