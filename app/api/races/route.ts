import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const date = searchParams.get('date')
    const venueId = searchParams.get('venue_id')
    const raceNumber = searchParams.get('race_number')

    const supabase = createServerClient()

    if (!supabase) {
      return NextResponse.json(
        { error: 'データベース接続が設定されていません' },
        { status: 503 }
      )
    }

    // レースデータ取得
    let raceQuery = supabase
      .from('races')
      .select('*')
      .order('race_number', { ascending: true })

    if (date) {
      raceQuery = raceQuery.eq('race_date', date)
    }

    if (venueId) {
      raceQuery = raceQuery.eq('venue_id', parseInt(venueId))
    }

    if (raceNumber) {
      raceQuery = raceQuery.eq('race_number', parseInt(raceNumber))
    }

    const { data: races, error: raceError } = await raceQuery.limit(100)

    if (raceError) {
      console.error('Database error:', raceError)
      return NextResponse.json(
        { error: 'Failed to fetch races' },
        { status: 500 }
      )
    }

    if (!races || races.length === 0) {
      return NextResponse.json(raceNumber ? null : { races: [] })
    }

    // レースごとにエントリーと選手データを取得
    const racesWithEntries = await Promise.all(
      races.map(async (race) => {
        const { data: entries, error: entriesError } = await supabase
          .from('race_entries')
          .select('*')
          .eq('race_id', race.id)
          .order('boat_number', { ascending: true })

        if (entriesError) {
          console.error('Entries error:', entriesError)
          return { ...race, race_entries: [] }
        }

        // 選手データを取得
        const entriesWithRacers = await Promise.all(
          (entries || []).map(async (entry) => {
            const { data: racer, error: racerError } = await supabase
              .from('racers')
              .select('*')
              .eq('id', entry.racer_id)
              .single()

            if (racerError) {
              console.error('Racer fetch error:', racerError)
              return { ...entry, racer: null }
            }

            return { ...entry, racer }
          })
        )

        return {
          ...race,
          race_entries: entriesWithRacers
        }
      })
    )

    // raceNumberが指定されている場合は単一のレースを返す
    if (raceNumber) {
      return NextResponse.json(racesWithEntries[0] || null)
    }

    return NextResponse.json({ races: racesWithEntries })

  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
