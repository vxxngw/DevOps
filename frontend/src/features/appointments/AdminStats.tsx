import { Icon } from '../../components/ui/icons';
import { Appointment, dateKey } from '../../lib/types';
export function AdminStats({ appointments }: { appointments: Appointment[] }) {
  const today = dateKey(new Date().toISOString());
  const stats = [
    {
      icon: 'calendar',
      label: 'Lịch khám hôm nay',
      value: appointments.filter(
        (item) => item.status !== 'CANCELLED' && dateKey(item.slot.starts_at) === today,
      ).length,
    },
    {
      icon: 'clock',
      label: 'Đang chờ khám',
      value: appointments.filter((item) => item.status === 'BOOKED').length,
    },
    {
      icon: 'mail',
      label: 'Email đang xử lý',
      value: appointments.filter((item) =>
        ['PENDING', 'PROCESSING', 'RETRY_PENDING'].includes(item.notification_status),
      ).length,
    },
    {
      icon: 'info',
      label: 'Email gửi lỗi',
      value: appointments.filter((item) => item.notification_status === 'FAILED_DLQ').length,
    },
  ];
  return (
    <dl className="stat-grid">
      {stats.map((stat) => (
        <div key={stat.label}>
          <dt>
            <Icon name={stat.icon} size={18} />
            {stat.label}
          </dt>
          <dd>{stat.value}</dd>
        </div>
      ))}
    </dl>
  );
}
