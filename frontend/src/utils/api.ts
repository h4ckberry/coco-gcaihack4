export interface AnalysisResult {
    found: boolean;
    box_2d: [number, number, number, number] | null;
    label: string | null;
    message: string;
    transcribed_text?: string;
    search_query?: string;
    all_objects: { box_2d: [number, number, number, number]; label: string }[];
    action?: string;
}

export async function analyzeImageAndAudio(
    imageBlob: Blob,
    audioBlob: Blob | null,
    isSubsequentRun: boolean = false,
    previousQuery: string = ""
): Promise<AnalysisResult> {
    const formData = new FormData();

    const imageExt = imageBlob.type.split("/")[1] || "jpeg";
    formData.append("image", imageBlob, `image.${imageExt}`);

    if (audioBlob) {
        const audioExt = audioBlob.type.split("/")[1] || "webm";
        formData.append("audio", audioBlob, `audio.${audioExt}`);
    }

    if (isSubsequentRun) {
        formData.append("is_subsequent_run", "true");
        formData.append("previous_query", previousQuery);
    }

    // Use the Next.js API Proxy to avoid CORS and Mixed Content issues
    const API_URL = "/api/analyze";

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server Error: ${response.status} ${errorText}`);
        }

        return response.json();
    } catch (error: any) {
        // Detailed error for debugging on iPad
        throw new Error(`Network/Fetch Error: ${error.name} - ${error.message}`);
    }
}

export async function monitorEnvironment(
    imageBlob: Blob
): Promise<any> {
    const formData = new FormData();
    const imageExt = imageBlob.type.split("/")[1] || "jpeg";
    formData.append("image", imageBlob, `image.${imageExt}`);

    const API_URL = "/api/monitor";

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Monitor failed: ${response.status} ${errorText}`);
            return null; // Don't throw, just return null to avoid stopping the loop
        }

        return response.json();
    } catch (error: any) {
        console.error(`Monitor Network Error: ${error.message}`);
        return null;
    }
}
