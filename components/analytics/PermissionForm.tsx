'use client'

import { useState } from 'react'

interface PermissionFormProps {
  onSubmit?: (data: { period: string; reason: string }) => void
}

export default function PermissionForm({ onSubmit }: PermissionFormProps) {
  const [period, setPeriod] = useState('1ヶ月')
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      if (onSubmit) {
        await onSubmit({ period, reason })
      }
      // フォームをリセット
      setReason('')
      alert('権限申請を送信しました')
    } catch (error) {
      console.error('送信エラー:', error)
      alert('送信に失敗しました')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="bg-white shadow-[0px_2px_8px_0px_rgba(0,0,0,0.16)] rounded-lg p-10 max-w-3xl w-full">
      {/* イラスト画像 */}
      <div className="flex justify-center mb-10">
        <svg viewBox="0 0 449 300" fill="none" className="w-full max-w-md">
          <rect width="449" height="300" fill="#F5F5F5" rx="8"/>
          <g transform="translate(100, 50)">
            <rect x="50" y="100" width="200" height="80" rx="8" fill="#E0E0E0"/>
            <rect x="80" y="40" width="140" height="100" rx="8" fill="#BBDEFB"/>
            <circle cx="150" cy="90" r="25" fill="#3C71DD"/>
            <path
              d="M140 87 L145 95 L160 80"
              stroke="white"
              strokeWidth="3"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </g>
        </svg>
      </div>

      {/* フォーム */}
      <form onSubmit={handleSubmit} className="max-w-lg mx-auto">
        <h2 className="text-base font-medium text-neutral-800 text-center mb-3">
          レポート【艇別総合データ指標】権限申請
        </h2>
        <p className="text-xs text-gray-500 text-center mb-8">
          提示紹介：競艇データ分析システム2.0
        </p>

        {/* 権限有効期限 */}
        <div className="mb-6">
          <label htmlFor="permission-period" className="block text-xs text-neutral-800 mb-2 font-medium">
            権限有効期限：
          </label>
          <select
            id="permission-period"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="w-full h-9 border border-[#d9d9d9] rounded px-3 text-xs text-neutral-800 focus:outline-none focus:border-[#3c71dd] focus:ring-1 focus:ring-[#3c71dd] transition-colors"
            aria-label="権限有効期限"
          >
            <option>1ヶ月</option>
            <option>3ヶ月</option>
            <option>6ヶ月</option>
            <option>1年</option>
          </select>
        </div>

        {/* 申請理由 */}
        <div className="mb-6">
          <label htmlFor="application-reason" className="block text-xs text-neutral-800 mb-2 font-medium">
            申請理由：
          </label>
          <textarea
            id="application-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full h-24 border border-[#d9d9d9] rounded px-3 py-2 text-xs text-neutral-800 resize-none focus:outline-none focus:border-[#3c71dd] focus:ring-1 focus:ring-[#3c71dd] transition-colors"
            placeholder="説明が必要な理由、完成が必要な作業手順を記述してください..."
            aria-label="申請理由"
            required
          />
        </div>

        {/* 送信ボタン */}
        <button
          type="submit"
          disabled={isSubmitting || !reason.trim()}
          className="w-full h-10 bg-[#3c71dd] text-white rounded text-sm font-medium hover:bg-[#2d5dbd] active:bg-[#1e4a9d] transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {isSubmitting ? '送信中...' : '送信'}
        </button>
      </form>
    </div>
  )
}
