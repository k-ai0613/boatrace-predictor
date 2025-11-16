import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// 日付フォーマット
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// パーセント表示
export function formatPercent(value: number, decimals: number = 1): string {
  return `${(value * 100).toFixed(decimals)}%`
}

// 級別スコア変換
export function gradeToScore(grade: string): number {
  const scores: { [key: string]: number } = {
    'A1': 4,
    'A2': 3,
    'B1': 2,
    'B2': 1
  }
  return scores[grade] || 0
}

// 艇番の色取得
export function getBoatColor(boatNumber: number): string {
  const colors: { [key: number]: string } = {
    1: 'bg-white text-black border-2 border-black',
    2: 'bg-black text-white',
    3: 'bg-red-600 text-white',
    4: 'bg-blue-600 text-white',
    5: 'bg-yellow-500 text-black',
    6: 'bg-green-600 text-white'
  }
  return colors[boatNumber] || 'bg-gray-600 text-white'
}

// 風向きを度数から文字列に変換
export function windDirectionToText(degrees: number): string {
  const directions = ['北', '北北東', '北東', '東北東', '東', '東南東', '南東', '南南東',
                     '南', '南南西', '南西', '西南西', '西', '西北西', '北西', '北北西']
  const index = Math.round(degrees / 22.5) % 16
  return directions[index]
}
