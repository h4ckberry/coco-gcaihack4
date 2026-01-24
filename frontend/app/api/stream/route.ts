import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import os from 'os';

// Path to store the temporary image frame
const TMP_FILE_PATH = path.join(os.tmpdir(), 'latest_frame.jpg');

export async function GET() {
  try {
    if (fs.existsSync(TMP_FILE_PATH)) {
      const imageBuffer = fs.readFileSync(TMP_FILE_PATH);
      return new NextResponse(imageBuffer, {
        headers: {
          'Content-Type': 'image/jpeg',
          'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
        },
      });
    } else {
        // Return a 404 or a placeholder if no frame yet
        return new NextResponse("No signal", { status: 404 });
    }
  } catch (error) {
    console.error("Error reading frame:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    // Expecting base64 data in the body or formData
    const body = await req.json();
    const { image } = body; // Expecting "data:image/jpeg;base64,..."

    if (!image) {
      return new NextResponse("No image data provided", { status: 400 });
    }

    // Strip the prefix "data:image/jpeg;base64,"
    const base64Data = image.replace(/^data:image\/\w+;base64,/, "");
    const buffer = Buffer.from(base64Data, 'base64');

    fs.writeFileSync(TMP_FILE_PATH, buffer);

    return new NextResponse("Frame received", { status: 200 });
  } catch (error) {
    console.error("Error saving frame:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
}
