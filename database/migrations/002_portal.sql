-- Add Under Review without changing existing status labels or their enum order.
-- The migration runner checks COLUMN_TYPE before applying this statement again.
USE campus_opportunity_planner;
ALTER TABLE applications MODIFY application_status
 ENUM('saved','preparing','applied','shortlisted','selected','rejected','withdrawn','under_review')
 NOT NULL DEFAULT 'saved';
