const TONES = 5;
export function Avatar({ name }: { name: string }) {
  const words = name
    .replace(/^(BS|ThS|TS|PGS|GS)\.?\s+/i, '')
    .trim()
    .split(/\s+/);
  const initials = words
    .slice(-2)
    .map((word) => word.charAt(0))
    .join('')
    .toLocaleUpperCase('vi');
  const tone = [...name].reduce((sum, char) => sum + char.charCodeAt(0), 0) % TONES;
  return (
    <span className={`avatar avatar-tone-${tone}`} aria-hidden="true">
      {initials}
    </span>
  );
}
