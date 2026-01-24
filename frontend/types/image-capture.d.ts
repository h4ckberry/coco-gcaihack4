// Type definitions for W3C Image Capture API
// Project: https://www.w3.org/TR/image-capture/

interface ImageCapture {
  takePhoto(photoSettings?: any): Promise<Blob>;
  getPhotoCapabilities(): Promise<any>;
  getPhotoSettings(): Promise<any>;
  grabFrame(): Promise<ImageBitmap>;
  track: MediaStreamTrack;
}

declare var ImageCapture: {
  prototype: ImageCapture;
  new(track: MediaStreamTrack): ImageCapture;
};

interface Window {
  ImageCapture: typeof ImageCapture;
}
