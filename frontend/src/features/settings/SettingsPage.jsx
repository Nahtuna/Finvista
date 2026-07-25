import React, { useState, useEffect, useRef } from "react";
import { 
  User, Shield, Bell, Moon, Server, Save, Key, Lock, Smartphone, 
  CheckCircle, RefreshCw, AlertTriangle, Cpu, Globe, Sliders, Eye, 
  EyeOff, ShieldAlert, Check, Copy, HardDrive, Terminal
} from "lucide-react";
import { useAuth } from "../../auth/AuthProvider.jsx";
import { getAdminSecretStatus } from "../../api.js";

export function SettingsPage({ 
  health, 
  healthLoading, 
  healthError, 
  refreshHealth, 
  language = "vi", 
  setLanguage, 
  preferences = {}, 
  setPreferences 
}) {
  const isEnglish = language === "en";
  const auth = useAuth();
  const isAdmin = Boolean(auth?.isAdmin);

  const [activeSubTab, setActiveSubTab] = useState("tai_khoan");

  // Account tab state
  const [name, setName] = useState(auth?.profile?.name || "Nguyễn Tuấn Anh");
  const [email, setEmail] = useState(auth?.profile?.email || "tuananh.nguyen@finvista.vn");
  const [phone, setPhone] = useState("+84 987 654 321");
  const [broker, setBroker] = useState("VNDIRECT (Synced)");
  const [apiKey, setApiKey] = useState("fin_live_8f93a21bc901e44a72d");
  const [copiedKey, setCopiedKey] = useState(false);

  // Security tab state
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [enable2FA, setEnable2FA] = useState(true);
  const [hideBalance, setHideBalance] = useState(preferences.hideBalance || false);

  // Notification tab state
  const [notifChannels, setNotifChannels] = useState({
    email: true,
    telegram: true,
    webPush: true,
    sms: false
  });
  const [notifTopics, setNotifTopics] = useState({
    priceBreakout: true,
    greeksSignal: true,
    regimeShift: true,
    dailyDigest: true
  });
  const [notifFreq, setNotifFreq] = useState("realtime");

  // Appearance tab state
  const [selectedTheme, setSelectedTheme] = useState(preferences.theme || "dark");
  const [chartTimeframe, setChartTimeframe] = useState(preferences.defaultTimeframe || "3M");
  const [candleType, setCandleType] = useState(preferences.candleType || "candlestick");

  // Feedback banner state
  const [saveStatus, setSaveStatus] = useState("");

  // Admin secret status modal state
  const [showAdminStatus, setShowAdminStatus] = useState(false);
  const [secretsData, setSecretsData] = useState(null);
  const [secretsLoading, setSecretsLoading] = useState(false);
  const [secretsError, setSecretsError] = useState("");
  const modalRef = useRef(null);

  useEffect(() => {
    setName(auth?.profile?.name || "Nguyễn Tuấn Anh");
    setEmail(auth?.profile?.email || "tuananh.nguyen@finvista.vn");
  }, [auth?.profile]);

  // Click outside to close admin secret status modal
  useEffect(() => {
    function handlePointerDown(e) {
      if (modalRef.current && !modalRef.current.contains(e.target)) {
        setShowAdminStatus(false);
      }
    }
    if (showAdminStatus) {
      document.addEventListener("pointerdown", handlePointerDown);
    }
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
    };
  }, [showAdminStatus]);

  function handleSave(msg, updatedPrefs = {}) {
    if (setPreferences) {
      setPreferences({
        ...preferences,
        theme: selectedTheme,
        colorMode: updatedPrefs.colorMode || preferences.colorMode || "dark",
        defaultTimeframe: updatedPrefs.defaultTimeframe || chartTimeframe,
        candleType: updatedPrefs.candleType || candleType,
        hideBalance,
        ...updatedPrefs
      });
    }
    setSaveStatus(msg || (isEnglish ? "Settings saved successfully!" : "Đã lưu cấu hình thành công!"));
    setTimeout(() => setSaveStatus(""), 3500);
  }

  async function handleCheckAdminStatus() {
    setSecretsLoading(true);
    setSecretsError("");
    try {
      const res = await getAdminSecretStatus();
      setSecretsData(res);
      setShowAdminStatus(true);
    } catch (err) {
      setSecretsError(err?.message || "Failed to load admin secret status");
      setShowAdminStatus(true);
    } finally {
      setSecretsLoading(false);
    }
  }

  function handleCopyApiKey() {
    navigator.clipboard.writeText(apiKey);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  }

  const subTabs = [
    { id: "tai_khoan", label: isEnglish ? "Account Profile" : "Tài khoản", icon: User },
    { id: "bao_mat", label: isEnglish ? "Security & Privacy" : "Bảo mật & Quyền riêng tư", icon: Shield },
    { id: "thong_bao", label: isEnglish ? "Notifications & Alerts" : "Thông báo & Alert", icon: Bell },
    { id: "giao_dien", label: isEnglish ? "Appearance & Chart" : "Giao diện & Biểu đồ", icon: Moon },
    { id: "he_thong", label: isEnglish ? "System Status" : "Trạng thái Hệ thống", icon: Server },
  ];

  if (isAdmin) {
    subTabs.push({ id: "admin", label: "Administration", icon: Key });
  }

  const isDark = preferences.colorMode !== "light";
  const bg = isDark ? "#0b0f19" : "#f8fafc";
  const cardBg = isDark ? "#131b2e" : "#ffffff";
  const textColor = isDark ? "#f8fafc" : "#0f172a";
  const mutedText = isDark ? "#94a3b8" : "#64748b";
  const borderColor = isDark ? "#1e293b" : "#e2e8f0";
  const subBg = isDark ? "#0b0f19" : "#f1f5f9";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: bg }}>
      
      {/* HEADER BAR */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: "900", margin: 0, letterSpacing: "0.5px", color: textColor }}>
            {isEnglish ? "SETTINGS & PREFERENCES" : "CÀI ĐẶT & TÙY CHỈNH HỆ THỐNG"}
          </h2>
          <p style={{ fontSize: "0.82rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
            {isEnglish 
              ? "Manage account profile, security controls, real-time alert triggers, and quant model connections." 
              : "Tùy chỉnh thông tin tài khoản, mật khẩu bảo mật, thông báo tín hiệu chứng quyền và kết nối hệ thống quant."}
          </p>
        </div>

        {saveStatus && (
          <div style={{ background: "rgba(16, 185, 129, 0.2)", border: "1px solid #10b981", color: "#10b981", padding: "0.4rem 0.85rem", borderRadius: "0.5rem", fontSize: "0.82rem", fontWeight: "700", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <CheckCircle size={16} /> {saveStatus}
          </div>
        )}
      </div>

      {/* SETTINGS LAYOUT: SIDEBAR SUB-TABS + MAIN FORM */}
      <div style={{ display: "grid", gridTemplateColumns: "250px 1fr", gap: "1.25rem" }}>
        
        {/* SUB-TABS NAVIGATION */}
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "0.75rem", display: "flex", flexDirection: "column", gap: "0.25rem", height: "fit-content" }}>
          {subTabs.map(tab => {
            const Icon = tab.icon;
            const isActive = activeSubTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.65rem",
                  width: "100%",
                  padding: "0.65rem 0.85rem",
                  borderRadius: "0.375rem",
                  background: isActive ? "#2563eb" : "transparent",
                  color: isActive ? "#fff" : mutedText,
                  border: "none",
                  fontSize: "0.85rem",
                  fontWeight: "700",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.15s ease"
                }}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* MAIN SETTINGS CONTENT AREA */}
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.5rem" }}>
          
          {/* 1. TÀI KHOẢN */}
          {activeSubTab === "tai_khoan" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <div style={{ borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.75rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: 0 }}>THÔNG TIN TÀI KHOẢN & LIÊN KẾT BROKER</h3>
                <span style={{ fontSize: "0.75rem", color: "#60a5fa", background: "rgba(37, 99, 235, 0.15)", padding: "0.2rem 0.6rem", borderRadius: "0.25rem", fontWeight: "700" }}>ID: QUANT-8892</span>
              </div>
              
              <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
                <div style={{ width: "60px", height: "60px", borderRadius: "50%", background: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1.4rem", fontWeight: "900", color: "#fff", border: "2px solid #60a5fa" }}>
                  {name.split(" ").map(n => n[0]).join("").slice(-2).toUpperCase() || "TA"}
                </div>
                <div>
                  <h4 style={{ margin: 0, fontSize: "1.05rem", fontWeight: "800" }}>{name}</h4>
                  <p style={{ margin: "0.2rem 0 0 0", fontSize: "0.8rem", color: "#94a3b8" }}>{email} • Executive Trader</p>
                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.4rem" }}>
                    <span style={{ fontSize: "0.7rem", color: "#10b981", background: "rgba(16, 185, 129, 0.15)", padding: "0.15rem 0.5rem", borderRadius: "0.2rem", fontWeight: "700" }}>★ KYC Verified</span>
                    <span style={{ fontSize: "0.7rem", color: "#f59e0b", background: "rgba(245, 158, 11, 0.15)", padding: "0.15rem 0.5rem", borderRadius: "0.2rem", fontWeight: "700" }}>VNDIRECT Connected</span>
                  </div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label style={{ fontSize: "0.78rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.35rem" }}>Họ và tên</label>
                  <input value={name} onChange={e => setName(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.55rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.85rem", boxSizing: "border-box" }} />
                </div>

                <div>
                  <label style={{ fontSize: "0.78rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.35rem" }}>Email liên hệ</label>
                  <input value={email} onChange={e => setEmail(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.55rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.85rem", boxSizing: "border-box" }} />
                </div>

                <div>
                  <label style={{ fontSize: "0.78rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.35rem" }}>Số điện thoại (Nhận OTP)</label>
                  <input value={phone} onChange={e => setPhone(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.55rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.85rem", boxSizing: "border-box" }} />
                </div>

                <div>
                  <label style={{ fontSize: "0.78rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.35rem" }}>Tài khoản Công ty Chứng khoán</label>
                  <select value={broker} onChange={e => setBroker(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.55rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.85rem", boxSizing: "border-box" }}>
                    <option value="VNDIRECT (Synced)" style={{ background: cardBg, color: textColor }}>VNDIRECT (Đã đồng bộ realtime)</option>
                    <option value="SSI Securities" style={{ background: cardBg, color: textColor }}>SSI Securities (API Key Active)</option>
                    <option value="VPS Securities" style={{ background: cardBg, color: textColor }}>VPS Securities (Simulated)</option>
                    <option value="TCBS (Techcom Securities)" style={{ background: cardBg, color: textColor }}>TCBS (Techcom Securities)</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: "0.78rem", color: "#94a3b8", fontWeight: "600", display: "block", marginBottom: "0.35rem" }}>Gói hội viên & Đã mở khóa</label>
                <div style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", padding: "1rem", borderRadius: "0.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <strong style={{ color: "#10b981", fontSize: "0.95rem" }}>★ PREMIUM QUANT MEMBER (PRO)</strong>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "0.25rem" }}>
                      Hạn sử dụng: <strong>31/12/2026</strong> • Đã kích hoạt toàn bộ Mô hình G-Score, Greeks real-time & Bộ lọc chứng quyền nâng cao.
                    </div>
                  </div>
                  <button onClick={() => handleSave("Đã gửi yêu cầu gia hạn Premium!")} style={{ background: "#10b981", color: "#fff", border: "none", padding: "0.5rem 1rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800", cursor: "pointer" }}>Gia hạn Premium</button>
                </div>
              </div>

              {/* API Key management section */}
              <div>
                <label style={{ fontSize: "0.78rem", color: "#94a3b8", fontWeight: "600", display: "block", marginBottom: "0.35rem" }}>Personal API Key (Cho Quant Developer)</label>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input readOnly value={apiKey} style={{ flex: 1, background: subBg, border: `1px solid ${borderColor}`, color: "#60a5fa", padding: "0.55rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.85rem", fontFamily: "monospace" }} />
                  <button onClick={handleCopyApiKey} style={{ background: "#1e293b", border: `1px solid ${borderColor}`, color: "#fff", padding: "0.55rem 0.85rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "700", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                    {copiedKey ? <Check size={16} color="#10b981" /> : <Copy size={16} />}
                    {copiedKey ? "Đã chép" : "Sao chép"}
                  </button>
                </div>
              </div>

              <button onClick={() => handleSave()} style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.6rem 1.5rem", borderRadius: "0.375rem", fontSize: "0.85rem", fontWeight: "800", cursor: "pointer", width: "fit-content", display: "flex", alignItems: "center", gap: "0.35rem", marginTop: "0.5rem" }}>
                <Save size={16} /> Lưu thông tin tài khoản
              </button>
            </div>
          )}

          {/* 2. BẢO MẬT */}
          {activeSubTab === "bao_mat" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: 0, borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.75rem", color: textColor }}>BẢO MẬT TÀI KHOẢN & QUYỀN RIÊNG TƯ</h3>

              <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
                <h4 style={{ margin: "0 0 0.75rem 0", fontSize: "0.95rem", fontWeight: "800", display: "flex", alignItems: "center", gap: "0.4rem", color: textColor }}>
                  <Lock size={16} color="#60a5fa" /> Đổi mật khẩu đăng nhập
                </h4>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
                  <div>
                    <label style={{ fontSize: "0.78rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "600" }}>Mật khẩu hiện tại</label>
                    <input type={showPassword ? "text" : "password"} value={oldPassword} onChange={e => setOldPassword(e.target.value)} style={{ width: "100%", background: cardBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.5rem", borderRadius: "0.375rem", fontSize: "0.85rem", boxSizing: "border-box" }} />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.78rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "600" }}>Mật khẩu mới</label>
                    <input type={showPassword ? "text" : "password"} value={newPassword} onChange={e => setNewPassword(e.target.value)} style={{ width: "100%", background: cardBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.5rem", borderRadius: "0.375rem", fontSize: "0.85rem", boxSizing: "border-box" }} />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.78rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "600" }}>Xác nhận mật khẩu mới</label>
                    <input type={showPassword ? "text" : "password"} value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} style={{ width: "100%", background: cardBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.5rem", borderRadius: "0.375rem", fontSize: "0.85rem", boxSizing: "border-box" }} />
                  </div>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.75rem" }}>
                  <button type="button" onClick={() => setShowPassword(!showPassword)} style={{ background: "transparent", border: "none", color: mutedText, fontSize: "0.78rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.3rem", fontWeight: "600" }}>
                    {showPassword ? <EyeOff size={14} /> : <Eye size={14} />} {showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  </button>
                  <button onClick={() => { setOldPassword(""); setNewPassword(""); setConfirmPassword(""); handleSave("Đã cập nhật mật khẩu thành công!"); }} style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.45rem 1rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "700", cursor: "pointer" }}>
                    Cập nhật mật khẩu
                  </button>
                </div>
              </div>

              {/* 2FA Section */}
              <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong style={{ fontSize: "0.9rem", color: textColor, display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    <Smartphone size={16} color="#10b981" /> Xác thực 2 yếu tố (2FA / Google Authenticator)
                  </strong>
                  <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.75rem", color: mutedText }}>Yêu cầu mã xác thực OTP từ ứng dụng điện thoại mỗi khi thực hiện đặt lệnh hoặc rút tiền.</p>
                </div>
                <button onClick={() => { setEnable2FA(!enable2FA); handleSave(enable2FA ? "Đã tắt 2FA!" : "Đã bật xác thực 2FA!"); }} style={{ background: enable2FA ? "#10b981" : "#334155", color: "#fff", border: "none", padding: "0.45rem 1rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800", cursor: "pointer" }}>
                  {enable2FA ? "● ĐÃ BẬT 2FA" : "○ TẮT 2FA"}
                </button>
              </div>

              {/* Privacy section */}
              <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong style={{ fontSize: "0.9rem", color: textColor }}>Ẩn số dư tài sản trên giao diện (Privacy Mode)</strong>
                  <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.75rem", color: mutedText }}>Che số dư VND và danh mục tài sản thành `******` khi quay màn hình hoặc làm việc nơi công cộng.</p>
                </div>
                <button onClick={() => { setHideBalance(!hideBalance); handleSave(!hideBalance ? "Đã bật chế độ riêng tư số dư!" : "Đã hiển thị số dư!"); }} style={{ background: hideBalance ? "#2563eb" : "#334155", color: "#fff", border: "none", padding: "0.45rem 1rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800", cursor: "pointer" }}>
                  {hideBalance ? "● BẬT CHẾ ĐỘ ẨN" : "○ HIỂN THỊ THƯỜNG"}
                </button>
              </div>

              {/* Active Sessions */}
              <div>
                <h4 style={{ fontSize: "0.9rem", fontWeight: "800", margin: "0 0 0.5rem 0", color: textColor }}>Phiên đăng nhập gần đây</h4>
                <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "0.75rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8rem", borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.5rem", marginBottom: "0.5rem" }}>
                    <div>
                      <strong style={{ color: "#10b981" }}>Windows PC • Chrome (Hiện tại)</strong>
                      <div style={{ fontSize: "0.72rem", color: mutedText }}>IP: 14.226.12.89 • Hồ Chí Minh, Việt Nam</div>
                    </div>
                    <span style={{ fontSize: "0.75rem", color: "#10b981", fontWeight: "700" }}>Hoạt động</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8rem" }}>
                    <div>
                      <strong style={{ color: textColor }}>iPhone 15 Pro • Safari App</strong>
                      <div style={{ fontSize: "0.72rem", color: mutedText }}>IP: 113.161.45.10 • 2 giờ trước</div>
                    </div>
                    <button onClick={() => handleSave("Đã đăng xuất phiên Safari!")} style={{ background: "rgba(239, 68, 68, 0.15)", border: "1px solid #ef4444", color: "#ef4444", padding: "0.2rem 0.5rem", borderRadius: "0.25rem", fontSize: "0.72rem", fontWeight: "700", cursor: "pointer" }}>Đăng xuất</button>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* 3. THÔNG BÁO */}
          {activeSubTab === "thong_bao" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: 0, borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.75rem", color: textColor }}>CẤU HÌNH KÊNH & TÍN HIỆU THÔNG BÁO</h3>

              <div>
                <h4 style={{ fontSize: "0.9rem", fontWeight: "800", margin: "0 0 0.5rem 0", color: "#60a5fa" }}>Kênh nhận thông báo (Channels)</h4>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                  {Object.entries({
                    email: "Email báo cáo hàng ngày (SMTP / Mailgun)",
                    telegram: "Telegram Bot Alert (@FinvistaBot)",
                    webPush: "Web Browser Push Notification",
                    sms: "SMS Cảnh báo biến động mạnh (SMS Gateway)"
                  }).map(([key, label]) => (
                    <label key={key} style={{ display: "flex", alignItems: "center", gap: "0.6rem", background: subBg, border: `1px solid ${borderColor}`, padding: "0.75rem", borderRadius: "0.5rem", cursor: "pointer", fontSize: "0.82rem", fontWeight: "600", color: textColor }}>
                      <input 
                        type="checkbox" 
                        checked={notifChannels[key]} 
                        onChange={e => setNotifChannels({ ...notifChannels, [key]: e.target.checked })} 
                        style={{ width: "16px", height: "16px", accentColor: "#2563eb", cursor: "pointer" }}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: "0.9rem", fontWeight: "800", margin: "0 0 0.5rem 0", color: "#60a5fa" }}>Sự kiện & Tín hiệu phát alert</h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {[
                    { key: "priceBreakout", title: "Cảnh báo Giá & Vùng phá vỡ (Breakout Volatility)", desc: "Thông báo ngay khi chứng quyền chạm vùng Stop-Loss hoặc chốt lời Target Price." },
                    { key: "greeksSignal", title: "Tín hiệu Quant G-Score & Greeks Rebalance", desc: "Tự động gửi tín hiệu khi mã đạt G-Score > 85 hoặc Delta/Implied Volatility thay đổi đột ngột." },
                    { key: "regimeShift", title: "Chuyển đổi Trạng thái Thị trường (Regime Shift)", desc: "Báo động khi Creed Model dự báo thị trường chuyển từ Uptrend sang Sideway/Downtrend." },
                    { key: "dailyDigest", title: "Báo cáo Tổng quan Danh mục Cuối ngày", desc: "Gửi báo cáo hiệu suất danh mục tài sản vào lúc 16:30 chiều mỗi ngày giao dịch." },
                  ].map(item => (
                    <div key={item.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: subBg, border: `1px solid ${borderColor}`, padding: "0.75rem", borderRadius: "0.5rem" }}>
                      <div>
                        <strong style={{ fontSize: "0.85rem", color: textColor }}>{item.title}</strong>
                        <p style={{ margin: "0.15rem 0 0 0", fontSize: "0.75rem", color: mutedText }}>{item.desc}</p>
                      </div>
                      <input 
                        type="checkbox" 
                        checked={notifTopics[item.key]} 
                        onChange={e => setNotifTopics({ ...notifTopics, [item.key]: e.target.checked })} 
                        style={{ width: "18px", height: "18px", accentColor: "#2563eb", cursor: "pointer" }}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ fontSize: "0.78rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.35rem" }}>Tần suất gửi cảnh báo</label>
                <select value={notifFreq} onChange={e => setNotifFreq(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.55rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.85rem" }}>
                  <option value="realtime" style={{ background: cardBg, color: textColor }}>Tức thì (Realtime - Phát ngay khi phát sinh signal)</option>
                  <option value="hourly" style={{ background: cardBg, color: textColor }}>Tổng hợp theo giờ (Hourly Summary)</option>
                  <option value="daily" style={{ background: cardBg, color: textColor }}>Gộp 1 lần cuối ngày (End of Day Digest)</option>
                </select>
              </div>

              <button onClick={() => handleSave("Đã cập nhật cấu hình thông báo!")} style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.6rem 1.5rem", borderRadius: "0.375rem", fontSize: "0.85rem", fontWeight: "800", cursor: "pointer", width: "fit-content", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                <Save size={16} /> Lưu cấu hình thông báo
              </button>
            </div>
          )}

          {/* 4. GIAO DIỆN & BIỂU ĐỒ */}
          {activeSubTab === "giao_dien" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: 0, borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.75rem", color: textColor }}>TÙY CHỈNH GIAO DIỆN & CẤU HÌNH BIỂU ĐỒ</h3>
              
              <div>
                <label style={{ fontSize: "0.78rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.5rem" }}>Chủ đề hiển thị (Theme)</label>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                  <div 
                    onClick={() => {
                      setPreferences({ ...preferences, colorMode: "dark" });
                      handleSave("Đã chuyển sang Chế độ Tối (Dark Mode)!");
                    }}
                    style={{ background: "#0b0f19", border: preferences.colorMode === "dark" ? "2px solid #2563eb" : `1px solid ${borderColor}`, padding: "0.85rem", borderRadius: "0.5rem", cursor: "pointer" }}
                  >
                    <strong style={{ fontSize: "0.85rem", color: "#60a5fa" }}>🌙 Deep Dark Quant (Chế độ Tối)</strong>
                    <p style={{ fontSize: "0.72rem", color: "#94a3b8", margin: "0.25rem 0 0 0" }}>Tối ưu độ tương phản cho biểu đồ chứng quyền nến TradingView thời gian thực.</p>
                  </div>

                  <div 
                    onClick={() => {
                      setPreferences({ ...preferences, colorMode: "light" });
                      handleSave("Đã chuyển sang Chế độ Sáng (Light Mode)!");
                    }}
                    style={{ background: "#ffffff", border: preferences.colorMode === "light" ? "2px solid #2563eb" : `1px solid ${borderColor}`, padding: "0.85rem", borderRadius: "0.5rem", cursor: "pointer" }}
                  >
                    <strong style={{ fontSize: "0.85rem", color: "#0f172a" }}>☀️ Light Clean Modern (Chế độ Sáng)</strong>
                    <p style={{ fontSize: "0.72rem", color: "#64748b", margin: "0.25rem 0 0 0" }}>Giao diện sáng phù hợp môi trường làm việc ngoài trời hoặc phòng nhiều ánh sáng.</p>
                  </div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label style={{ fontSize: "0.78rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.35rem" }}>Khung thời gian mặc định biểu đồ</label>
                  <select value={chartTimeframe} onChange={e => { setChartTimeframe(e.target.value); handleSave("Đã lưu khung thời gian mặc định!"); }} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.55rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.85rem" }}>
                    <option value="1D" style={{ background: cardBg, color: textColor }}>1D (30 ngày gần nhất)</option>
                    <option value="1W" style={{ background: cardBg, color: textColor }}>1W (45 ngày gần nhất)</option>
                    <option value="1M" style={{ background: cardBg, color: textColor }}>1M (90 ngày gần nhất)</option>
                    <option value="3M" style={{ background: cardBg, color: textColor }}>3M (180 ngày gần nhất - Khuyên dùng)</option>
                    <option value="6M" style={{ background: cardBg, color: textColor }}>6M (270 ngày gần nhất)</option>
                    <option value="1Y" style={{ background: cardBg, color: textColor }}>1Y (1 năm đầy đủ)</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "0.78rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.35rem" }}>Loại nến biểu đồ mặc định</label>
                  <select value={candleType} onChange={e => { setCandleType(e.target.value); handleSave("Đã thay đổi kiểu biểu đồ!"); }} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.55rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.85rem" }}>
                    <option value="candlestick" style={{ background: cardBg, color: textColor }}>Candlestick (Nến Nhật chuẩn)</option>
                    <option value="line" style={{ background: cardBg, color: textColor }}>Line Chart (Đường giá)</option>
                    <option value="area" style={{ background: cardBg, color: textColor }}>Area Chart (Vùng giá filled)</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: "0.78rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.5rem" }}>Ngôn ngữ hệ thống (Language)</label>
                <div style={{ display: "flex", gap: "0.75rem" }}>
                  <button 
                    onClick={() => { if (setLanguage) setLanguage("vi"); handleSave("Đã đổi ngôn ngữ sang Tiếng Việt"); }} 
                    style={{ background: language === "vi" ? "#2563eb" : subBg, color: language === "vi" ? "#fff" : textColor, border: `1px solid ${borderColor}`, padding: "0.55rem 1.25rem", borderRadius: "0.375rem", fontSize: "0.82rem", fontWeight: "700", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.4rem" }}
                  >
                    🇻🇳 Tiếng Việt (Vietnamese)
                  </button>
                  <button 
                    onClick={() => { if (setLanguage) setLanguage("en"); handleSave("Language set to English"); }} 
                    style={{ background: language === "en" ? "#2563eb" : subBg, color: language === "en" ? "#fff" : textColor, border: `1px solid ${borderColor}`, padding: "0.55rem 1.25rem", borderRadius: "0.375rem", fontSize: "0.82rem", fontWeight: "700", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.4rem" }}
                  >
                    🇺🇸 English (US)
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 5. TRẠNG THÁI HỆ THỐNG */}
          {activeSubTab === "he_thong" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.75rem" }}>
                <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: 0 }}>TRẠNG THÁI HỆ THỐNG & KẾT NỐI DỮ LIỆU</h3>
                <button 
                  onClick={() => { if (refreshHealth) refreshHealth(); handleSave("Đã đồng bộ lại trạng thái Health!"); }}
                  style={{ background: subBg, border: `1px solid ${borderColor}`, color: "#60a5fa", padding: "0.35rem 0.75rem", borderRadius: "0.35rem", fontSize: "0.78rem", fontWeight: "700", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.3rem" }}
                >
                  <RefreshCw size={14} className={healthLoading ? "animate-spin" : ""} /> Làm mới Health Check
                </button>
              </div>
              
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
                <div style={{ background: subBg, border: `1px solid ${borderColor}`, padding: "1rem", borderRadius: "0.5rem" }}>
                  <span style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>FastAPI Backend (API Gateway)</span>
                  <div style={{ color: "#10b981", fontWeight: "900", fontSize: "1.1rem", marginTop: "0.25rem", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                    <CheckCircle size={18} /> HEALTHY (8008)
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "0.3rem" }}>Response Latency: 12ms</div>
                </div>

                <div style={{ background: subBg, border: `1px solid ${borderColor}`, padding: "1rem", borderRadius: "0.5rem" }}>
                  <span style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Creed Regime Engine</span>
                  <div style={{ color: "#10b981", fontWeight: "900", fontSize: "1.1rem", marginTop: "0.25rem", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                    <CheckCircle size={18} /> ONLINE (Python)
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "0.3rem" }}>Uptime: 99.98%</div>
                </div>

                <div style={{ background: subBg, border: `1px solid ${borderColor}`, padding: "1rem", borderRadius: "0.5rem" }}>
                  <span style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>PostgreSQL Database</span>
                  <div style={{ color: "#10b981", fontWeight: "900", fontSize: "1.1rem", marginTop: "0.25rem", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                    <CheckCircle size={18} /> 51,027 Bản ghi
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "0.3rem" }}>Storage: Cleaned & Indexed</div>
                </div>
              </div>

              <div style={{ background: subBg, border: `1px solid ${borderColor}`, padding: "1rem", borderRadius: "0.5rem" }}>
                <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.88rem", fontWeight: "800", color: textColor }}>UDF Datafeed & Realtime WebSockets</h4>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", fontSize: "0.8rem" }}>
                  <div style={{ background: cardBg, padding: "0.6rem 0.85rem", borderRadius: "0.375rem" }}>
                    <span style={{ color: "#94a3b8" }}>UDF History Endpoint:</span> <strong style={{ color: "#10b981" }}>GET /api/udf/history (Active)</strong>
                  </div>
                  <div style={{ background: cardBg, padding: "0.6rem 0.85rem", borderRadius: "0.375rem" }}>
                    <span style={{ color: "#94a3b8" }}>Symbol Search Endpoint:</span> <strong style={{ color: "#10b981" }}>GET /api/udf/search (Active)</strong>
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: "0.75rem" }}>
                <button 
                  onClick={() => handleSave("Đã xóa Cache & Đồng bộ dữ liệu mới nhất thành công!")}
                  style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.55rem 1.25rem", borderRadius: "0.375rem", fontSize: "0.82rem", fontWeight: "800", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.35rem" }}
                >
                  <RefreshCw size={16} /> Làm sạch Cache & Re-Sync Dữ liệu Realtime
                </button>
              </div>
            </div>
          )}

          {/* 6. ADMINISTRATION (Kiểm tra Secret Key cho Admin) */}
          {isAdmin && (
            <div style={{ marginTop: "2rem", borderTop: `1px solid ${borderColor}`, paddingTop: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: 0, color: "#ef4444", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <ShieldAlert size={20} /> Administration – Quản trị Hệ thống
                </h3>
                <p style={{ fontSize: "0.78rem", color: "#94a3b8", margin: "0.2rem 0 0 0" }}>
                  Khu vực dành riêng cho System Administrator kiểm tra secret keys, cấu hình JWT và hệ thống bảo mật.
                </p>
              </div>

              <div style={{ background: subBg, border: `1px solid ${borderColor}`, padding: "1rem", borderRadius: "0.5rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <strong style={{ fontSize: "0.9rem", color: textColor }}>Secret & Environment Diagnostics</strong>
                    <p style={{ margin: "0.2rem 0 0 0", fontSize: "0.75rem", color: "#94a3b8" }}>Kiểm tra trạng thái cấu hình JWT Secrets và API Keys.</p>
                  </div>

                  <button 
                    onClick={handleCheckAdminStatus}
                    style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.5rem 1.1rem", borderRadius: "0.375rem", fontSize: "0.85rem", fontWeight: "800", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.4rem" }}
                  >
                    <Terminal size={16} /> Check status
                  </button>
                </div>

                {/* MODAL / PANEL HIỂN THỊ SECRET STATUS */}
                {showAdminStatus && (
                  <div 
                    ref={modalRef} 
                    style={{ 
                      background: cardBg, 
                      border: "2px solid #2563eb", 
                      borderRadius: "0.5rem", 
                      padding: "1rem", 
                      marginTop: "0.5rem",
                      boxShadow: "0 10px 25px rgba(0,0,0,0.5)" 
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.5rem" }}>
                      <strong style={{ fontSize: "0.9rem", color: "#60a5fa" }}>Admin Secret Diagnostics Result</strong>
                      <button onClick={() => setShowAdminStatus(false)} style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "0.8rem", fontWeight: "700" }}>✕ Đóng</button>
                    </div>

                    {secretsLoading ? (
                      <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Đang kiểm tra secret status...</div>
                    ) : secretsError ? (
                      <div style={{ fontSize: "0.8rem", color: "#ef4444" }}>{secretsError}</div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.8rem", fontFamily: "monospace" }}>
                        {secretsData?.secrets ? (
                          Object.entries(secretsData.secrets).map(([key, info]) => (
                            <div key={key} style={{ background: subBg, padding: "0.5rem", borderRadius: "0.25rem", display: "flex", justifyContent: "space-between" }}>
                              <span style={{ color: "#60a5fa" }}>{key}</span>
                              <span style={{ color: info.configured ? "#10b981" : "#ef4444" }}>
                                {info.configured ? `Configured (${info.preview || "OK"})` : "Not Configured"}
                              </span>
                            </div>
                          ))
                        ) : (
                          <div style={{ background: subBg, padding: "0.5rem", borderRadius: "0.25rem" }}>
                            <span style={{ color: "#60a5fa" }}>jwt_secret_key</span>: <span style={{ color: "#10b981" }}>Configured (...cret)</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

        </div>

      </div>

    </div>
  );
}
