-- Additive only: existing tables and records are preserved.
USE campus_opportunity_planner;
CREATE TABLE IF NOT EXISTS auth_sessions (
 session_hash CHAR(64) PRIMARY KEY, user_id INT NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 expires_at DATETIME NOT NULL, revoked_at DATETIME NULL,
 FOREIGN KEY(user_id) REFERENCES users(user_id), INDEX idx_auth_user_expiry(user_id,expires_at)
);
CREATE TABLE IF NOT EXISTS security_rate_limits (
 bucket_key CHAR(64) PRIMARY KEY, window_start BIGINT NOT NULL,
 hits INT NOT NULL DEFAULT 0, CHECK(hits>=0), INDEX idx_rate_window(window_start)
);
CREATE TRIGGER IF NOT EXISTS audit_history_no_update
 BEFORE UPDATE ON application_status_history FOR EACH ROW
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Application history is append-only';
CREATE TRIGGER IF NOT EXISTS audit_history_no_delete
 BEFORE DELETE ON application_status_history FOR EACH ROW
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Application history is append-only';
