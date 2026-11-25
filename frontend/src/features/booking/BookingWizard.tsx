import { Icon, Spinner } from '../../components/ui/icons';
import { Notice, Button, Toggle } from '../../components/ui';
import { Avatar } from '../../components/ui/Avatar';
import { dateKey, weekday, dayLabel, timeLabel, leadLabel } from '../../lib/types';
import type { ClinicController } from '../../app/useClinicApp';
type Props = Pick<
  ClinicController,
  | 'act'
  | 'book'
  | 'busy'
  | 'chooseDoctor'
  | 'chosen'
  | 'day'
  | 'daySlots'
  | 'days'
  | 'doctorId'
  | 'effectiveReminder'
  | 'lead'
  | 'pending'
  | 'reloadSlots'
  | 'reminderEligible'
  | 'search'
  | 'selectedAvailable'
  | 'selectedDoctor'
  | 'session'
  | 'setBanner'
  | 'setChosen'
  | 'setDay'
  | 'setReminder'
  | 'setSearch'
  | 'setSpecialty'
  | 'setStep'
  | 'slotError'
  | 'slotLoading'
  | 'slots'
  | 'specialties'
  | 'specialty'
  | 'step'
  | 'visibleDoctors'
>;
export function BookingWizard({
  act,
  book,
  busy,
  chooseDoctor,
  chosen,
  day,
  daySlots,
  days,
  doctorId,
  effectiveReminder,
  lead,
  pending,
  reloadSlots,
  reminderEligible,
  search,
  selectedAvailable,
  selectedDoctor,
  session,
  setBanner,
  setChosen,
  setDay,
  setReminder,
  setSearch,
  setSpecialty,
  setStep,
  slotError,
  slotLoading,
  slots,
  specialties,
  specialty,
  step,
  visibleDoctors,
}: Props) {
  if (!session) return null;
  return (
    <div className="booking-layout">
      <section className="card booking-panel">
        <ol className="booking-steps" aria-label="Tiến trình đặt lịch">
          {['Chọn bác sĩ', 'Chọn lịch', 'Xem lại'].map((label, index) => (
            <li
              key={label}
              className={step === index + 1 ? 'current' : step > index + 1 ? 'complete' : ''}
              aria-current={step === index + 1 ? 'step' : undefined}
            >
              <span>{step > index + 1 ? <Icon name="check" size={16} /> : index + 1}</span>
              <button
                disabled={busy || index + 1 > step}
                onClick={() => {
                  setStep(index + 1);
                  setBanner(null);
                }}
              >
                {label}
              </button>
            </li>
          ))}
        </ol>
        <div className="step-content" key={step}>
          {step === 1 ? (
            <>
              <div className="step-heading">
                <h2>Chọn bác sĩ của bạn</h2>
                <p>Tìm bác sĩ hoặc chọn theo chuyên khoa.</p>
              </div>
              <div className="doctor-filters">
                <div className="field">
                  <label htmlFor="doctor-search">Tìm bác sĩ</label>
                  <div className="input-with-icon">
                    <Icon name="search" />
                    <input
                      id="doctor-search"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="Tên bác sĩ hoặc chuyên khoa"
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="specialty-filter">Chuyên khoa</label>
                  <select
                    id="specialty-filter"
                    value={specialty}
                    onChange={(event) => setSpecialty(event.target.value)}
                  >
                    <option value="">Tất cả chuyên khoa</option>
                    {specialties.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="doctor-grid">
                {visibleDoctors.map((doctor) => (
                  <button
                    type="button"
                    key={doctor.id}
                    className={`doctor-card ${doctorId === doctor.id ? 'selected' : ''}`}
                    data-doctor={doctor.id}
                    aria-pressed={doctorId === doctor.id}
                    onClick={() => chooseDoctor(doctor.id)}
                  >
                    <Avatar name={doctor.name} />
                    <span className="doctor-details">
                      <strong>{doctor.name}</strong>
                      <span>{doctor.specialty}</span>
                    </span>
                    <span className="selection-indicator">
                      {doctorId === doctor.id && <Icon name="check" size={14} />}
                    </span>
                  </button>
                ))}
              </div>
              {!visibleDoctors.length && (
                <div className="empty-state compact">
                  <Icon name="search" size={26} />
                  <h3>Chưa tìm thấy bác sĩ phù hợp</h3>
                  <p>Vui lòng thử tên khác hoặc chọn tất cả chuyên khoa.</p>
                </div>
              )}
            </>
          ) : step === 2 ? (
            <>
              <div className="step-heading">
                <h2>Chọn ngày và giờ khám</h2>
                <p>
                  {selectedDoctor?.name} · {selectedDoctor?.specialty}
                </p>
              </div>
              {slotLoading ? (
                <div className="loading-state" role="status">
                  <Spinner />
                  Đang tải khung giờ khám…
                  <div className="skeleton-grid">
                    {Array.from({ length: 8 }, (_, index) => (
                      <span key={index} />
                    ))}
                  </div>
                </div>
              ) : slotError ? (
                <Notice kind="error">
                  {slotError}
                  <Button variant="ghost" onClick={() => act('slots', reloadSlots)}>
                    Tải lại khung giờ
                  </Button>
                </Notice>
              ) : !days.length ? (
                <div className="empty-state">
                  <Icon name="calendar" size={28} />
                  <h3>Chưa có khung giờ khám</h3>
                  <p>Vui lòng chọn bác sĩ khác hoặc quay lại sau.</p>
                  <Button variant="secondary" onClick={() => setStep(1)}>
                    Chọn bác sĩ khác
                  </Button>
                </div>
              ) : (
                <>
                  <div className="date-strip" role="group" aria-label="Ngày khám">
                    {days.map((key) => {
                      const first = slots.find((slot) => dateKey(slot.starts_at) === key)!;
                      return (
                        <button
                          type="button"
                          data-date={key}
                          key={key}
                          aria-pressed={day === key}
                          className={day === key ? 'selected' : ''}
                          onClick={() => {
                            setDay(key);
                            if (chosen && dateKey(chosen.starts_at) !== key) setChosen(null);
                          }}
                        >
                          <span>{weekday(first.starts_at)}</span>
                          <strong>{dayLabel(first.starts_at).slice(0, 5)}</strong>
                        </button>
                      );
                    })}
                  </div>
                  <div className="times-heading">
                    <h3>Khung giờ khám</h3>
                    <span>{daySlots.filter((slot) => slot.available).length} giờ còn trống</span>
                  </div>
                  <div className="slot-grid">
                    {daySlots.map((slot) => (
                      <button
                        type="button"
                        className={`time-slot ${chosen?.id === slot.id && slot.available ? 'selected' : ''} ${!slot.available ? 'unavailable' : ''}`}
                        key={slot.id}
                        data-slot={slot.id}
                        data-available={slot.available}
                        aria-pressed={chosen?.id === slot.id && slot.available}
                        disabled={!slot.available || busy}
                        aria-label={`${timeLabel(slot.starts_at)}, ${slot.available ? 'còn trống' : 'đã hết chỗ'}`}
                        onClick={() => setChosen(slot)}
                      >
                        <strong>{timeLabel(slot.starts_at)}</strong>
                        <span>
                          {!slot.available ? (
                            'Đã hết chỗ'
                          ) : chosen?.id === slot.id ? (
                            <>
                              <Icon name="check" size={13} />
                              Đã chọn
                            </>
                          ) : (
                            'Còn trống'
                          )}
                        </span>
                      </button>
                    ))}
                  </div>
                  <div className="slot-legend">
                    <span>
                      <i className="legend-available" />
                      Còn trống
                    </span>
                    <span>
                      <i className="legend-selected" />
                      Đã chọn
                    </span>
                    <span>
                      <i className="legend-unavailable" />
                      Đã hết chỗ
                    </span>
                  </div>
                </>
              )}
            </>
          ) : (
            <>
              <div className="step-heading">
                <h2>Xem lại lịch hẹn</h2>
                <p>Vui lòng kiểm tra thông tin trước khi xác nhận.</p>
              </div>
              <dl className="review-details">
                <div>
                  <dt>
                    <Icon name="user" />
                    Bác sĩ
                  </dt>
                  <dd>
                    <strong>{selectedDoctor?.name}</strong>
                    <span>{selectedDoctor?.specialty}</span>
                  </dd>
                </div>
                <div>
                  <dt>
                    <Icon name="calendar" />
                    Ngày khám
                  </dt>
                  <dd>{chosen && dayLabel(chosen.starts_at)}</dd>
                </div>
                <div>
                  <dt>
                    <Icon name="clock" />
                    Giờ khám
                  </dt>
                  <dd>
                    {chosen && `${timeLabel(chosen.starts_at)} – ${timeLabel(chosen.ends_at)}`}
                  </dd>
                </div>
                <div>
                  <dt>
                    <Icon name="mail" />
                    Email nhận thông báo
                  </dt>
                  <dd className="break-word">{session.email}</dd>
                </div>
              </dl>
              <Button variant="ghost" disabled={busy} onClick={() => setStep(2)}>
                <Icon name="back" size={17} />
                Sửa lịch hẹn
              </Button>
              <div className="notification-settings">
                <h3>
                  <Icon name="bell" />
                  Thông báo lịch khám
                </h3>
                <div className="confirmation-option">
                  <span>Email xác nhận lịch hẹn</span>
                  <span className="subtle-badge">Luôn bật</span>
                </div>
                <Toggle
                  id="booking-reminder"
                  checked={effectiveReminder}
                  disabled={busy || !reminderEligible}
                  onChange={setReminder}
                  title="Nhắc lịch qua email"
                  description={
                    reminderEligible
                      ? `Gửi một email nhắc trước giờ khám ${leadLabel(lead)}. Bạn có thể thay đổi trong Lịch hẹn của tôi.`
                      : `Khung giờ này còn dưới ${leadLabel(lead)}. Bạn vẫn nhận được email xác nhận.`
                  }
                />
              </div>
              {!selectedAvailable && (
                <Notice kind="error">
                  Khung giờ này vừa hết chỗ. Các thông tin khác vẫn được giữ; vui lòng chọn lại giờ
                  khám.
                </Notice>
              )}
            </>
          )}
        </div>
        <div className="wizard-actions">
          {step > 1 ? (
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => {
                setStep(step - 1);
                setBanner(null);
              }}
            >
              <Icon name="back" size={17} />
              Quay lại
            </Button>
          ) : (
            <span className="step-hint">Bạn có thể đổi lựa chọn ở bước tiếp theo.</span>
          )}
          {step < 3 ? (
            <Button
              disabled={step === 1 ? !doctorId : !chosen || !selectedAvailable || slotLoading}
              onClick={() => {
                setStep(step + 1);
                setBanner(null);
              }}
            >
              {step === 1 ? 'Tiếp tục' : 'Xem lại lịch hẹn'}
              <Icon name="next" size={18} />
            </Button>
          ) : (
            <Button busy={pending === 'book'} disabled={busy || !selectedAvailable} onClick={book}>
              {pending === 'book' ? 'Đang đặt lịch…' : 'Xác nhận đặt lịch'}
              {!busy && <Icon name="check" size={18} />}
            </Button>
          )}
        </div>
      </section>
      <aside className="booking-aside">
        <section className="card summary-card">
          <h2>
            <Icon name="calendar" />
            Lịch hẹn của bạn
          </h2>
          <div className="summary-section">
            <span>Bác sĩ</span>
            <strong>{selectedDoctor?.name || 'Chưa chọn bác sĩ'}</strong>
            {selectedDoctor && <p>{selectedDoctor.specialty}</p>}
          </div>
          <div className="summary-section">
            <span>Thời gian khám</span>
            <strong>{chosen ? dayLabel(chosen.starts_at) : 'Chưa chọn khung giờ'}</strong>
            {chosen && (
              <p>
                {timeLabel(chosen.starts_at)} – {timeLabel(chosen.ends_at)}
              </p>
            )}
          </div>
          <div className="summary-note">
            <Icon name="mail" size={18} />
            <p>Email xác nhận sẽ được gửi sau khi đặt lịch thành công.</p>
          </div>
          {chosen && (
            <div className="summary-reminder">
              <Icon name="bell" size={17} />
              {effectiveReminder ? `Nhắc trước ${leadLabel(lead)}` : 'Không bật nhắc lịch'}
            </div>
          )}
        </section>
        <section className="booking-help">
          <h3>
            <Icon name="info" size={18} />
            Một vài lưu ý nhỏ
          </h3>
          <p>Bạn có thể hủy lịch trước giờ khám trong mục Lịch hẹn của tôi.</p>
          <p>Tất cả thời gian hiển thị theo giờ Việt Nam.</p>
        </section>
      </aside>
    </div>
  );
}
