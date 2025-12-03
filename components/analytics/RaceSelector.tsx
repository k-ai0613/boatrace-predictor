'use client'

import { useState, useEffect } from 'react'
import { VENUES } from '@/types'

interface RaceSelectorProps {
  onRaceSelect: (venueId: number, date: string, raceNumber: number) => void
}

export default function RaceSelector({ onRaceSelect }: RaceSelectorProps) {
  const [selectedVenue, setSelectedVenue] = useState<number>(1)
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [selectedRace, setSelectedRace] = useState<number>(1)

  useEffect(() => {
    // デフォルトで今日の日付を設定
    const today = new Date()
    const dateStr = today.toISOString().split('T')[0]
    setSelectedDate(dateStr)
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedVenue && selectedDate && selectedRace) {
      onRaceSelect(selectedVenue, selectedDate, selectedRace)
    }
  }

  // 次の7日間の日付を生成
  const generateDates = () => {
    const dates = []
    const today = new Date()
    for (let i = 0; i < 7; i++) {
      const date = new Date(today)
      date.setDate(today.getDate() + i)
      dates.push({
        value: date.toISOString().split('T')[0],
        label: `${date.getMonth() + 1}/${date.getDate()} (${['日', '月', '火', '水', '木', '金', '土'][date.getDay()]})`
      })
    }
    return dates
  }

  const dates = generateDates()
  const venueList = Object.values(VENUES)

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-lg font-bold text-neutral-800 mb-6">レース選択</h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 開催場選択 */}
        <div>
          <label htmlFor="venue" className="block text-sm font-medium text-gray-700 mb-2">
            開催場
          </label>
          <select
            id="venue"
            value={selectedVenue}
            onChange={(e) => setSelectedVenue(Number(e.target.value))}
            className="w-full h-10 border border-gray-300 rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#3c71dd] focus:border-transparent"
          >
            {venueList.map(venue => (
              <option key={venue.id} value={venue.id}>
                {venue.name} ({venue.prefecture})
              </option>
            ))}
          </select>
        </div>

        {/* 日付選択 */}
        <div>
          <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-2">
            開催日
          </label>
          <select
            id="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="w-full h-10 border border-gray-300 rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#3c71dd] focus:border-transparent"
          >
            {dates.map(date => (
              <option key={date.value} value={date.value}>
                {date.label}
              </option>
            ))}
          </select>
        </div>

        {/* レース番号選択 */}
        <div>
          <label htmlFor="race" className="block text-sm font-medium text-gray-700 mb-2">
            レース番号
          </label>
          <div className="grid grid-cols-6 gap-2">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(num => (
              <button
                key={num}
                type="button"
                onClick={() => setSelectedRace(num)}
                className={`h-10 rounded-lg font-medium text-sm transition-all ${
                  selectedRace === num
                    ? 'bg-[#3c71dd] text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {num}R
              </button>
            ))}
          </div>
        </div>

        {/* 送信ボタン */}
        <button
          type="submit"
          className="w-full h-12 bg-gradient-to-r from-[#3c71dd] to-[#2d5dbd] text-white rounded-lg font-bold text-sm hover:from-[#2d5dbd] hover:to-[#1e4a9d] transition-all shadow-lg"
        >
          予測を表示
        </button>
      </form>

      {/* 選択中の情報表示 */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-sm text-blue-900">
          <span className="font-bold">選択中：</span>
          {VENUES[selectedVenue]?.name} / {selectedDate} / {selectedRace}R
        </p>
      </div>
    </div>
  )
}
