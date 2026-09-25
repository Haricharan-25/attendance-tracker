import { useState, useEffect } from "react";
import api from "../services/api";

function AttendancePlanner({ syncTrigger = 0, onSyncRequest }) {
  const [plannerData, setPlannerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Month navigation: 0 = current month, 1 = next month
  const [monthOffset, setMonthOffset] = useState(0);

  // Selected date string: "YYYY-MM-DD"
  const [selectedDate, setSelectedDate] = useState("");

  // Multi-date Simulation selections state:
  // { "YYYY-MM-DD": { [subjectName]: "present" | "absent" } }
  const [selections, setSelections] = useState({});

  // Simulation calculation result
  const [calculating, setCalculating] = useState(false);
  const [simResult, setSimResult] = useState(null);

  // Plan Leave mode state
  const [leaveMode, setLeaveMode] = useState(false);
  const [selectedLeaveDates, setSelectedLeaveDates] = useState([]); // array of "YYYY-MM-DD"
  const [leaveCalculating, setLeaveCalculating] = useState(false);
  const [leaveResult, setLeaveResult] = useState(null);

  const fetchPlannerData = () => {
    setLoading(true);
    api
      .get("/attendance-planner/")
      .then((res) => {
        setPlannerData(res.data);
        setError("");
        // Default selected date to today
        if (res.data?.today) {
          setSelectedDate(res.data.today);
        }
      })
      .catch((err) => {
        console.error("Planner load error:", err);
        setError("Unable to load timetable. Please try again.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPlannerData();
  }, [syncTrigger]);

  // Today reference
  const today = plannerData?.today ? new Date(plannerData.today + "T00:00:00") : new Date();
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth(); // 0-indexed

  // Active month/year based on monthOffset (0 or 1)
  const activeDate = new Date(currentYear, currentMonth + monthOffset, 1);
  const activeYear = activeDate.getFullYear();
  const activeMonth = activeDate.getMonth();

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const dayNamesAbbr = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

  // Helper to format date YYYY-MM-DD
  const formatDateStr = (year, month, day) => {
    const m = String(month + 1).padStart(2, "0");
    const d = String(day).padStart(2, "0");
    return `${year}-${m}-${d}`;
  };

  // Helper to get timetable day abbr ("MON", "TUE", etc.) for a date string
  const getDayAbbr = (dateStr) => {
    const d = new Date(dateStr + "T00:00:00");
    const jsDay = d.getDay(); // 0 is Sunday, 1 is Monday
    const map = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
    return map[jsDay];
  };

  // Get subjects scheduled on a given date string
  const getClassesForDate = (dateStr) => {
    if (!plannerData?.timetable) return [];
    const dayAbbr = getDayAbbr(dateStr);
    return plannerData.timetable[dayAbbr] || [];
  };

  // Next 7 days projection map for fast lookup on calendar cells: { "YYYY-MM-DD": { ... } }
  const next7DaysMap = {};
  if (plannerData?.next_7_days) {
    plannerData.next_7_days.forEach((item) => {
      next7DaysMap[item.date] = item;
    });
  }

  // Handle Subject Choice Selection in simulation mode by slot index
  const handleSelectChoice = (dateStr, slotIndex, subject, choice) => {
    setSelections((prev) => {
      const dateSelections = { ...(prev[dateStr] || {}) };
      // Store object with subject and choice keyed by slotIndex
      dateSelections[slotIndex] = { subject, choice };
      return {
        ...prev,
        [dateStr]: dateSelections,
      };
    });
    // Reset calculated result when selections change
    setSimResult(null);
  };

  // Calculate Attendance (Simulation Mode)
  const handleCalculateSimulation = async () => {
    setCalculating(true);
    try {
      // Format selections payload: array of { subject, choice } per date
      const formattedSelections = {};
      Object.entries(selections).forEach(([dStr, slotChoices]) => {
        formattedSelections[dStr] = Object.values(slotChoices).map((item) => ({
          subject: item.subject,
          choice: item.choice,
        }));
      });

      const res = await api.post("/attendance-planner/calculate/", {
        mode: "simulation",
        selections: formattedSelections,
      });
      setSimResult(res.data);
    } catch (err) {
      console.error("Simulation calc error:", err);
    } finally {
      setCalculating(false);
    }
  };

  // Handle Date Click
  const handleDateClick = (dateStr) => {
    if (leaveMode) {
      // Plan Leave Mode: toggle date in selectedLeaveDates
      setSelectedLeaveDates((prev) => {
        if (prev.includes(dateStr)) {
          return prev.filter((d) => d !== dateStr);
        } else {
          return [...prev, dateStr];
        }
      });
      setLeaveResult(null);
    } else {
      // Normal simulation mode: set selected date
      setSelectedDate(dateStr);
    }
  };

  // Calculate Leave Impact
  const handleCalculateLeave = async () => {
    if (selectedLeaveDates.length === 0) return;
    setLeaveCalculating(true);
    try {
      const res = await api.post("/attendance-planner/calculate/", {
        mode: "leave",
        leave_dates: selectedLeaveDates,
      });
      setLeaveResult(res.data);
    } catch (err) {
      console.error("Leave calc error:", err);
    } finally {
      setLeaveCalculating(false);
    }
  };

  // Clear Selected Leave Days
  const handleClearLeaveDays = () => {
    setSelectedLeaveDates([]);
    setLeaveResult(null);
  };

  // Build calendar matrix for activeMonth / activeYear
  const daysInMonth = new Date(activeYear, activeMonth + 1, 0).getDate();
  const firstDayOfWeek = new Date(activeYear, activeMonth, 1).getDay(); // 0 is SUN
  // Shift so Monday is index 0: (SUN is 6, MON is 0, TUE is 1, etc.)
  const startingCol = (firstDayOfWeek + 6) % 7;

  const calendarDays = [];
  // Empty slots before 1st of month
  for (let i = 0; i < startingCol; i++) {
    calendarDays.push(null);
  }
  // Days of month
  for (let d = 1; d <= daysInMonth; d++) {
    calendarDays.push(d);
  }

  // Selected date scheduled classes
  const selectedDateClasses = selectedDate ? getClassesForDate(selectedDate) : [];
  const selectedDateSelections = selectedDate ? selections[selectedDate] || {} : {};

  // Format header for selected date (e.g. "Friday, September 25")
  const formatSelectedDateHeader = (dateStr) => {
    if (!dateStr) return "";
    const d = new Date(dateStr + "T00:00:00");
    const options = { weekday: "long", month: "long", day: "numeric" };
    return d.toLocaleDateString(undefined, options);
  };

  if (loading) {
    return (
      <div className="planner-card loading-state">
        <div className="spinner"></div>
        <p className="loading-caption">Loading timetable...</p>
      </div>
    );
  }

  const hasTimetable = plannerData?.timetable && Object.keys(plannerData.timetable).length > 0;

  if (error && !plannerData) {
    return (
      <div className="planner-card empty-state">
        <div className="empty-icon">📅</div>
        <h3>Attendance Planner</h3>
        <p className="planner-err-text">{error}</p>
        <button className="primary-btn retry-btn" onClick={fetchPlannerData}>
          Try Again
        </button>
      </div>
    );
  }

  const todayStr = plannerData?.today || formatDateStr(today.getFullYear(), today.getMonth(), today.getDate());

  return (
    <div className="attendance-planner-container">
      {/* Planner Card Header */}
      <div className="planner-card-header">
        <div>
          <h2 className="planner-title">Attendance Planner</h2>
          <span className="planner-subtitle">What-If Attendance Simulator</span>
        </div>
        <button
          type="button"
          className={`mode-toggle-btn ${leaveMode ? "active-leave-mode" : ""}`}
          onClick={() => {
            setLeaveMode(!leaveMode);
            setLeaveResult(null);
            setSimResult(null);
          }}
        >
          {leaveMode ? "← Simulator Mode" : "✈ Plan Leave"}
        </button>
      </div>

      {!hasTimetable && (
        <div className="leave-mode-banner" style={{ background: "rgba(59, 130, 246, 0.12)", borderColor: "rgba(59, 130, 246, 0.4)", color: "#93c5fd" }}>
          <span>
            ℹ No timetable found for this student account yet. Click <strong>Sync</strong> above to fetch your timetable and attendance records from GEMS.
          </span>
        </div>
      )}

      {/* Month Navigation: Current month & Next month only */}
      <div className="calendar-month-bar">
        <button
          type="button"
          className="month-nav-btn"
          disabled={monthOffset === 0}
          onClick={() => setMonthOffset(0)}
          title="Previous month (disabled for past months)"
        >
          ‹
        </button>
        <span className="month-display">
          {monthNames[activeMonth]} {activeYear}
        </span>
        <button
          type="button"
          className="month-nav-btn"
          disabled={monthOffset === 1}
          onClick={() => setMonthOffset(1)}
          title="Next month"
        >
          ›
        </button>
      </div>

      {leaveMode && (
        <div className="leave-mode-banner">
          <span>Tap dates on calendar to mark leave days. Every scheduled class will count as absent.</span>
        </div>
      )}

      {/* Calendar Grid */}
      <div className="planner-calendar">
        {/* Day name headers: MON TUE WED THU FRI SAT SUN */}
        <div className="calendar-weekdays-row">
          {["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((d) => (
            <span key={d} className="calendar-weekday-cell">
              {d}
            </span>
          ))}
        </div>

        {/* Calendar Day Cells */}
        <div className="calendar-days-grid">
          {calendarDays.map((dayNum, index) => {
            if (dayNum === null) {
              return <div key={`empty-${index}`} className="calendar-day-cell empty-slot" />;
            }

            const cellDateStr = formatDateStr(activeYear, activeMonth, dayNum);
            const isToday = cellDateStr === todayStr;
            const isSelected = selectedDate === cellDateStr && !leaveMode;
            const isLeaveSelected = selectedLeaveDates.includes(cellDateStr) && leaveMode;
            const next7Info = next7DaysMap[cellDateStr];
            const hasSimSelections = selections[cellDateStr] && Object.keys(selections[cellDateStr]).length > 0;

            return (
              <div
                key={cellDateStr}
                className={`calendar-day-cell ${isToday ? "today-cell" : ""} ${
                  isSelected ? "selected-cell" : ""
                } ${isLeaveSelected ? "leave-selected-cell" : ""} ${
                  hasSimSelections ? "has-selections" : ""
                }`}
                onClick={() => handleDateClick(cellDateStr)}
              >
                <div className="day-number-row">
                  <span className="day-number">{dayNum}</span>
                  {hasSimSelections && <span className="selection-dot" title="Modified in simulation">•</span>}
                </div>

                {/* Next 7 Days Attendance Information Directly Visible */}
                {next7Info && (
                  <div className="next7-projection-badge">
                    {next7Info.no_classes ? (
                      <span className="no-classes-tag">No classes</span>
                    ) : (
                      <span className="proj-percent-tag">{next7Info.projected_percentage}%</span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ========================================================
          MODE 1: NORMAL DATE SELECTION & MULTI-DATE SIMULATION
          ======================================================== */}
      {!leaveMode && (
        <div className="date-simulation-panel">
          <div className="selected-date-header">
            <span className="selected-date-label">Selected Date:</span>
            <h3 className="selected-date-val">{formatSelectedDateHeader(selectedDate)}</h3>
          </div>

          {selectedDateClasses.length === 0 ? (
            <div className="empty-classes-msg">
              <span>No classes scheduled for this date.</span>
            </div>
          ) : (
            <div className="scheduled-classes-list">
              {selectedDateClasses.map((subjectCode, idx) => {
                const currentChoice = selectedDateSelections[idx]?.choice;
                return (
                  <div key={`${subjectCode}-${idx}`} className="subject-sim-row">
                    <span className="sim-subject-name">{subjectCode}</span>
                    <div className="sim-choice-toggle">
                      <button
                        type="button"
                        className={`choice-btn present-btn ${
                          currentChoice === "present" ? "active-present" : ""
                        }`}
                        onClick={() => handleSelectChoice(selectedDate, idx, subjectCode, "present")}
                      >
                        Present
                      </button>
                      <button
                        type="button"
                        className={`choice-btn absent-btn ${
                          currentChoice === "absent" ? "active-absent" : ""
                        }`}
                        onClick={() => handleSelectChoice(selectedDate, idx, subjectCode, "absent")}
                      >
                        Absent
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Action Row */}
          <div className="planner-actions-row">
            <button
              type="button"
              className="primary-btn calculate-btn"
              onClick={handleCalculateSimulation}
              disabled={calculating}
            >
              {calculating ? "Calculating..." : "Calculate Attendance"}
            </button>
          </div>

          {/* Simulation Result Card */}
          {simResult && (
            <div className="simulation-result-card">
              <div className="sim-result-head">
                <span className="res-badge">Projected Attendance</span>
                <span
                  className={`change-tag ${
                    simResult.change >= 0 ? "positive-change" : "negative-change"
                  }`}
                >
                  {simResult.change >= 0 ? `+${simResult.change}%` : `${simResult.change}%`}
                </span>
              </div>

              <div className="sim-numbers-row">
                <div className="sim-number-box">
                  <span className="sim-num-label">Current</span>
                  <span className="sim-num-val">{simResult.current_attendance}%</span>
                </div>
                <div className="sim-arrow">→</div>
                <div className="sim-number-box projected-box">
                  <span className="sim-num-label">Projected</span>
                  <span className="sim-num-val highlight">{simResult.projected_attendance}%</span>
                </div>
              </div>

              {/* Detailed Breakdown */}
              <div className="sim-details-grid">
                <div className="detail-item">
                  <span>Current Attended / Total</span>
                  <strong>
                    {simResult.current_attended} / {simResult.current_total}
                  </strong>
                </div>
                <div className="detail-item">
                  <span>Simulated Adds</span>
                  <strong className="accent-add">
                    +{simResult.simulated_present} Present, +{simResult.simulated_absent} Absent
                  </strong>
                </div>
                <div className="detail-item">
                  <span>Final Projected Attended</span>
                  <strong>{simResult.final_attended}</strong>
                </div>
                <div className="detail-item">
                  <span>Final Projected Total</span>
                  <strong>{simResult.final_total}</strong>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================
          MODE 2: PLAN LEAVE MODE
          ======================================================== */}
      {leaveMode && (
        <div className="leave-plan-panel">
          <div className="leave-status-row">
            <span className="leave-count-label">
              Selected Leave Days: <strong>{selectedLeaveDates.length}</strong>
            </span>
            {selectedLeaveDates.length > 0 && (
              <button
                type="button"
                className="clear-link-btn"
                onClick={handleClearLeaveDays}
              >
                Clear Selected Days
              </button>
            )}
          </div>

          {selectedLeaveDates.length > 0 && (
            <div className="selected-leave-chips">
              {selectedLeaveDates.sort().map((dStr) => (
                <span key={dStr} className="leave-date-chip">
                  {formatSelectedDateHeader(dStr)}
                  <button
                    type="button"
                    className="chip-remove-btn"
                    onClick={() => handleDateClick(dStr)}
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          )}

          <div className="planner-actions-row">
            <button
              type="button"
              className="primary-btn calculate-btn alert-leave-btn"
              onClick={handleCalculateLeave}
              disabled={leaveCalculating || selectedLeaveDates.length === 0}
            >
              {leaveCalculating ? "Calculating..." : "Calculate Leave Impact"}
            </button>
          </div>

          {/* Leave Result Card */}
          {leaveResult && (
            <div className="simulation-result-card leave-impact-card">
              <div className="sim-result-head">
                <span className="res-badge">Leave Impact</span>
                <span className="change-tag negative-change">
                  {leaveResult.change >= 0 ? `+${leaveResult.change}%` : `${leaveResult.change}%`}
                </span>
              </div>

              <div className="sim-numbers-row">
                <div className="sim-number-box">
                  <span className="sim-num-label">Current</span>
                  <span className="sim-num-val">{leaveResult.current_attendance}%</span>
                </div>
                <div className="sim-arrow">→</div>
                <div className="sim-number-box projected-box">
                  <span className="sim-num-label">Projected</span>
                  <span className="sim-num-val highlight alert-val">
                    {leaveResult.projected_attendance}%
                  </span>
                </div>
              </div>

              <div className="sim-details-grid">
                <div className="detail-item">
                  <span>Selected Leave Days</span>
                  <strong>{leaveResult.selected_leave_days}</strong>
                </div>
                <div className="detail-item">
                  <span>Classes Missed</span>
                  <strong className="accent-missed">{leaveResult.classes_missed}</strong>
                </div>
                <div className="detail-item">
                  <span>Final Attended</span>
                  <strong>{leaveResult.final_attended}</strong>
                </div>
                <div className="detail-item">
                  <span>Final Total</span>
                  <strong>{leaveResult.final_total}</strong>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AttendancePlanner;
