import { Card } from "./Card";

export function rendersCardTitle() {
  return Card({ title: "Billing", children: "Content" }).props.children[0].props.children === "Billing";
}
