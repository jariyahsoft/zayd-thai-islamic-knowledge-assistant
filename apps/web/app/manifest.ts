import type { MetadataRoute } from "next";
import { createUserAppManifest } from "@zayd/ui";

export default function manifest(): MetadataRoute.Manifest {
  const manifestData = createUserAppManifest();
  return {
    ...manifestData,
    icons: manifestData.icons.map((icon) => ({
      src: icon.src,
      sizes: icon.sizes,
      type: icon.type,
      purpose: icon.purpose,
    })),
  };
}