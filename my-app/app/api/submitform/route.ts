// app/api/submitform/route.ts

import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  try {
    const data = await req.json()  
    console.log('Form data received:', data)

    const response = await fetch('http://localhost:8000/execute', {
      method: 'POST',
      body: JSON.stringify(data)
    })
    const responseData = await response.json()
    const { sessionId, debuggingUrl, status, title } = responseData

    return NextResponse.json({ 
      sessionId,
      debuggingUrl,
      status,
      title
     })
  } catch (error) {
    console.error(error)
    return NextResponse.json({ error: 'Something went wrong' }, { status: 500 })
  }
}

