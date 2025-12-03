import { NextRequest, NextResponse } from 'next/server'
import { supabase, isSupabaseAvailable } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  try {
    if (!isSupabaseAvailable()) {
      return NextResponse.json(
        { error: 'データベース接続が設定されていません' },
        { status: 503 }
      )
    }

    const searchParams = request.nextUrl.searchParams
    const venueId = searchParams.get('venue_id')
    const date = searchParams.get('date')

    if (!venueId) {
      return NextResponse.json(
        { error: 'Venue ID is required' },
        { status: 400 }
      )
    }

    let query = supabase
      .from('weather_data')
      .select('*')
      .eq('venue_id', parseInt(venueId))
      .order('record_datetime', { ascending: false })

    if (date) {
      // 指定日の天気データを取得
      const startDate = new Date(date)
      const endDate = new Date(date)
      endDate.setDate(endDate.getDate() + 1)

      query = query
        .gte('record_datetime', startDate.toISOString())
        .lt('record_datetime', endDate.toISOString())
    } else {
      // 最新のデータのみ取得
      query = query.limit(1)
    }

    const { data, error } = await query

    if (error) {
      console.error('Weather data fetch error:', error)
      return NextResponse.json(
        { error: 'Failed to fetch weather data' },
        { status: 500 }
      )
    }

    return NextResponse.json({ weather: data })

  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    if (!isSupabaseAvailable()) {
      return NextResponse.json(
        { error: 'データベース接続が設定されていません' },
        { status: 503 }
      )
    }

    const weatherData = await request.json()

    const { data, error } = await supabase
      .from('weather_data')
      .insert(weatherData)
      .select()

    if (error) {
      console.error('Weather data insert error:', error)
      return NextResponse.json(
        { error: 'Failed to insert weather data' },
        { status: 500 }
      )
    }

    return NextResponse.json({ data }, { status: 201 })

  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
