import { Icon } from '../../components/ui/icons';
import { request } from '../../lib/api';
import { Doctor } from '../../lib/types';
import { Button } from '../../components/ui';
import type { ClinicController } from '../../app/useClinicApp';
type Props = Pick<
  ClinicController,
  | 'act'
  | 'adminDoctor'
  | 'busy'
  | 'doctorName'
  | 'doctors'
  | 'newSpecialty'
  | 'pending'
  | 'session'
  | 'setAdminDoctor'
  | 'setBanner'
  | 'setDoctorName'
  | 'setDoctors'
  | 'setNewSpecialty'
  | 'setSlotTime'
  | 'slotTime'
>;
export function AdminSetup({
  act,
  adminDoctor,
  busy,
  doctorName,
  doctors,
  newSpecialty,
  pending,
  session,
  setAdminDoctor,
  setBanner,
  setDoctorName,
  setDoctors,
  setNewSpecialty,
  setSlotTime,
  slotTime,
}: Props) {
  if (!session) return null;
  return (
    <div className="admin-layout">
      <section className="card">
        <div className="panel-heading">
          <div>
            <h2>Thêm bác sĩ</h2>
            <p>Cập nhật danh sách bác sĩ của phòng khám.</p>
          </div>
          <Icon name="user" />
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            act('doctor', async () => {
              await request('/api/admin/doctors', session.token, {
                method: 'POST',
                body: JSON.stringify({ name: doctorName, specialty: newSpecialty }),
              });
              setDoctorName('');
              setNewSpecialty('');
              setBanner({ kind: 'success', message: 'Đã thêm bác sĩ.' });
              const list = await request<Doctor[]>('/api/doctors', session.token).catch(() => null);
              if (list) setDoctors(list);
              else
                setBanner({
                  kind: 'success',
                  message: 'Đã thêm bác sĩ. Vui lòng tải lại trang để cập nhật danh sách.',
                });
            });
          }}
        >
          <div className="field">
            <label htmlFor="doctor-name">Họ tên</label>
            <input
              id="doctor-name"
              value={doctorName}
              onChange={(event) => setDoctorName(event.target.value)}
              maxLength={100}
              required
              disabled={busy}
            />
          </div>
          <div className="field">
            <label htmlFor="doctor-specialty">Chuyên khoa</label>
            <input
              id="doctor-specialty"
              value={newSpecialty}
              onChange={(event) => setNewSpecialty(event.target.value)}
              maxLength={100}
              required
              disabled={busy}
            />
          </div>
          <Button type="submit" busy={pending === 'doctor'} disabled={busy}>
            Thêm bác sĩ
          </Button>
        </form>
      </section>
      <section className="card">
        <div className="panel-heading">
          <div>
            <h2>Thêm khung giờ</h2>
            <p>Mỗi khung khám mới kéo dài 30 phút.</p>
          </div>
          <Icon name="calendar" />
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            act('slot', async () => {
              const start = new Date(slotTime + ':00+07:00');
              await request('/api/admin/slots', session.token, {
                method: 'POST',
                body: JSON.stringify({
                  doctor_id: adminDoctor,
                  starts_at: start.toISOString(),
                  ends_at: new Date(start.getTime() + 1800000).toISOString(),
                }),
              });
              setSlotTime('');
              setBanner({ kind: 'success', message: 'Đã thêm khung khám 30 phút.' });
            });
          }}
        >
          <div className="field">
            <label htmlFor="admin-doctor">Bác sĩ</label>
            <select
              id="admin-doctor"
              value={adminDoctor}
              onChange={(event) => setAdminDoctor(event.target.value)}
              required
              disabled={busy}
            >
              {doctors.map((doctor) => (
                <option key={doctor.id} value={doctor.id}>
                  {doctor.name} · {doctor.specialty}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="slot-time">Bắt đầu (giờ Việt Nam)</label>
            <input
              id="slot-time"
              type="datetime-local"
              value={slotTime}
              onChange={(event) => setSlotTime(event.target.value)}
              required
              disabled={busy}
            />
          </div>
          <Button type="submit" busy={pending === 'slot'} disabled={busy || !adminDoctor}>
            Thêm khung 30 phút
          </Button>
        </form>
      </section>
    </div>
  );
}
