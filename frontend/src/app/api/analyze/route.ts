import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();

        // Forward to Backend (running locally)
        // Note: Since this runs on the server, we can use localhost or 127.0.0.1
        const BACKEND_URL = "http://127.0.0.1:8000/analyze";

        const response = await fetch(BACKEND_URL, {
            method: "POST",
            body: formData,
            // Don't set Content-Type header manually for FormData, fetch does it automatically with boundary
        });

        if (!response.ok) {
            const errorText = await response.text();
            return NextResponse.json(
                { error: `Backend Error: ${response.status} ${errorText}` },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);

    } catch (error: any) {
        console.error("Proxy Error:", error);
        return NextResponse.json(
            { error: `Proxy Error: ${error.message}` },
            { status: 500 }
        );
    }
}
