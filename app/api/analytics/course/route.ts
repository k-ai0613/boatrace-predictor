import { NextResponse } from 'next/server'
import { getCourseStatistics } from '@/lib/analytics'

export async function GET() {
  try {
    const stats = await getCourseStatistics()
    return NextResponse.json(stats)
  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'データの取得に失敗しました' },
      { status: 500 }
    )
  }
}
