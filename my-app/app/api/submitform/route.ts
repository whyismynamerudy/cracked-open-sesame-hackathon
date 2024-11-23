// app/api/submitform/route.ts

import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  try {
    const data = await req.json()  
    console.log('Form data received:', data)

    
    return NextResponse.json({ message: 'Form submitted successfully!' })
  } catch (error) {
    console.error(error)
    return NextResponse.json({ error: 'Something went wrong' }, { status: 500 })
  }
}

