import { Icon } from '../../components/ui/icons';
import { Button } from '../../components/ui';
import { leadLabel } from '../../lib/types';
import type { ClinicController } from '../../app/useClinicApp';
type Props = Pick<
  ClinicController,
  'busy' | 'email' | 'lead' | 'login' | 'password' | 'pending' | 'setEmail' | 'setPassword'
>;
export function LoginPage({
  busy,
  email,
  lead,
  login,
  password,
  pending,
  setEmail,
  setPassword,
}: Props) {
  return (
    <div className="login-layout">
      <section className="card login-card">
        <div className="card-icon">
          <Icon name="user" size={24} />
        </div>
        <h2>Đăng nhập để đặt lịch</h2>
        <p>Vui lòng sử dụng tài khoản đã được cung cấp.</p>
        <form onSubmit={login}>
          <div className="field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              disabled={busy}
              placeholder="Nhập địa chỉ email"
            />
          </div>
          <div className="field">
            <label htmlFor="login-password">Mật khẩu</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              disabled={busy}
              placeholder="Nhập mật khẩu"
            />
          </div>
          <Button type="submit" busy={pending === 'login'}>
            {pending === 'login' ? 'Đang đăng nhập…' : 'Đăng nhập'}
            {!busy && <Icon name="next" />}
          </Button>
        </form>
        <p className="login-help">
          <Icon name="lock" size={16} />
          Thông tin đăng nhập chỉ dùng để truy cập lịch hẹn của bạn.
        </p>
      </section>
      <aside className="login-guide">
        <h2>
          Lịch khám phù hợp,
          <br />
          chủ động mỗi ngày.
        </h2>
        <p>Đặt lịch và nhận thông báo để không bỏ lỡ cuộc hẹn.</p>
        <ol>
          {[
            ['user', 'Chọn bác sĩ', 'Tìm bác sĩ và chuyên khoa phù hợp.'],
            ['calendar', 'Chọn thời gian', 'Xem các khung giờ còn trống.'],
            [
              'bell',
              'Nhận thông báo',
              `Nhận email xác nhận và tùy chọn nhắc trước ${leadLabel(lead)}.`,
            ],
          ].map(([icon, title, text], index) => (
            <li key={title}>
              <span className="guide-icon">
                <Icon name={icon} />
              </span>
              <div>
                <span className="guide-number">0{index + 1}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="gentle-note">
          <Icon name="heart" />
          Dành thời gian cho sức khỏe của bạn.
        </div>
      </aside>
    </div>
  );
}
