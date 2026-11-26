import { Icon } from '../components/ui/icons';
import { Notice } from '../components/ui';
import { LoginPage } from '../features/auth/LoginPage';
import { AdminSetup } from '../features/admin/AdminSetup';
import { BookingConfirmation } from '../features/booking/BookingConfirmation';
import { BookingWizard } from '../features/booking/BookingWizard';
import { AppointmentList } from '../features/appointments/AppointmentList';
import { useClinicApp } from './useClinicApp';
export default function App() {
  const controller = useClinicApp();
  const {
    session,
    view,
    setView,
    adminSection,
    setAdminSection,
    banner,
    setBanner,
    confirmed,
    busy,
    liveConfirmation,
    logout,
  } = controller;
  return (
    <div className="site-shell">
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="/" aria-label="An Uyên Hospital, trang chủ">
            <img
              src="/brand/an-uyen-logo-blue.svg"
              alt="Logo An Uyên Hospital"
              width="44"
              height="44"
            />
            <span>
              An Uyên<small>HOSPITAL</small>
            </span>
          </a>
          {session ? (
            <>
              <nav className="main-nav" aria-label="Điều hướng chính">
                {session.role === 'patient' ? (
                  <>
                    <button
                      className={view === 'booking' ? 'active' : ''}
                      aria-current={view === 'booking' ? 'page' : undefined}
                      onClick={() => {
                        setView('booking');
                        setBanner(null);
                      }}
                    >
                      <Icon name="calendar" />
                      Đặt lịch khám
                    </button>
                    <button
                      className={view === 'appointments' ? 'active' : ''}
                      aria-current={view === 'appointments' ? 'page' : undefined}
                      onClick={() => {
                        setView('appointments');
                        setBanner(null);
                      }}
                    >
                      <Icon name="clock" />
                      Lịch hẹn của tôi
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className={adminSection === 'appointments' ? 'active' : ''}
                      onClick={() => {
                        setAdminSection('appointments');
                        setBanner(null);
                      }}
                    >
                      Lịch hẹn
                    </button>
                    <button
                      className={adminSection === 'setup' ? 'active' : ''}
                      onClick={() => {
                        setAdminSection('setup');
                        setBanner(null);
                      }}
                    >
                      Bác sĩ &amp; khung giờ
                    </button>
                  </>
                )}
              </nav>
              <div className="account">
                <span className="account-label">
                  <Icon name="user" />
                  {session.role === 'admin' ? 'Admin' : 'Tài khoản của tôi'}
                </span>
                <button
                  className="logout-button"
                  onClick={logout}
                  disabled={busy}
                  aria-label="Đăng xuất"
                >
                  <Icon name="logout" />
                  <span>Đăng xuất</span>
                </button>
              </div>
            </>
          ) : (
            <span className="header-assurance">
              <Icon name="lock" size={18} />
              Thông tin được bảo vệ
            </span>
          )}
        </div>
      </header>
      <main className="page-container">
        <div className="page-intro">
          <div>
            <h1>
              {!session
                ? 'Đặt lịch khám tại An Uyên, khiến bạn an tâm hơn.'
                : session.role === 'admin'
                  ? 'Quản lý phòng khám'
                  : view === 'appointments'
                    ? 'Lịch hẹn của bạn'
                    : 'Đặt lịch khám'}
            </h1>
            <p>
              {!session
                ? 'Một vài bước đơn giản để chọn lịch khám phù hợp với bạn.'
                : session.role === 'admin'
                  ? 'Sắp xếp lịch khám và theo dõi thông báo tại một nơi.'
                  : view === 'appointments'
                    ? 'Theo dõi lịch khám và chủ động sắp xếp thời gian của bạn.'
                    : 'Chọn bác sĩ, thời gian và xem lại thông tin trước khi xác nhận nhé.'}
            </p>
          </div>
          <span className="timezone">
            <Icon name="clock" size={18} />
            Giờ Việt Nam · UTC+7
          </span>
        </div>
        {banner && (
          <div className="page-banner">
            <Notice kind={banner.kind}>{banner.message}</Notice>
          </div>
        )}
        {!session ? (
          <LoginPage {...controller} />
        ) : session.role === 'admin' ? (
          adminSection === 'appointments' ? (
            <AppointmentList {...controller} admin />
          ) : (
            <AdminSetup {...controller} />
          )
        ) : view === 'appointments' ? (
          <AppointmentList {...controller} />
        ) : confirmed && liveConfirmation ? (
          <BookingConfirmation {...controller} />
        ) : (
          <BookingWizard {...controller} />
        )}
      </main>
      <footer className="site-footer">
        <div>
          <span>An Uyên Hospital</span>
          <span>Đặt lịch khám có thông báo</span>
        </div>
        <p>Phiên bản thử nghiệm · Chỉ sử dụng dữ liệu giả lập.</p>
      </footer>
    </div>
  );
}
