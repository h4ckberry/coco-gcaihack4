/**
 * Calculates the percentage difference between two image data objects.
 *
 * @param prevData - The previous frame's ImageData
 * @param currentData - The current frame's ImageData
 * @param threshold - The sensitivity threshold for pixel difference (0-255). Default 30.
 * @returns Percentage of pixels that are significantly different (0-100).
 */
export function compareFrames(
  prevData: ImageData,
  currentData: ImageData,
  threshold: number = 30
): number {
  if (prevData.width !== currentData.width || prevData.height !== currentData.height) {
    console.warn("Frame dimensions do not match");
    return 100; // Treat as 100% different if dimensions change
  }

  let diffPixels = 0;
  const totalPixels = prevData.width * prevData.height;
  const len = prevData.data.length; // 4 * totalPixels

  // Loop through pixels (R, G, B, A) -> stride 4
  for (let i = 0; i < len; i += 4) {
    const rDiff = Math.abs(prevData.data[i] - currentData.data[i]);
    const gDiff = Math.abs(prevData.data[i + 1] - currentData.data[i + 1]);
    const bDiff = Math.abs(prevData.data[i + 2] - currentData.data[i + 2]);

    // Simple sum of differences
    if (rDiff + gDiff + bDiff > threshold * 3) {
      diffPixels++;
    }
  }

  return (diffPixels / totalPixels) * 100;
}

/**
 * Calculates the average brightness of a frame.
 * @param frameData - The ImageData of the frame.
 * @returns Average brightness (0-255).
 */
export function calculateBrightness(frameData: ImageData): number {
  if (!frameData || !frameData.data) return 0;

  let totalBrightness = 0;
  const len = frameData.data.length;
  const totalPixels = len / 4;

  for (let i = 0; i < len; i += 4) {
    const r = frameData.data[i];
    const g = frameData.data[i + 1];
    const b = frameData.data[i + 2];
    // Simple average or luminance formula. Using simple average for speed.
    totalBrightness += (r + g + b) / 3;
  }

  return totalBrightness / totalPixels;
}
