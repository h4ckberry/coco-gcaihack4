/**
 * Calculates the average brightness of an image data.
 * @param frameData The ImageData from a canvas.
 * @returns A value between 0 (black) and 255 (white).
 */
export const calculateBrightness = (frameData: ImageData): number => {
  const data = frameData.data;
  let r, g, b, avg;
  let colorSum = 0;

  for (let x = 0, len = data.length; x < len; x += 4) {
    r = data[x];
    g = data[x + 1];
    b = data[x + 2];

    avg = Math.floor((r + g + b) / 3);
    colorSum += avg;
  }

  const brightness = Math.floor(colorSum / (frameData.width * frameData.height));
  return brightness;
};

/**
 * Compares two image data frames and returns the percentage difference.
 * Uses a simple pixel-by-pixel comparison and a threshold.
 * @param oldFrame The previous ImageData.
 * @param newFrame The current ImageData.
 * @param threshold Pixel difference threshold (0-255).
 * @returns Percentage of pixels that are different (0-100).
 */
export const compareFrames = (oldFrame: ImageData, newFrame: ImageData, threshold: number = 30): number => {
  if (oldFrame.data.length !== newFrame.data.length) return 100;

  let diffPixels = 0;
  const totalPixels = oldFrame.width * oldFrame.height;
  const data1 = oldFrame.data;
  const data2 = newFrame.data;

  for (let i = 0; i < data1.length; i += 4) {
    const rDiff = Math.abs(data1[i] - data2[i]);
    const gDiff = Math.abs(data1[i + 1] - data2[i + 1]);
    const bDiff = Math.abs(data1[i + 2] - data2[i + 2]);

    if (rDiff + gDiff + bDiff > threshold) {
      diffPixels++;
    }
  }

  return (diffPixels / totalPixels) * 100;
};
