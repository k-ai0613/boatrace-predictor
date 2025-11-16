import { NextRequest, NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const date = searchParams.get('date')
    const venueId = searchParams.get('venue_id')

    let query = supabase
      .from('races')
      .select('*')
      .order('race_date', { ascending: false })
      .order('venue_id')
      .order('race_number')

    if (date) {
      query = query.eq('race_date', date)
    }

    if (venueId) {
      query = query.eq('venue_id', parseInt(venueId))
    }

    const { data, error } = await query.limit(100)

    if (error) {
      console.error('Database error:', error)
      return NextResponse.json(
        { error: 'Failed to fetch races' },
        { status: 500 }
      )
    }

    return NextResponse.json({ races: data })

  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
