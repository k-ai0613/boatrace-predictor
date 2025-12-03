'use client'

interface Tab {
  id: string
  label: string
}

interface HeaderTabsProps {
  title: string
  tabs: Tab[]
  activeTab: string
  onTabChange: (tabId: string) => void
}

export default function HeaderTabs({ title, tabs, activeTab, onTabChange }: HeaderTabsProps) {
  return (
    <div className="h-12 bg-white shadow-[0px_2px_8px_0px_rgba(0,0,0,0.16)] flex items-center px-6">
      <div className="flex items-center gap-2">
        <div className="w-4 h-4 bg-gradient-to-br from-blue-400 to-blue-600 rounded"></div>
        <h1 className="text-sm text-neutral-800 font-medium">{title}</h1>
      </div>
      <div className="flex gap-10 ml-16">
        {tabs.map(tab => (
          <div
            key={tab.id}
            className={`text-xs cursor-pointer pb-1 transition-all ${
              activeTab === tab.id
                ? 'text-[#3c71dd] font-medium border-b-2 border-[#3c71dd]'
                : 'text-neutral-800 hover:text-[#3c71dd]'
            }`}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </div>
        ))}
      </div>
      <div className="ml-auto cursor-pointer hover:bg-gray-100 p-1 rounded transition-colors">
        <svg viewBox="0 0 16 16" fill="none" className="w-4 h-4">
          <path
            d="M8 2L9.5 6.5L14 8L9.5 9.5L8 14L6.5 9.5L2 8L6.5 6.5L8 2Z"
            stroke="#666"
            strokeWidth="1.5"
            fill="none"
          />
        </svg>
      </div>
    </div>
  )
}
