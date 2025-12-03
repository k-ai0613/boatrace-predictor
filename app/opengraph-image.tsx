import { ImageResponse } from 'next/og'

export const runtime = 'edge'

export const alt = 'ボートレース予測AI - 競艇レース予測分析ツール'
export const size = {
  width: 1200,
  height: 630,
}
export const contentType = 'image/png'

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 48,
          background: 'linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%)',
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          padding: '40px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            marginBottom: '20px',
          }}
        >
          <svg
            width="80"
            height="80"
            viewBox="0 0 24 24"
            fill="none"
            style={{ marginRight: '20px' }}
          >
            <path
              d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span style={{ fontSize: '64px', fontWeight: 'bold' }}>
            ボートレース予測AI
          </span>
        </div>
        <div
          style={{
            fontSize: '32px',
            opacity: 0.9,
            marginBottom: '40px',
          }}
        >
          AI機械学習による競艇レース予測
        </div>
        <div
          style={{
            display: 'flex',
            gap: '40px',
            fontSize: '24px',
          }}
        >
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              background: 'rgba(255,255,255,0.15)',
              padding: '20px 30px',
              borderRadius: '12px',
            }}
          >
            <span style={{ fontSize: '36px', fontWeight: 'bold' }}>5年分</span>
            <span>データ分析</span>
          </div>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              background: 'rgba(255,255,255,0.15)',
              padding: '20px 30px',
              borderRadius: '12px',
            }}
          >
            <span style={{ fontSize: '36px', fontWeight: 'bold' }}>40万+</span>
            <span>レースデータ</span>
          </div>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              background: 'rgba(255,255,255,0.15)',
              padding: '20px 30px',
              borderRadius: '12px',
            }}
          >
            <span style={{ fontSize: '36px', fontWeight: 'bold' }}>無料</span>
            <span>利用可能</span>
          </div>
        </div>
      </div>
    ),
    {
      ...size,
    }
  )
}
