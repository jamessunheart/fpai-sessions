import { NextRequest, NextResponse } from 'next/server'
import crypto from 'crypto'

export async function POST(request: NextRequest) {
  try {
    const { email, password } = await request.json()

    const adminEmail = process.env.ADMIN_EMAIL
    const adminPasswordHash = process.env.ADMIN_PASSWORD_HASH

    if (!adminEmail || !adminPasswordHash) {
      console.error('Environment variables not loaded')
      return NextResponse.json({ success: false, error: 'Server configuration error' }, { status: 500 })
    }

    const passwordHash = crypto.createHash('sha256').update(password).digest('hex')

    if (email === adminEmail && passwordHash === adminPasswordHash) {
      return NextResponse.json({ success: true })
    }

    return NextResponse.json({ success: false }, { status: 401 })
  } catch (error) {
    console.error('Login error:', error)
    return NextResponse.json({ success: false }, { status: 500 })
  }
}
