import { useState, useRef, useEffect, FormEvent } from 'react';
import { Session, Doctor, Appointment, Slot, canRemind, dateKey, fullTime } from '../lib/types';
import { request, ApiError } from '../lib/api';
type Banner = {
  kind: 'error' | 'success';
  message: string;
} | null;
export function useClinicApp() {
  const [session, setSession] = useState<Session | null>(null);
  const sessionToken = useRef('');
  const [email, setEmail] = useState('patient@example.test');
  const [password, setPassword] = useState('');
  const [view, setView] = useState<'booking' | 'appointments' | 'admin'>('booking');
  const [adminSection, setAdminSection] = useState<'appointments' | 'setup'>('appointments');
  const [pending, setPending] = useState('');
  const [banner, setBanner] = useState<Banner>(null);
  const [syncError, setSyncError] = useState('');
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [lead, setLead] = useState(60);
  const [step, setStep] = useState(1);
  const [search, setSearch] = useState('');
  const [specialty, setSpecialty] = useState('');
  const [doctorId, setDoctorId] = useState('');
  const [slots, setSlots] = useState<Slot[]>([]);
  const [day, setDay] = useState('');
  const [chosen, setChosen] = useState<Slot | null>(null);
  const [slotLoading, setSlotLoading] = useState(false);
  const [slotError, setSlotError] = useState('');
  const [reminder, setReminder] = useState(true);
  const [confirmed, setConfirmed] = useState<Appointment | null>(null);
  const bookingKey = useRef<{
    signature: string;
    key: string;
  } | null>(null);
  const [filter, setFilter] = useState('');
  const [doctorName, setDoctorName] = useState('');
  const [newSpecialty, setNewSpecialty] = useState('');
  const [adminDoctor, setAdminDoctor] = useState('');
  const [slotTime, setSlotTime] = useState('');
  const selectedDoctor = doctors.find((doctor) => doctor.id === doctorId);
  const selectedAvailable = Boolean(
    chosen && slots.some((slot) => slot.id === chosen.id && slot.available),
  );
  const reminderEligible = Boolean(chosen && canRemind(chosen, lead));
  const effectiveReminder = reminder && reminderEligible;
  const busy = Boolean(pending);
  const days = [...new Set(slots.map((slot) => dateKey(slot.starts_at)))];
  const daySlots = slots.filter((slot) => dateKey(slot.starts_at) === day);
  const specialties = [...new Set(doctors.map((doctor) => doctor.specialty))].sort();
  const visibleDoctors = doctors.filter(
    (doctor) =>
      (!specialty || doctor.specialty === specialty) &&
      `${doctor.name} ${doctor.specialty}`
        .toLocaleLowerCase('vi')
        .includes(search.toLocaleLowerCase('vi')),
  );
  const liveConfirmation =
    appointments.find((appointment) => appointment.id === confirmed?.id) || confirmed;
  async function act(key: string, work: () => Promise<void>) {
    setPending(key);
    setBanner(null);
    try {
      await work();
    } catch (error) {
      setBanner({
        kind: 'error',
        message: error instanceof Error ? error.message : 'Chưa thể hoàn tất. Vui lòng thử lại.',
      });
    } finally {
      setPending('');
    }
  }
  async function refreshAppointments(auth = session) {
    if (!auth) return;
    const list = await request<Appointment[]>(
      auth.role === 'admin' ? '/api/admin/appointments' : '/api/appointments',
      auth.token,
    );
    if (sessionToken.current === auth.token) {
      setAppointments(list);
      setSyncError('');
    }
  }
  async function safeRefresh() {
    try {
      await refreshAppointments();
    } catch {
      setSyncError('Chưa cập nhật được trạng thái mới. Vui lòng bấm Làm mới để thử lại.');
    }
  }
  async function reloadSlots() {
    if (!session || !doctorId) return;
    const list = await request<Slot[]>(
      `/api/doctors/${doctorId}/slots?include_unavailable=true`,
      session.token,
    );
    if (sessionToken.current === session.token) {
      setSlots(list);
      setSlotError('');
      setDay((current) =>
        list.some((slot) => dateKey(slot.starts_at) === current)
          ? current
          : list[0]
            ? dateKey(list[0].starts_at)
            : '',
      );
    }
  }
  useEffect(() => {
    if (!session || !doctorId) return;
    const controller = new AbortController();
    setSlotLoading(true);
    setSlotError('');
    request<Slot[]>(`/api/doctors/${doctorId}/slots?include_unavailable=true`, session.token, {
      signal: controller.signal,
    })
      .then((list) => {
        if (!controller.signal.aborted) {
          setSlots(list);
          setDay((current) =>
            list.some((slot) => dateKey(slot.starts_at) === current)
              ? current
              : list[0]
                ? dateKey(list[0].starts_at)
                : '',
          );
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) setSlotError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setSlotLoading(false);
      });
    return () => controller.abort();
  }, [session, doctorId]);
  useEffect(() => {
    if (!session) return;
    const timer = window.setInterval(() => {
      safeRefresh();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [session]);
  async function login(event: FormEvent) {
    event.preventDefault();
    await act('login', async () => {
      const result = await request<{
        access_token: string;
        role: Session['role'];
      }>('/api/auth/login', '', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const auth = {
        token: result.access_token,
        role: result.role,
        email: email.trim().toLowerCase(),
      };
      const [doctorList, options, appointmentList] = await Promise.all([
        request<Doctor[]>('/api/doctors', auth.token),
        request<{
          reminder_lead_minutes: number;
        }>('/api/options', auth.token),
        request<Appointment[]>(
          auth.role === 'admin' ? '/api/admin/appointments' : '/api/appointments',
          auth.token,
        ),
      ]);
      sessionToken.current = auth.token;
      setSession(auth);
      setPassword('');
      setDoctors(doctorList);
      setAdminDoctor(doctorList[0]?.id || '');
      setLead(options.reminder_lead_minutes);
      setAppointments(appointmentList);
      setView(auth.role === 'admin' ? 'admin' : 'booking');
      setAdminSection('appointments');
    });
  }
  function logout() {
    sessionToken.current = '';
    setSession(null);
    setAppointments([]);
    setBanner(null);
    setSyncError('');
    setDoctorId('');
    setChosen(null);
    setSlots([]);
    setStep(1);
    setConfirmed(null);
    setFilter('');
    bookingKey.current = null;
  }
  function chooseDoctor(id: string) {
    if (id !== doctorId) {
      setDoctorId(id);
      setChosen(null);
      setSlots([]);
      setDay('');
    }
  }
  function newBooking() {
    setConfirmed(null);
    setChosen(null);
    setStep(1);
    setBanner(null);
    bookingKey.current = null;
    setView('booking');
  }
  async function book() {
    if (!session || !chosen) return;
    await act('book', async () => {
      const payload = { slot_id: chosen.id, reminder_enabled: effectiveReminder };
      const signature = JSON.stringify(payload);
      if (bookingKey.current?.signature !== signature)
        bookingKey.current = { signature, key: crypto.randomUUID() };
      let result: Appointment;
      try {
        result = await request<Appointment>('/api/appointments', session.token, {
          method: 'POST',
          headers: { 'Idempotency-Key': bookingKey.current.key },
          body: signature,
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) await reloadSlots().catch(() => {});
        throw error;
      }
      setConfirmed(result);
      setAppointments((current) => [
        result,
        ...current.filter((appointment) => appointment.id !== result.id),
      ]);
      bookingKey.current = null;
      await safeRefresh();
      await reloadSlots().catch(() => {});
    });
  }
  async function cancel(appointment: Appointment) {
    if (
      !session ||
      !window.confirm(
        `Bạn muốn hủy lịch khám với ${appointment.doctor} vào ${fullTime(appointment.slot)}?`,
      )
    )
      return;
    await act(`cancel:${appointment.id}`, async () => {
      const result = await request<Appointment>(
        `/api/appointments/${appointment.id}/cancel`,
        session.token,
        { method: 'POST' },
      );
      setAppointments((current) => current.map((item) => (item.id === result.id ? result : item)));
      setBanner({
        kind: 'success',
        message: 'Đã hủy lịch hẹn và dừng nhắc lịch. Email cập nhật sẽ được gửi đến bạn.',
      });
      await reloadSlots().catch(() => {});
    });
  }
  async function toggleReminder(appointment: Appointment, enabled: boolean) {
    if (!session) return;
    await act(`reminder:${appointment.id}`, async () => {
      const result = await request<Appointment>(
        `/api/appointments/${appointment.id}/reminder`,
        session.token,
        { method: 'PATCH', body: JSON.stringify({ enabled }) },
      );
      setAppointments((current) => current.map((item) => (item.id === result.id ? result : item)));
      setBanner({
        kind: 'success',
        message: enabled ? 'Đã bật nhắc lịch qua email.' : 'Đã tắt nhắc lịch cho lịch hẹn này.',
      });
    });
  }
  return {
    act,
    adminDoctor,
    adminSection,
    appointments,
    banner,
    book,
    bookingKey,
    busy,
    cancel,
    chooseDoctor,
    chosen,
    confirmed,
    day,
    daySlots,
    days,
    doctorId,
    doctorName,
    doctors,
    effectiveReminder,
    email,
    filter,
    lead,
    liveConfirmation,
    login,
    logout,
    newBooking,
    newSpecialty,
    password,
    pending,
    refreshAppointments,
    reloadSlots,
    reminder,
    reminderEligible,
    safeRefresh,
    search,
    selectedAvailable,
    selectedDoctor,
    session,
    sessionToken,
    setAdminDoctor,
    setAdminSection,
    setAppointments,
    setBanner,
    setChosen,
    setConfirmed,
    setDay,
    setDoctorId,
    setDoctorName,
    setDoctors,
    setEmail,
    setFilter,
    setLead,
    setNewSpecialty,
    setPassword,
    setPending,
    setReminder,
    setSearch,
    setSession,
    setSlotError,
    setSlotLoading,
    setSlotTime,
    setSlots,
    setSpecialty,
    setStep,
    setSyncError,
    setView,
    slotError,
    slotLoading,
    slotTime,
    slots,
    specialties,
    specialty,
    step,
    syncError,
    toggleReminder,
    view,
    visibleDoctors,
  };
}
export type ClinicController = ReturnType<typeof useClinicApp>;
