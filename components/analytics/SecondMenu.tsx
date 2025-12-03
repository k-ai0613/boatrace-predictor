'use client'

import { useState } from 'react'

interface SecondMenuItem {
  id: string
  label: string
  children?: SecondMenuItem[]
}

interface SecondMenuProps {
  selectedItem: string
  onItemSelect: (itemId: string) => void
}

export default function SecondMenu({ selectedItem, onItemSelect }: SecondMenuProps) {
  const [expandedItems, setExpandedItems] = useState<string[]>(['core-overview'])

  const toggleItem = (itemId: string) => {
    setExpandedItems(prev =>
      prev.includes(itemId) ? prev.filter(id => id !== itemId) : [...prev, itemId]
    )
  }

  const menuItems: SecondMenuItem[] = [
    {
      id: 'core-overview',
      label: 'コア指標概要',
      children: [
        { id: 'race-results', label: 'レース結果' },
        { id: 'comprehensive-analysis', label: '総合データ分析' },
        { id: 'player-performance', label: '選手成績' },
        { id: 'course-performance', label: 'コース成績' },
      ]
    },
    {
      id: 'process-monitoring',
      label: 'レース経過監視'
    },
    {
      id: 'detail-query',
      label: '詳細データ照会'
    }
  ]

  const renderMenuItem = (item: SecondMenuItem, isChild: boolean = false) => {
    const hasChildren = item.children && item.children.length > 0
    const isExpanded = expandedItems.includes(item.id)
    const isSelected = selectedItem === item.id

    if (isChild) {
      return (
        <div
          key={item.id}
          className={`h-12 overflow-hidden flex items-center pl-10 cursor-pointer transition-colors ${
            isSelected ? 'bg-[rgba(60,113,221,0.1)]' : 'bg-[#fafbfc] hover:bg-gray-100'
          }`}
          onClick={() => onItemSelect(item.id)}
        >
          <span className={`text-xs ${isSelected ? 'font-medium text-[#3c71dd] leading-[18px]' : 'text-[#595959]'}`}>
            {item.label}
          </span>
        </div>
      )
    }

    return (
      <div key={item.id}>
        <div
          className="h-12 overflow-hidden flex items-center px-6 cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={() => {
            if (hasChildren) {
              toggleItem(item.id)
            } else {
              onItemSelect(item.id)
            }
          }}
        >
          <span className="text-xs text-neutral-800 flex-1">{item.label}</span>
          {hasChildren && (
            <div className={`w-3 h-3 transition-transform ${isExpanded ? '' : 'rotate-180'}`}>
              <svg viewBox="0 0 12 12" fill="none" className="w-full h-full">
                <path d="M3 4.5L6 7.5L9 4.5" stroke="#595959" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
          )}
        </div>
        {hasChildren && isExpanded && item.children?.map(child => renderMenuItem(child, true))}
      </div>
    )
  }

  return (
    <div className="bg-white w-[200px] flex flex-col border-r border-gray-200 h-full overflow-y-auto">
      {menuItems.map(item => renderMenuItem(item))}
    </div>
  )
}
