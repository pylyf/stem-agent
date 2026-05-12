export type Theme = {
  radius: number;
  color: "blue" | "green" | "gray";
};

export const defaultTheme: Theme = {
  radius: 6,
  color: "blue",
};

export function resolveTheme(theme?: Partial<Theme>): Theme {
  return { ...defaultTheme, ...theme };
}
