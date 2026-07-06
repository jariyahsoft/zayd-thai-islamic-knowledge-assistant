export const roles = ["guest", "user", "reviewer", "admin"] as const;

export type Role = (typeof roles)[number];
