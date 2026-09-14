import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import BottomNav from "../components/BottomNav";

function Leaderboard() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [userParticipating, setUserParticipating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      navigate("/");
      return;
    }

    api
      .get("/leaderboard/")
      .then((res) => {
        setLeaderboard(res.data.leaderboard || []);
        setUserParticipating(res.data.user_participating || false);
        setError("");
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to load leaderboard.");
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  if (loading) {
    return (
      <div className="mobile-page-container flex-center">
        <div className="spinner"></div>
        <p className="loading-caption">Fetching rankings...</p>
      </div>
    );
  }

  const topThree = leaderboard.slice(0, 3);
  const remaining = leaderboard.slice(3);

  return (
    <div className="mobile-page-container">
      <header className="mobile-top-header">
        <div>
          <h1 className="user-title">Leaderboard</h1>
          <span className="sub-heading">Academic Streak & XP Rankings</span>
        </div>
      </header>

      {/* Opt-in banner if user is not participating */}
      {!userParticipating && (
        <div className="opt-in-banner">
          <div className="opt-in-info">
            <strong>You are currently anonymous</strong>
            <p>Opt in via your profile to earn badges and appear on the leaderboard.</p>
          </div>
          <button
            className="secondary-btn-small"
            onClick={() => navigate("/profile")}
          >
            Edit Profile
          </button>
        </div>
      )}

      {error && <div className="alert-message error">{error}</div>}

      {/* Top 3 Podium */}
      {topThree.length > 0 && (
        <div className="podium-container">
          {topThree[1] && (
            <div className="podium-spot rank-2">
              <div className="podium-badge">🥈 2nd</div>
              <div className="podium-nickname">{topThree[1].nickname}</div>
              <div className="podium-xp">{topThree[1].xp} XP</div>
              <div className="podium-lvl">Lvl {topThree[1].level}</div>
            </div>
          )}

          {topThree[0] && (
            <div className="podium-spot rank-1">
              <div className="podium-badge champion">👑 1st</div>
              <div className="podium-nickname">{topThree[0].nickname}</div>
              <div className="podium-xp">{topThree[0].xp} XP</div>
              <div className="podium-lvl">Lvl {topThree[0].level}</div>
            </div>
          )}

          {topThree[2] && (
            <div className="podium-spot rank-3">
              <div className="podium-badge">🥉 3rd</div>
              <div className="podium-nickname">{topThree[2].nickname}</div>
              <div className="podium-xp">{topThree[2].xp} XP</div>
              <div className="podium-lvl">Lvl {topThree[2].level}</div>
            </div>
          )}
        </div>
      )}

      {/* Full Leaderboard List */}
      <div className="leaderboard-list">
        {leaderboard.length === 0 ? (
          <div className="empty-state-card mini">
            <p>No students have opted into the leaderboard yet. Be the first!</p>
          </div>
        ) : (
          leaderboard.map((item) => {
            const isSelf = item.is_current_user;
            return (
              <div
                key={item.rank}
                className={`leaderboard-row ${isSelf ? "highlight-self" : ""}`}
              >
                <div className="rank-number-col">
                  {item.rank === 1 ? "🥇" : item.rank === 2 ? "🥈" : item.rank === 3 ? "🥉" : `#${item.rank}`}
                </div>

                <div className="user-info-col">
                  <div className="name-wrapper">
                    <span className="user-nickname">{item.nickname}</span>
                    {isSelf && <span className="self-tag">You</span>}
                  </div>
                  <span className="user-stats-sub">
                    Level {item.level} • 🔥 {item.current_streak} streak
                  </span>
                </div>

                <div className="xp-points-col">
                  <span className="xp-badge">{item.xp} XP</span>
                </div>
              </div>
            );
          })
        )}
      </div>

      <BottomNav />
    </div>
  );
}

export default Leaderboard;
