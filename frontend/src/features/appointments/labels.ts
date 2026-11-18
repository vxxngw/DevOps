import { Appointment, canRemind, leadLabel } from '../../lib/types';
export const statusLabel: Record<string, string> = {
  BOOKED: 'Sắp tới',
  CANCELLED: 'Đã hủy',
  COMPLETED: 'Hoàn tất',
};
export const deliveryLabel: Record<string, string> = {
  PENDING: 'Đang chờ gửi email xác nhận',
  PROCESSING: 'Đang gửi email xác nhận',
  RETRY_PENDING: 'Email đang được gửi lại',
  SENT: 'Đã gửi email xác nhận',
  FAILED_DLQ: 'Email chưa gửi được. Lịch hẹn vẫn được lưu.',
  SKIPPED: 'Thông báo cũ đã được bỏ qua',
};
export const reminderDeliveryLabel: Record<string, string> = {
  PENDING: 'Đang chờ gửi email nhắc lịch.',
  PROCESSING: 'Đang gửi email nhắc lịch.',
  RETRY_PENDING: 'Đang thử gửi lại email nhắc lịch.',
  SENT: 'Email nhắc lịch đã được gửi.',
  FAILED_DLQ:
    'Email nhắc lịch chưa gửi được. Lịch hẹn vẫn được lưu; vui lòng xem thời gian khám ở trên.',
  SKIPPED: 'Email nhắc lịch đã được bỏ qua. Vui lòng xem thời gian khám ở trên.',
  CANCELLED: 'Đã dừng email nhắc lịch cho lịch hẹn này.',
};
export function reminderDescription(appointment: Appointment, lead: number) {
  if (reminderDeliveryLabel[appointment.reminder_status])
    return reminderDeliveryLabel[appointment.reminder_status];
  if (appointment.reminder_enabled)
    return canRemind(appointment.slot, lead)
      ? `Nhắc trước giờ khám ${leadLabel(lead)}.`
      : 'Đã lên lịch nhắc. Trạng thái gửi sẽ được cập nhật tại đây.';
  return canRemind(appointment.slot, lead)
    ? 'Đã tắt nhắc lịch. Bạn vẫn nhận được email xác nhận.'
    : 'Đã qua thời gian bật nhắc. Bạn vẫn có thể xem email xác nhận.';
}
