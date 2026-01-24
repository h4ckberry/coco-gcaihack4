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
