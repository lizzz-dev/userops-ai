import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "UserOps AI",
    short_name: "UserOps",
    description: "Natural-language user operations workspace",
    start_url: "/",
    display: "standalone",
    background_color: "#020617",
    theme_color: "#020617",
    icons: [
      {
        src: "/userops-logo.svg",
        sizes: "any",
        type: "image/svg+xml",
      },
    ],
  };
}
