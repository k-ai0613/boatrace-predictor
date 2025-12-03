import { NextResponse } from 'next/server'
import { getTopRacers } from '@/lib/analytics'

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')

    const racers = await getTopRacers(limit)
    return NextResponse.json(racers)
  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'データの取得に失敗しました' },
      { status: 500 }
    )
  }
}
