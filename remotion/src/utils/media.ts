import { staticFile } from "remotion";

export function resolveMediaSrc(src?: string): string | undefined {
  if (!src) return undefined;
  if (
    src.startsWith("data:") ||
    src.startsWith("http://") ||
    src.startsWith("https://") ||
    src.startsWith("blob:")
  ) {
    return src;
  }
  // Clean leading slash for staticFile
  const cleanPath = src.startsWith("/") ? src.slice(1) : src;
  return staticFile(cleanPath);
}
