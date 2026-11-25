import { Icon } from '../../components/ui/icons';
import { fullTime, leadLabel } from '../../lib/types';
import { Notice, Button } from '../../components/ui';
import { deliveryLabel } from '../appointments/labels';
import type { ClinicController } from '../../app/useClinicApp';
type Props = Pick<
  ClinicController,
  'lead' | 'liveConfirmation' | 'newBooking' | 'setBanner' | 'setView'
>;
export function BookingConfirmation({
  lead,
  liveConfirmation,
  newBooking,
  setBanner,
  setView,
}: Props) {
  if (!liveConfirmation) return null;
  return (
    <section className="card success-card">
      <span className="success-icon">
        <Icon name="check" size={32} />
      </span>
      <h2>Đặt lịch thành công</h2>
      <p>Cảm ơn bạn đã lựa chọn An Uyên Hospital.</p>
      <div className="success-summary">
        <h3>{liveConfirmation.doctor}</h3>
        <p>
          <Icon name="calendar" />
          {fullTime(liveConfirmation.slot)}
        </p>
        <p>
          Mã lịch hẹn <strong>{liveConfirmation.id.slice(0, 8).toUpperCase()}</strong>
        </p>
      </div>
      <Notice kind={liveConfirmation.notification_status === 'FAILED_DLQ' ? 'error' : 'success'}>
        {deliveryLabel[liveConfirmation.notification_status] || 'Đang cập nhật trạng thái email'}
      </Notice>
      {liveConfirmation.reminder_enabled && (
        <p className="confirmation-reminder">
          <Icon name="bell" size={18} />
          Đã bật nhắc trước giờ khám {leadLabel(lead)}.
        </p>
      )}
      <div className="success-actions">
        <Button
          onClick={() => {
            setView('appointments');
            setBanner(null);
          }}
        >
          Xem lịch hẹn
          <Icon name="next" />
        </Button>
        <Button variant="secondary" onClick={newBooking}>
          Đặt lịch mới
        </Button>
      </div>
    </section>
  );
}
