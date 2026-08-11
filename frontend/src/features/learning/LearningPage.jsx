import React, { useState } from "react";
import { BookOpen, Video, Play, Award, CheckCircle, HelpCircle, ChevronRight } from "lucide-react";
import { useThemeTokens } from "../../app/useThemeTokens.js";

export function LearningPage({ language = "vi", preferences = {} }) {
  const isEnglish = language === "en";
  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);
  const [activeTab, setActiveTab] = useState("course");
  const [selectedAns, setSelectedAns] = useState(null);
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizScore, setQuizScore] = useState(null);

  const courses = [
    { 
      id: 1, 
      title: isEnglish ? "Warrant Fundamentals" : "Cơ bản về Chứng quyền", 
      subtitle: isEnglish ? "Beginner" : "Cơ bản", 
      lessons: "12", 
      completed: true, 
      desc: isEnglish ? "Understanding warrant structure, pricing basics, and key terminology" : "Hiểu về cấu trúc chứng quyền, định giá cơ bản và thuật ngữ chính"
    },
    { 
      id: 2, 
      title: isEnglish ? "Greeks & Risk Management" : "Greeks & Quản lý rủi ro", 
      subtitle: isEnglish ? "Intermediate" : "Trung cấp", 
      lessons: "18", 
      completed: false, 
      desc: isEnglish ? "Master Delta, Gamma, Theta, Vega and portfolio hedging strategies" : "Làm chủ Delta, Gamma, Theta, Vega và chiến lược phòng ngừa danh mục"
    },
    { 
      id: 3, 
      title: isEnglish ? "Advanced Trading Strategies" : "Chiến lược Giao dịch Nâng cao", 
      subtitle: isEnglish ? "Advanced" : "Nâng cao", 
      lessons: "24", 
      completed: false, 
      desc: isEnglish ? "Spread trading, arbitrage opportunities, and market timing techniques" : "Giao dịch spread, cơ hội arbitrage và kỹ thuật thị trường thời gian thực"
    },
    { 
      id: 4, 
      title: isEnglish ? "Quantitative Backtesting" : "Backtest Định lượng", 
      subtitle: isEnglish ? "Expert" : "Chuyên gia", 
      lessons: "15", 
      completed: false, 
      desc: isEnglish ? "Build and test trading strategies using Python and historical data" : "Xây dựng và kiểm tra chiến lược giao dịch bằng Python và dữ liệu lịch sử"
    }
  ];

  const quizOptions = isEnglish ? [
    { key: "A", text: "A. 0 < Delta < 1" },
    { key: "B", text: "B. -1 < Delta < 0" },
    { key: "C", text: "C. -1 < Delta < 1" },
    { key: "D", text: "D. Delta > 1" }
  ] : [
    { key: "A", text: "A. 0 < Delta < 1" },
    { key: "B", text: "B. -1 < Delta < 0" },
    { key: "C", text: "C. -1 < Delta < 1" },
    { key: "D", text: "D. Delta > 1" }
  ];
  const correctAns = "A";

  function handleQuizSubmit() {
    if (!selectedAns) return;
    setQuizSubmitted(true);
    setQuizScore(selectedAns === correctAns);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: bg }}>
      
      {/* HEADER BAR (PDF Page 15) */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <h2 style={{ fontSize: "1.5rem", fontWeight: "900", margin: 0, letterSpacing: "0.5px", color: textColor }}>
              {isEnglish ? "LEARNING — WARRANT INVESTMENT" : "LEARNING — HỌC ĐẦU TƯ CHỨNG QUYỀN"}
            </h2>
            <p style={{ fontSize: "0.82rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
              {isEnglish ? "Quantitative warrant trading training program from basic to advanced" : "Chương trình đào tạo giao dịch chứng quyền chuẩn định lượng từ cơ bản đến nâng cao"}
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.35rem", background: subBg, padding: "0.25rem", borderRadius: "0.5rem", width: "fit-content" }}>
          {[
            { id: "course", label: isEnglish ? "Courses" : "Khóa học" },
            { id: "video", label: isEnglish ? "Videos" : "Video" },
            { id: "articles", label: isEnglish ? "Articles" : "Bài viết" },
            { id: "quiz", label: isEnglish ? "Daily Quiz" : "Quiz hàng ngày" },
            { id: "sim", label: isEnglish ? "Simulation" : "Mô phỏng" }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: activeTab === tab.id ? "#2563eb" : "transparent",
                color: activeTab === tab.id ? "#fff" : mutedText,
                border: "none",
                borderRadius: "0.375rem",
                padding: "0.4rem 1.25rem",
                fontSize: "0.82rem",
                fontWeight: "700",
                cursor: "pointer"
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.25rem" }}>
        
        {/* Left Side: Courses list */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: "800", margin: "0 0 1rem 0", color: textColor }}>
              {isEnglish ? "FEATURED COURSES" : "KHÓA HỌC NỔI BẬT"}
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              {courses.map(course => (
                <div key={course.id} style={{
                  background: subBg,
                  border: `1px solid ${borderColor}`,
                  borderRadius: "0.5rem",
                  padding: "1rem",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  gap: "0.75rem"
                }}>
                  <div>
                    <span style={{ fontSize: "0.72rem", color: "#60a5fa", fontWeight: "700" }}>{course.subtitle}</span>
                    <h4 style={{ fontSize: "0.95rem", fontWeight: "800", marginTop: "0.25rem", color: textColor }}>{course.title}</h4>
                    <p style={{ fontSize: "0.78rem", color: mutedText, marginTop: "0.4rem" }}>{course.desc}</p>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: `1px solid ${borderColor}`, paddingTop: "0.75rem" }}>
                    <span style={{ fontSize: "0.72rem", color: mutedText }}>{course.lessons} {isEnglish ? "lessons" : "bài học"}</span>
                    <button style={{ padding: "0.3rem 0.75rem", fontSize: "0.75rem", fontWeight: "800", borderRadius: "0.25rem", border: "none", background: course.completed ? subBg : "#2563eb", color: course.completed ? mutedText : "#fff", cursor: "pointer" }}>
                      {course.completed ? (isEnglish ? "Review" : "Xem lại") : (isEnglish ? "Start" : "Bắt đầu")}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Progress Tracker */}
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: "800", margin: "0 0 1rem 0", color: textColor }}>
              {isEnglish ? "YOUR LEARNING PROGRESS" : "TIẾN TRÌNH HỌC TẬP CỦA BẠN"}
            </h3>
            <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", marginBottom: "0.5rem" }}>
                  <span style={{ color: textColor }}>{isEnglish ? "Total completion rate" : "Tổng tỷ lệ hoàn thành"}</span>
                  <strong style={{ color: "#10b981" }}>65%</strong>
                </div>
                <div style={{ background: subBg, height: "8px", borderRadius: "999px", overflow: "hidden" }}>
                  <div style={{ background: "#10b981", width: "65%", height: "100%" }}></div>
                </div>
              </div>
              <div style={{ borderLeft: `1px solid ${borderColor}`, paddingLeft: "1.5rem" }}>
                <strong style={{ fontSize: "1.5rem", color: textColor }}>13/20</strong>
                <p style={{ fontSize: "0.75rem", color: mutedText, margin: 0 }}>{isEnglish ? "lessons completed" : "bài học hoàn thành"}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Interactive Daily Quiz */}
        <div>
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: "800", margin: "0 0 1rem 0", display: "flex", alignItems: "center", gap: "0.5rem", color: textColor }}>
              <HelpCircle size={16} style={{ color: "#f59e0b" }} /> {isEnglish ? "DAILY TRIVIA QUIZ" : "QUIZ TRẮC NGHIỆM HÀNG NGÀY"}
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <span style={{ fontSize: "0.75rem", color: mutedText }}>{isEnglish ? "Question 1/5" : "Câu 1/5"}</span>
                <p style={{ fontWeight: "700", color: textColor, fontSize: "0.9rem", marginTop: "0.25rem" }}>
                  {isEnglish ? "What is the range of Delta for a Call Warrant?" : "Delta của chứng quyền MUA (Call Warrant) luôn nằm trong khoảng nào?"}
                </p>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {quizOptions.map(opt => {
                  const isSelected = selectedAns === opt.key;
                  return (
                    <button
                      key={opt.key}
                      disabled={quizSubmitted}
                      onClick={() => setSelectedAns(opt.key)}
                      style={{
                        textAlign: "left",
                        width: "100%",
                        padding: "0.65rem",
                        borderRadius: "0.375rem",
                        background: isSelected ? "rgba(37,99,235,0.2)" : subBg,
                        border: isSelected ? "1px solid #2563eb" : `1px solid ${borderColor}`,
                        color: isSelected ? "#60a5fa" : textColor,
                        cursor: quizSubmitted ? "default" : "pointer",
                        fontSize: "0.82rem",
                        fontWeight: isSelected ? "700" : "500"
                      }}
                    >
                      {opt.text}
                    </button>
                  );
                })}
              </div>

              {quizSubmitted ? (
                <div style={{
                  padding: "0.75rem",
                  borderRadius: "0.375rem",
                  background: quizScore ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
                  border: quizScore ? "1px solid #10b981" : "1px solid #ef4444",
                  fontSize: "0.82rem",
                  color: quizScore ? "#10b981" : "#ef4444",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem"
                }}>
                  <CheckCircle size={16} />
                  <span>
                    {quizScore
                      ? (isEnglish ? "Correct! Call Warrant Delta always lies in range (0, 1)." : "Chính xác! Delta của Call Warrant luôn nằm trong khoảng (0, 1).")
                      : (isEnglish ? "Incorrect! The correct answer is A (0 < Delta < 1)." : "Chưa chính xác! Đáp án đúng là A (0 < Delta < 1).")}
                  </span>
                </div>
              ) : (
                <button
                  onClick={handleQuizSubmit}
                  disabled={!selectedAns}
                  style={{ width: "100%", background: "#2563eb", color: "#fff", border: "none", padding: "0.5rem", borderRadius: "0.375rem", fontWeight: "800", fontSize: "0.82rem", cursor: "pointer" }}
                >
                  {isEnglish ? "SUBMIT ANSWER" : "NỘP BÀI TRẢ LỜI"}
                </button>
              )}
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
