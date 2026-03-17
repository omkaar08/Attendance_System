import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import style from './HomePage.module.css';

export function HomePage() {
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => {};
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleGetStarted = () => {
    navigate('/login');
  };

  return (
    <div className={style.homepage}>
      {/* Navigation Header */}
      <header className={style.header}>
        <div className={style.container}>
          <div className={style.navbar}>
            <div className={style.logo}>
              <img src="/visionattend-logo.svg" alt="VisionAttend" className={style.logoImg} />
              <span className={style.brandName}>VISIONATTEND</span>
            </div>
            <nav className={style.nav}>
              <a href="#features">Features</a>
              <a href="#benefits">Benefits</a>
              <a href="#roles">Roles</a>
              <button className="btn btn-primary" onClick={handleGetStarted}>
                Login
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className={style.hero}>
        <div className={style.container}>
          <div className={style.heroContent}>
            <div className={style.heroText}>
              <h1 className={`${style.heroTitle} animate-fade-in-up`}>
                AI-Powered Face Recognition
                <span className={style.highlight}> Attendance System</span>
              </h1>
              <p className={`${style.heroSubtitle} animate-fade-in-up`}>
                Transform your attendance management with cutting-edge facial recognition. Secure, accurate, and effortless.
              </p>
              <div className={`${style.heroCTA} animate-fade-in-up`}>
                <button className="btn btn-primary btn-lg" onClick={handleGetStarted}>
                  Get Started Free
                </button>
                <button className="btn btn-outline btn-lg">
                  Watch Demo
                </button>
              </div>
            </div>
            <div className={style.heroImage}>
              <div className={`${style.floatingCard} ${style.card1}`}>
                <div className={style.cardIcon}>👤</div>
                <span>Face Recognition</span>
              </div>
              <div className={`${style.floatingCard} ${style.card2}`}>
                <div className={style.cardIcon}>✓</div>
                <span>99% Accuracy</span>
              </div>
              <div className={`${style.floatingCard} ${style.card3}`}>
                <div className={style.cardIcon}>⚡</div>
                <span>Instant Results</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className={style.features}>
        <div className={style.container}>
          <h2 className={style.sectionTitle}>Powerful Features</h2>
          <div className={style.featureGrid}>
            <div className="card animate-fade-in-up">
              <div className={style.featureIcon}>🎯</div>
              <h3>Face Recognition</h3>
              <p>Advanced ONNX-based face detection and recognition with 90%+ accuracy across various lighting conditions.</p>
            </div>
            <div className="card animate-fade-in-up">
              <div className={style.featureIcon}>📊</div>
              <h3>Real-time Analytics</h3>
              <p>Live attendance tracking and meaningful analytics with professional visualizations for instant insights.</p>
            </div>
            <div className="card animate-fade-in-up">
              <div className={style.featureIcon}>👥</div>
              <h3>Role-based Access</h3>
              <p>Faculty, HOD, and Admin roles with granular permissions and department-scoped access control.</p>
            </div>
            <div className="card animate-fade-in-up">
              <div className={style.featureIcon}>📱</div>
              <h3>Manual Attendance</h3>
              <p>Faculty can manually mark attendance for students who missed the face detection process.</p>
            </div>
            <div className="card animate-fade-in-up">
              <div className={style.featureIcon}>📥</div>
              <h3>Bulk Operations</h3>
              <p>Import and export students via CSV. Perfect for semester onboarding and data management.</p>
            </div>
            <div className="card animate-fade-in-up">
              <div className={style.featureIcon}>🔒</div>
              <h3>Enterprise Security</h3>
              <p>JWT authentication, row-level security, audit logging, and encrypted data storage.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section id="benefits" className={style.benefits}>
        <div className={style.container}>
          <h2 className={style.sectionTitle}>Why Choose VisionAttend?</h2>
          <div className={style.benefitGrid}>
            <div className={style.benefitItem}>
              <div className={style.benefitNumber}>90%+</div>
              <h4>Accuracy</h4>
              <p>Industry-leading face recognition accuracy with anti-spoofing detection</p>
            </div>
            <div className={style.benefitItem}>
              <div className={style.benefitNumber}>100%</div>
              <h4>Uptime</h4>
              <p>Cloud-based infrastructure with automatic scaling and backups</p>
            </div>
            <div className={style.benefitItem}>
              <div className={style.benefitNumber}>3</div>
              <h4>User Roles</h4>
              <p>Faculty, HOD, and Admin with specialized dashboards and permissions</p>
            </div>
            <div className={style.benefitItem}>
              <div className={style.benefitNumber}>24/7</div>
              <h4>Support</h4>
              <p>Professional support team ready to help anytime</p>
            </div>
          </div>
        </div>
      </section>

      {/* Roles Section */}
      <section id="roles" className={style.roles}>
        <div className={style.container}>
          <h2 className={style.sectionTitle}>Tailored for Every Role</h2>
          <div className={style.roleGrid}>
            <div className="card">
              <h3 className={style.roleTitle}>🎓 Faculty</h3>
              <ul className={style.roleFeatures}>
                <li>Mark attendance via face recognition</li>
                <li>Manual attendance marking</li>
                <li>View attendance reports (subject-scoped)</li>
                <li>Real-time analytics</li>
                <li>Student management</li>
                <li>Download reports</li>
              </ul>
            </div>
            <div className="card">
              <h3 className={style.roleTitle}>👔 Head of Department (HOD)</h3>
              <ul className={style.roleFeatures}>
                <li>All Faculty features</li>
                <li>Create & manage subjects</li>
                <li>Manage faculty assignments</li>
                <li>Department-level analytics</li>
                <li>Bulk import students</li>
                <li>Department reports</li>
              </ul>
            </div>
            <div className="card">
              <h3 className={style.roleTitle}>👨‍💼 Administrator</h3>
              <ul className={style.roleFeatures}>
                <li>Full system access</li>
                <li>Manage departments</li>
                <li>Create HODs & Faculty</li>
                <li>View audit logs</li>
                <li>System-wide analytics</li>
                <li>System maintenance</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className={style.stats}>
        <div className={style.container}>
          <div className={style.statGrid}>
            <div className={style.statItem}>
              <h3>10,000+</h3>
              <p>Students Tracked</p>
            </div>
            <div className={style.statItem}>
              <h3>500+</h3>
              <p>Faculty Members</p>
            </div>
            <div className={style.statItem}>
              <h3>50+</h3>
              <p>Departments</p>
            </div>
            <div className={style.statItem}>
              <h3>99%</h3>
              <p>System Uptime</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className={style.cta}>
        <div className={style.container}>
          <div className={style.ctaContent}>
            <h2>Ready to Transform Your Attendance?</h2>
            <p>Join hundreds of institutions using VisionAttend for smarter attendance management</p>
            <button className="btn btn-primary btn-lg" onClick={handleGetStarted}>
              Login Now
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className={style.footer}>
        <div className={style.container}>
          <div className={style.footerContent}>
            <div className={style.footerBrand}>
              <img src="/visionattend-logo.svg" alt="VisionAttend" className={style.logoImg} />
              <p>VisionAttend - AI-Powered Attendance Management</p>
            </div>
            <div className={style.footerLinks}>
              <a href="#features">Features</a>
              <a href="#benefits">Benefits</a>
              <a href="#roles">Roles</a>
              <a href="#privacy">Privacy</a>
              <a href="#terms">Terms</a>
            </div>
          </div>
          <div className={style.footerBottom}>
            <p>&copy; 2026 VisionAttend. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
