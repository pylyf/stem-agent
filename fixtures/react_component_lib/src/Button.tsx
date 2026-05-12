import React from "react";

export type ButtonProps = {
  label: string;
  variant?: "primary" | "secondary";
  onClick?: () => void;
};

export function Button({ label, variant = "primary", onClick }: ButtonProps) {
  return (
    <button data-variant={variant} onClick={onClick}>
      {label}
    </button>
  );
}
