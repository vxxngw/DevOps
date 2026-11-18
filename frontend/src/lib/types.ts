export type Doctor = { id: string; name: string; specialty: string };
export type Slot = {
  id: string;
  doctor_id: string;
  starts_at: string;
  ends_at: string;
  available: boolean;
};
export type Appointment = {
  id: string;
  doctor: string;
  slot: Omit<Slot, 'available'>;
  status: string;
  version: number;
  notification_status: string;
  notification_error: string | null;
  reminder_enabled: boolean;
  reminder_at: string | null;
  reminder_status: string;
};
export type Session = { token: string; role: 'patient' | 'admin'; email: string };

export const TIMEZONE = 'Asia/Ho_Chi_Minh';
export const dateKey = (iso: string) => {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date(iso));
  return ['year', 'month', 'day']
    .map((type) => parts.find((part) => part.type === type)?.value)
    .join('-');
};
export const dayLabel = (iso: string) =>
  new Intl.DateTimeFormat('vi-VN', {
    timeZone: TIMEZONE,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(iso));
export const timeLabel = (iso: string) =>
  new Intl.DateTimeFormat('vi-VN', {
    timeZone: TIMEZONE,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(iso));
export const weekday = (iso: string) =>
  new Intl.DateTimeFormat('vi-VN', { timeZone: TIMEZONE, weekday: 'short' }).format(new Date(iso));
export const fullTime = (slot: Pick<Slot, 'starts_at' | 'ends_at'>) =>
  `${timeLabel(slot.starts_at)} – ${timeLabel(slot.ends_at)}, ${dayLabel(slot.starts_at)}`;
export const canRemind = (slot: Pick<Slot, 'starts_at'>, lead: number) =>
  new Date(slot.starts_at).getTime() - Date.now() > lead * 60_000;
export const leadLabel = (minutes: number) =>
  minutes % 60 === 0 ? `${minutes / 60} giờ` : `${minutes} phút`;
