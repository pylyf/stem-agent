import { useCallback, useState } from "react";

export function useDisclosure(initial = false) {
  const [open, setOpen] = useState(initial);
  const show = useCallback(() => setOpen(true), []);
  const hide = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen((value) => !value), []);
  return { open, show, hide, toggle };
}
