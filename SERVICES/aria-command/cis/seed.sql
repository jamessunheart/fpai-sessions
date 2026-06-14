-- Seed data for CIS

-- Default user (James)
INSERT OR IGNORE INTO users (id, external_id, name, timezone) 
VALUES ('james', '1759822075', 'James', 'America/Los_Angeles');

-- Default channel (Telegram)
INSERT OR IGNORE INTO user_channels (id, user_id, channel, channel_address, priority, active, verified)
VALUES ('james-telegram', 'james', 'telegram', '1759822075', 1, 1, 1);

-- MVP Actions

-- STABILIZE actions
INSERT OR IGNORE INTO actions (id, action_key, category, name, instruction, duration_seconds, effective_states, min_intensity, max_intensity)
VALUES 
('a1', 'breathe_3', 'stabilize', '3 Slow Breaths', 
 'Take 3 slow breaths. Exhale longer than inhale. 30 seconds total.', 
 30, '["busy", "overloaded", "stuck"]', 3, 5);

INSERT OR IGNORE INTO actions (id, action_key, category, name, instruction, duration_seconds, effective_states, min_intensity, max_intensity)
VALUES 
('a2', 'breathe_1', 'stabilize', '1 Deep Breath', 
 'One breath. 4 seconds in, 6 seconds out.', 
 10, '["busy", "overloaded"]', 2, 4);

INSERT OR IGNORE INTO actions (id, action_key, category, name, instruction, duration_seconds, effective_states, min_intensity, max_intensity)
VALUES 
('a3', 'pause_2min', 'stabilize', '2-Minute Pause', 
 'Step away from screen for 2 minutes. Look at something distant.', 
 120, '["overloaded", "stuck"]', 4, 5);

INSERT OR IGNORE INTO actions (id, action_key, category, name, instruction, duration_seconds, effective_states, min_intensity, max_intensity)
VALUES 
('a4', 'ground_check', 'stabilize', 'Ground Check', 
 'Feet on floor. Name 3 things you see. 20 seconds.', 
 20, '["overloaded", "stuck"]', 4, 5);

INSERT OR IGNORE INTO actions (id, action_key, category, name, instruction, duration_seconds, effective_states, min_intensity, max_intensity)
VALUES 
('a5', 'water', 'stabilize', 'Drink Water', 
 'Get water. Drink slowly. Return.', 
 60, '["busy", "overloaded", "stuck"]', 2, 5);

-- DISRUPT actions
INSERT OR IGNORE INTO actions (id, action_key, category, name, instruction, duration_seconds, effective_states, min_intensity, max_intensity)
VALUES 
('a6', 'change_location', 'disrupt', 'Change Location', 
 'Move to a different room or space for 5 minutes.', 
 300, '["stuck"]', 3, 5);

INSERT OR IGNORE INTO actions (id, action_key, category, name, instruction, duration_seconds, effective_states, min_intensity, max_intensity)
VALUES 
('a7', 'name_the_stuck', 'disrupt', 'Name the Stuck', 
 'Write one sentence: what exactly are you stuck on?', 
 60, '["stuck"]', 2, 4);

INSERT OR IGNORE INTO actions (id, action_key, category, name, instruction, duration_seconds, effective_states, min_intensity, max_intensity)
VALUES 
('a8', 'smallest_next', 'disrupt', 'Smallest Next Action', 
 'What is the smallest possible next action? Do only that.', 
 30, '["stuck", "overloaded"]', 3, 5);

-- EXECUTE actions
INSERT OR IGNORE INTO actions (id, action_key, category, name, instruction, duration_seconds, effective_states, min_intensity, max_intensity)
VALUES 
('a9', 'clear_one_task', 'execute', 'Clear One Task', 
 'Pick the smallest open task. Finish it or kill it. Reply when done.', 
 300, '["busy", "stuck"]', 2, 4);

INSERT OR IGNORE INTO actions (id, action_key, category, name, instruction, duration_seconds, effective_states, min_intensity, max_intensity)
VALUES 
('a10', 'delegate_one', 'coordinate', 'Delegate One Thing', 
 'Identify one thing you are holding that someone else could do. Hand it off.', 
 180, '["overloaded"]', 4, 5);

-- Default user state (conservative)
INSERT OR IGNORE INTO user_state (id, user_id, state, intensity, confidence, source)
VALUES ('james-state', 'james', 'calm', 2, 'low', 'default');








