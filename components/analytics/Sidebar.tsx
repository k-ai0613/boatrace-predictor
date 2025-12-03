'use client'

import { useState } from 'react'

interface MenuItem {
  id: string
  label: string
  icon?: boolean
  children?: MenuItem[]
  expanded?: boolean
}

interface SidebarProps {
  selectedMenu: string
  onMenuSelect: (menuId: string) => void
}

export default function Sidebar({ selectedMenu, onMenuSelect }: SidebarProps) {
  const [expandedMenus, setExpandedMenus] = useState<string[]>(['race-analysis', 'may-special', 'regular-stats'])

  const toggleMenu = (menuId: string) => {
    setExpandedMenus(prev =>
      prev.includes(menuId) ? prev.filter(id => id !== menuId) : [...prev, menuId]
    )
  }

  const menuItems: MenuItem[] = [
    {
      id: 'race-analysis',
      label: 'レース分析メニュー',
      icon: true,
      expanded: true,
      children: [
        { id: 'player-data', label: '選手データ分析' },
        { id: 'boat-results', label: '艇別成績' },
        { id: 'course-analysis', label: 'コース別分析' },
        { id: 'odds-info', label: 'オッズ情報' },
        { id: 'venue-data', label: '開催場データ' },
      ]
    },
    {
      id: 'may-special',
      label: '今節特集',
      icon: true,
      expanded: false
    },
    {
      id: 'data-history',
      label: 'データ履歴',
      icon: true
    },
    {
      id: 'regular-stats',
      label: '通常統計',
      icon: true,
      expanded: false
    },
    {
      id: 'data-statistics',
      label: 'データ統計',
      icon: true
    },
    {
      id: 'data-analysis',
      label: 'データ分析',
      icon: true
    },
    {
      id: 'data-management',
      label: 'データ管理',
      icon: true
    }
  ]

  const renderMenuItem = (item: MenuItem, isChild: boolean = false) => {
    const hasChildren = item.children && item.children.length > 0
    const isExpanded = expandedMenus.includes(item.id)
    const isSelected = selectedMenu === item.id

    if (isChild) {
      return (
        <div
          key={item.id}
          className={`h-12 overflow-hidden flex items-center pl-16 cursor-pointer ${
            isSelected ? 'bg-[#3c71dd]' : 'bg-[#1d2129]'
          }`}
          onClick={() => onMenuSelect(item.id)}
        >
          <span className={`text-xs text-white ${isSelected ? 'font-medium' : 'opacity-60'}`}>
            {item.label}
          </span>
        </div>
      )
    }

    return (
      <div key={item.id}>
        <div
          className="h-12 overflow-hidden flex items-center px-6 cursor-pointer hover:bg-white/5 transition-colors"
          onClick={() => {
            if (hasChildren) {
              toggleMenu(item.id)
            } else {
              onMenuSelect(item.id)
            }
          }}
        >
          {item.icon && <div className="w-5 h-5 bg-white/20 rounded mr-2"></div>}
          <span className={`text-xs text-white opacity-90 flex-1 ${hasChildren ? 'font-medium' : ''}`}>
            {item.label}
          </span>
          {hasChildren && (
            <div className={`w-3 h-3 transition-transform ${isExpanded ? '' : 'rotate-180'}`}>
              <svg viewBox="0 0 12 12" fill="none" className="w-full h-full">
                <path d="M3 4.5L6 7.5L9 4.5" stroke="rgba(255,255,255,0.6)" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
          )}
        </div>
        {hasChildren && isExpanded && item.children?.map(child => renderMenuItem(child, true))}
      </div>
    )
  }

  return (
    <div className="bg-[#2b313d] w-[220px] shadow-[2px_0px_5px_0px_rgba(0,0,0,0.16)] flex flex-col h-full">
      {/* ユーザー情報 */}
      <div className="h-12 overflow-hidden px-4 flex items-center border-b border-white/5">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 mr-2 flex items-center justify-center text-white text-xs font-bold">
          YZ
        </div>
        <p className="font-sans text-xs text-white opacity-90 flex-1">yuewen.zhang</p>
        <div className="w-3 h-3 cursor-pointer">
          <svg viewBox="0 0 12 12" fill="none" className="w-full h-full">
            <path d="M3 4.5L6 7.5L9 4.5" stroke="rgba(255,255,255,0.6)" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>
      </div>

      {/* メインメニュー */}
      <div className="flex-1 overflow-y-auto">
        {menuItems.map(item => renderMenuItem(item))}
      </div>

      {/* 底部ボタン */}
      <div className="h-12 flex items-center justify-center border-t border-[rgba(234,234,236,0.1)] cursor-pointer hover:bg-white/5 transition-colors">
        <div className="w-5 h-5 bg-white/20 rounded flex items-center justify-center">
          <svg viewBox="0 0 20 20" fill="none" className="w-3 h-3">
            <path d="M3 6h14M3 10h14M3 14h14" stroke="rgba(255,255,255,0.7)" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
      </div>
    </div>
  )
}
