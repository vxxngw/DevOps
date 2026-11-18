import { ButtonHTMLAttributes, ReactNode } from 'react';
import { Spinner, Icon } from './icons';
export function Button({
  children,
  busy = false,
  variant = 'primary',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  busy?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
}) {
  return (
    <button
      type="button"
      className={`button button-${variant}`}
      {...props}
      disabled={props.disabled || busy}
      aria-busy={busy}
    >
      {busy && <Spinner />}
      {children}
    </button>
  );
}
export function Notice({
  kind,
  children,
}: {
  kind: 'error' | 'success' | 'info';
  children: ReactNode;
}) {
  return (
    <div
      className={`notice notice-${kind}`}
      role={kind === 'error' ? 'alert' : kind === 'success' ? 'status' : undefined}
    >
      <Icon name={kind === 'success' ? 'check' : 'info'} />
      <div>{children}</div>
    </div>
  );
}
export function Toggle({
  id,
  checked,
  disabled,
  onChange,
  title,
  description,
  busy = false,
  error = false,
}: {
  id: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
  title: string;
  description: string;
  busy?: boolean;
  error?: boolean;
}) {
  return (
    <div className="toggle-row">
      <div className="toggle-description">
        <label htmlFor={id}>{title}</label>
        <p
          id={`${id}-help`}
          className={error ? 'reminder-error' : undefined}
          role={error ? 'alert' : undefined}
          aria-live={error ? undefined : 'polite'}
        >
          {description}
        </p>
      </div>
      {busy && <Spinner />}
      <input
        id={id}
        className="switch"
        type="checkbox"
        role="switch"
        checked={checked}
        disabled={disabled || busy}
        onChange={(event) => onChange(event.target.checked)}
        aria-describedby={`${id}-help`}
      />
    </div>
  );
}
