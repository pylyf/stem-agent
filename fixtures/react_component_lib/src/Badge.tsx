import React from "react";

export type BadgeProps = {
  tone?: "info" | "warning";
  children: React.ReactNode;
};

export function Badge({ tone = "info", children }: BadgeProps) {
  return <span data-tone={tone}>{children}</span>;
}
