import type { ReactNode } from "react";

export type CardProps = {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function Card({ title, children, footer }: CardProps) {
  return (
    <section className="ui-card">
      <header>{title}</header>
      <div>{children}</div>
      {footer ? <footer>{footer}</footer> : null}
    </section>
  );
}
