import { useState, useEffect, useCallback } from 'react';

// Define SpeechRecognition types (since they might be missing in TS)
interface SpeechRecognitionEvent extends Event {
    results: SpeechRecognitionResultList;
}

interface SpeechRecognitionResultList {
    length: number;
    item(index: number): SpeechRecognitionResult;
    [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
    isFinal: boolean;
    length: number;
    item(index: number): SpeechRecognitionAlternative;
    [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
    transcript: string;
    confidence: number;
}

interface SpeechRecognition extends EventTarget {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    start(): void;
    stop(): void;
    abort(): void;
    onresult: (event: SpeechRecognitionEvent) => void;
    onend: () => void;
    onerror: (event: any) => void;
}

declare global {
    interface Window {
        SpeechRecognition: any;
        webkitSpeechRecognition: any;
    }
}

export function useSpeechRecognition() {
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (SpeechRecognition) {
                const reco = new SpeechRecognition();
                reco.continuous = false; // Stop after one sentence
                reco.interimResults = false;
                reco.lang = 'ja-JP';

                reco.onresult = (event: SpeechRecognitionEvent) => {
                    const last = event.results.length - 1;
                    const result = event.results[last][0];
                    const text = result.transcript.trim();
                    const confidence = result.confidence;

                    console.log(`STT Raw: "${text}" (Conf: ${confidence})`);

                    // Noise Filter: Ignore short utterances or low confidence (if supported)
                    if (text.length < 2) {
                        console.log("Ignored: Too short (likely noise)");
                        return;
                    }

                    // Optional: Japanese/mixed check. 
                    // Allowing generic text for now, but skipping obviously empty signals.

                    setTranscript(text);
                };

                reco.onend = () => {
                    setIsListening(false);
                };

                reco.onerror = (event: any) => {
                    console.error("STT Error:", event.error);
                    setIsListening(false);
                };

                setRecognition(reco);
            } else {
                console.warn("Speech Recognition API not supported in this browser.");
            }
        }
    }, []);

    const startListening = useCallback(() => {
        if (recognition) {
            setTranscript('');
            try {
                recognition.start();
                setIsListening(true);
            } catch (e) {
                console.error("Start error (already started?):", e);
            }
        }
    }, [recognition]);

    const stopListening = useCallback(() => {
        if (recognition) {
            recognition.stop();
            setIsListening(false);
        }
    }, [recognition]);

    return { isListening, transcript, startListening, stopListening, setTranscript };
}
