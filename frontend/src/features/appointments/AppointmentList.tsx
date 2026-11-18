import { Button, Notice, Toggle } from '../../components/ui';
import { Icon } from '../../components/ui/icons';
import { statusLabel, deliveryLabel, reminderDescription } from '../appointments/labels';
import { dayLabel, timeLabel, canRemind, Appointment } from '../../lib/types';
import { request } from '../../lib/api';
import type { ClinicController } from '../../app/useClinicApp';
type Props = Pick<
  ClinicController,
  | 'act'
  | 'appointments'
  | 'busy'
  | 'cancel'
  | 'filter'
  | 'lead'
  | 'newBooking'
  | 'pending'
  | 'safeRefresh'
  | 'session'
  | 'setAppointments'
  | 'setBanner'
  | 'setFilter'
  | 'syncError'
  | 'toggleReminder'
> & {
  admin?: boolean;
};
export function AppointmentList({
  admin = false,
  act,
  appointments,
  busy,
  cancel,
  filter,
  lead,
  newBooking,
  pending,
  safeRefresh,
  session,
  setAppointments,
  setBanner,
  setFilter,
  syncError,
  toggleReminder,
}: Props) {
  const list = appointments.filter((appointment) => !filter || appointment.status === filter);
  return (
    <section className="card appointments-panel">
      <div className="panel-heading">
        <div>
          <h2>{admin ? 'Danh sách lịch hẹn' : 'Lịch hẹn của tôi'}</h2>
          <p>
            {admin
              ? 'Theo dõi lịch khám và trạng thái thông báo.'
              : 'Xem lịch đã đặt hoặc điều chỉnh nhắc lịch.'}
          </p>
        </div>
        <Button
          variant="secondary"
          busy={pending === 'refresh'}
          onClick={() => act('refresh', safeRefresh)}
        >
          <Icon name="refresh" />
          Làm mới
        </Button>
      </div>
      <div className="filter-row">
        <label htmlFor="appointment-filter">Trạng thái</label>
        <select
          id="appointment-filter"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        >
          <option value="">Tất cả lịch hẹn</option>
          {Object.entries(statusLabel).map(([status, text]) => (
            <option key={status} value={status}>
              {text}
            </option>
          ))}
        </select>
        <span className="result-count">{list.length} lịch hẹn</span>
      </div>
      {syncError && <Notice kind="error">{syncError}</Notice>}
      {!list.length ? (
        <div className="empty-state">
          <span className="empty-icon">
            <Icon name="calendar" size={28} />
          </span>
          <h3>Chưa có lịch hẹn</h3>
          <p>
            {filter
              ? 'Chưa có lịch hẹn ở trạng thái này.'
              : 'Lịch khám của bạn sẽ xuất hiện tại đây sau khi đặt thành công.'}
          </p>
          {!admin && (
            <Button onClick={newBooking}>
              Đặt lịch khám
              <Icon name="next" />
            </Button>
          )}
        </div>
      ) : (
        <ul className="appointment-list">
          {list.map((appointment) => (
            <li className="appointment-item" key={appointment.id} data-appointment={appointment.id}>
              <div className="appointment-top">
                <div className="appointment-doctor">
                  <span className="avatar">
                    <Icon name="user" />
                  </span>
                  <div>
                    <h3>{appointment.doctor}</h3>
                    <p>
                      Mã lịch hẹn <strong>{appointment.id.slice(0, 8).toUpperCase()}</strong>
                    </p>
                  </div>
                </div>
                <span className={`badge badge-${appointment.status.toLowerCase()}`}>
                  {statusLabel[appointment.status]}
                </span>
              </div>
              <div className="appointment-time">
                <Icon name="calendar" />
                <span>{dayLabel(appointment.slot.starts_at)}</span>
                <Icon name="clock" />
                <span>
                  {timeLabel(appointment.slot.starts_at)} – {timeLabel(appointment.slot.ends_at)}
                </span>
              </div>
              <p className="delivery-note">
                <Icon name="mail" size={18} />
                {deliveryLabel[appointment.notification_status] || 'Đang cập nhật trạng thái email'}
              </p>
              {admin && appointment.notification_error && (
                <p className="field-help">Mã lỗi gửi: {appointment.notification_error}</p>
              )}
              {appointment.status === 'BOOKED' &&
                new Date(appointment.slot.starts_at) > new Date() &&
                !admin && (
                  <Toggle
                    id={`reminder-${appointment.id}`}
                    checked={appointment.reminder_enabled}
                    disabled={
                      busy || (!appointment.reminder_enabled && !canRemind(appointment.slot, lead))
                    }
                    busy={pending === `reminder:${appointment.id}`}
                    title="Nhắc lịch qua email"
                    description={reminderDescription(appointment, lead)}
                    error={appointment.reminder_status === 'FAILED_DLQ'}
                    onChange={(enabled) => toggleReminder(appointment, enabled)}
                  />
                )}
              {appointment.status === 'BOOKED' && (
                <div className="appointment-actions">
                  {!admin && new Date(appointment.slot.starts_at) > new Date() && (
                    <Button
                      variant="ghost"
                      busy={pending === `cancel:${appointment.id}`}
                      disabled={busy}
                      onClick={() => cancel(appointment)}
                    >
                      Hủy lịch hẹn
                    </Button>
                  )}
                  {admin && new Date(appointment.slot.ends_at) < new Date() && (
                    <Button
                      variant="secondary"
                      busy={pending === `complete:${appointment.id}`}
                      disabled={busy}
                      onClick={() =>
                        act(`complete:${appointment.id}`, async () => {
                          const result = await request<Appointment>(
                            `/api/admin/appointments/${appointment.id}/complete`,
                            session!.token,
                            { method: 'POST' },
                          );
                          setAppointments((current) =>
                            current.map((item) => (item.id === result.id ? result : item)),
                          );
                          setBanner({
                            kind: 'success',
                            message: 'Đã đánh dấu hoàn tất lịch khám.',
                          });
                        })
                      }
                    >
                      Đánh dấu hoàn tất
                    </Button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
