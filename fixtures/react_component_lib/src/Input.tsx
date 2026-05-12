export type InputProps = {
  label: string;
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
};

export function Input({ label, value, disabled = false, onChange }: InputProps) {
  return (
    <label className="ui-input">
      <span>{label}</span>
      <input disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}
