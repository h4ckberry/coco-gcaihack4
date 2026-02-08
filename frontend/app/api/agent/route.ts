import { NextRequest, NextResponse } from 'next/server';
import { ReasoningEngineExecutionServiceClient } from '@google-cloud/aiplatform';

// Environment variables
const PROJECT_ID = process.env.NEXT_PUBLIC_PROJECT_ID || 'ai-coco';
const LOCATION = process.env.NEXT_PUBLIC_LOCATION || 'us-west1';
const REASONING_ENGINE_ID = process.env.REASONING_ENGINE_ID;

// Initialize Client
// Regional endpoint is crucial for Vertex AI resources
const clientOptions = {
  apiEndpoint: `${LOCATION}-aiplatform.googleapis.com`,
  projectId: PROJECT_ID,
};

const client = new ReasoningEngineExecutionServiceClient(clientOptions);

// Timeout for long-running queries (120 seconds = 2 minutes)
const CALL_TIMEOUT_MS = 120000;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { query } = body;
    let { session_id } = body;

    // Fully qualified resource name
    const name = `projects/${PROJECT_ID}/locations/${LOCATION}/reasoningEngines/${REASONING_ENGINE_ID}`;

    console.log(`Sending query to Reasoning Engine (${name}): ${query}, session_id: ${session_id}`);

    // 1. Create Session if not exists
    if (!session_id) {
      console.log("No session_id provided. Creating new session...");
      const createRequest = {
        name: name,
        classMethod: 'create_session',
        input: {
          fields: {
            user_id: { stringValue: 'default-user' }
          }
        },
      };


      const [createResponse] = await client.queryReasoningEngine(createRequest as any, {
        timeout: CALL_TIMEOUT_MS
      });

      // Extract session ID from Struct response
      const output = createResponse.output;
      if (output && output.structValue && output.structValue.fields && output.structValue.fields.id) {
        session_id = output.structValue.fields.id.stringValue;
        console.log("Created new session:", session_id);
      } else {
        console.error("Failed to parse session ID from create_session response:", JSON.stringify(createResponse, null, 2));
        return NextResponse.json({ error: 'Failed to create session' }, { status: 500 });
      }
    }

    // 2. Query with session_id using chat method
    if (!query) {
      // If only init was requested
      return NextResponse.json({ session_id });
    }

    const queryRequest = {
      name: name,
      classMethod: 'chat',
      input: {
        fields: {
          session_id: { stringValue: session_id },
          user_input: { stringValue: query },
          user_id: { stringValue: 'default-user' }
        }
      }
    };

    const [queryResponse] = await client.queryReasoningEngine(queryRequest as any, {
      timeout: CALL_TIMEOUT_MS
    });
    console.log("Query Response:", JSON.stringify(queryResponse, null, 2));

    // Parse Response Text
    let responseText = "";
    const out = queryResponse.output;
    if (out && out.structValue && out.structValue.fields && out.structValue.fields.output) {
      responseText = out.structValue.fields.output.stringValue || "";
    } else if (out && out.structValue && out.structValue.fields && out.structValue.fields.error) {
      // Handle error response from backend
      const errorMsg = out.structValue.fields.error.stringValue || "Unknown error";
      console.error("Backend error:", errorMsg);
      return NextResponse.json({ error: errorMsg }, { status: 500 });
    } else if (typeof out === 'string') {
      responseText = out;
    } else {
      responseText = JSON.stringify(out);
    }

    // Extract audio_content from response
    let audioContent: string | null = null;
    if (out && out.structValue && out.structValue.fields && out.structValue.fields.audio_content) {
      audioContent = out.structValue.fields.audio_content.stringValue || null;
    }

    // Cleanup quotes if JSON.stringify added them to a simple string
    if (responseText.startsWith('"') && responseText.endsWith('"')) {
      try {
        const parsed = JSON.parse(responseText);
        if (typeof parsed === 'string') responseText = parsed;
      } catch (e) {
        // ignore
      }
    }

    return NextResponse.json({
      session_id,
      text: responseText,
      audio_content: audioContent
    });

  } catch (error) {
    console.error('Error querying Reasoning Engine:', error);
    return NextResponse.json(
      { error: 'Failed to process request', details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
