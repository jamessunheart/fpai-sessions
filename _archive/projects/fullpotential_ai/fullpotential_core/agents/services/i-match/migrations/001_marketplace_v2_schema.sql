-- I MATCH Marketplace V2 Schema Migration
-- Adds support for multi-category marketplace + POTENTIAL (POT) token system
-- Created: 2025-11-15
-- Migration: 001_marketplace_v2_schema

-- ============================================================================
-- PART 1: NEW TABLES FOR MARKETPLACE V2
-- ============================================================================

-- USERS TABLE (Unified identity across platform)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    password_hash VARCHAR(255),  -- For future auth system
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- POT Token balances
    pot_balance INTEGER DEFAULT 0,
    total_pot_earned INTEGER DEFAULT 0,
    total_pot_spent INTEGER DEFAULT 0,
    total_pot_burned INTEGER DEFAULT 0,

    -- Account metadata
    account_type VARCHAR(20) DEFAULT 'seeker',  -- 'seeker', 'provider', 'both'
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,

    -- Reputation
    rating_average DECIMAL(3,2) DEFAULT 0.00,
    rating_count INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'suspended', 'deleted'

    -- Tracking
    last_login_at TIMESTAMP,
    login_count INTEGER DEFAULT 0
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_account_type ON users(account_type);

-- CATEGORIES TABLE (Marketplace categories)
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,  -- 'financial_advisors', 'career_coaches'
    display_name VARCHAR(255) NOT NULL,  -- 'Financial Advisors', 'Career Coaches'
    description TEXT,
    icon VARCHAR(50),  -- Emoji or icon identifier

    -- Launch tracking
    launched_at TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,

    -- Economics
    commission_rate DECIMAL(5,2) DEFAULT 20.00,  -- % commission on deals

    -- Matching configuration
    matching_criteria JSON,  -- Category-specific criteria and weights
    intake_questions JSON,   -- Questions to ask seekers
    profile_fields JSON,     -- Required provider profile fields

    -- Metrics
    provider_count INTEGER DEFAULT 0,
    seeker_count INTEGER DEFAULT 0,
    match_count INTEGER DEFAULT 0,
    engagement_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_active ON categories(active);
CREATE INDEX idx_categories_name ON categories(name);

-- SEEKERS TABLE (People looking for matches)
CREATE TABLE IF NOT EXISTS seekers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),

    -- Core needs
    needs_description TEXT NOT NULL,
    budget_min INTEGER,
    budget_max INTEGER,
    location VARCHAR(255),

    -- Preferences
    format_preference VARCHAR(20),  -- 'in-person', 'remote', 'either'
    urgency VARCHAR(20),  -- 'immediate', 'this_week', 'this_month', 'flexible'

    -- Category-specific data
    additional_criteria JSON,

    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'matched', 'engaged', 'completed', 'inactive'

    -- Tracking
    match_count INTEGER DEFAULT 0,
    engagement_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_seekers_user_id ON seekers(user_id);
CREATE INDEX idx_seekers_category_id ON seekers(category_id);
CREATE INDEX idx_seekers_status ON seekers(status);

-- PROVIDERS TABLE (Service providers across categories)
CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),

    -- Business info
    business_name VARCHAR(255),
    bio TEXT,
    website VARCHAR(500),
    linkedin_url VARCHAR(500),

    -- Expertise
    specialties JSON,  -- Array of specialization strings
    years_experience INTEGER,
    certifications JSON,  -- Array of certification objects
    languages JSON,  -- Array of language strings

    -- Pricing
    pricing_min INTEGER,
    pricing_max INTEGER,
    pricing_model VARCHAR(50),  -- 'hourly', 'project', 'retainer', 'commission', 'subscription'

    -- Logistics
    location VARCHAR(255),
    formats_offered JSON,  -- ['in-person', 'remote', 'hybrid']
    availability VARCHAR(100),  -- 'full-time', 'part-time', 'weekends', 'evenings'

    -- Category-specific profile
    additional_profile JSON,

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'active', 'suspended', 'inactive'
    approved_at TIMESTAMP,

    -- Premium features
    boosted_until TIMESTAMP,  -- Profile boost expiration
    featured_until TIMESTAMP,  -- Featured listing expiration
    verified_badge BOOLEAN DEFAULT FALSE,

    -- Tracking
    lead_count INTEGER DEFAULT 0,
    engagement_count INTEGER DEFAULT 0,
    response_count INTEGER DEFAULT 0,
    avg_response_time_hours DECIMAL(6,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_providers_user_id ON providers(user_id);
CREATE INDEX idx_providers_category_id ON providers(category_id);
CREATE INDEX idx_providers_status ON providers(status);
CREATE INDEX idx_providers_boosted ON providers(boosted_until);

-- MATCHES TABLE (AI-generated seeker-provider matches)
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seeker_id INTEGER NOT NULL REFERENCES seekers(id) ON DELETE CASCADE,
    provider_id INTEGER NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),

    -- Match quality
    match_score DECIMAL(5,2) NOT NULL,  -- 0.00 to 100.00
    match_reasoning TEXT,  -- AI-generated explanation (2-3 sentences)
    criteria_breakdown JSON,  -- Scores for each matching criterion
    strengths JSON,  -- Array of strength strings
    concerns JSON,  -- Array of potential concern strings

    -- Status tracking
    status VARCHAR(20) DEFAULT 'suggested',  -- 'suggested', 'viewed', 'contacted', 'engaged', 'declined', 'expired'

    -- Engagement tracking
    viewed_at TIMESTAMP,
    contacted_at TIMESTAMP,
    engaged_at TIMESTAMP,
    declined_at TIMESTAMP,
    decline_reason TEXT,

    -- Metadata
    match_batch_id VARCHAR(100),  -- Group matches from same request
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_matches_seeker_id ON matches(seeker_id);
CREATE INDEX idx_matches_provider_id ON matches(provider_id);
CREATE INDEX idx_matches_category_id ON matches(category_id);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_score ON matches(match_score DESC);

-- ENGAGEMENTS TABLE (Confirmed seeker-provider relationships)
CREATE TABLE IF NOT EXISTS engagements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    seeker_id INTEGER NOT NULL REFERENCES seekers(id) ON DELETE CASCADE,
    provider_id INTEGER NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),

    -- Deal economics (USD)
    deal_value_usd DECIMAL(10,2) NOT NULL,
    commission_rate DECIMAL(5,2) NOT NULL,  -- % commission (usually 20.00)
    commission_usd DECIMAL(10,2) NOT NULL,  -- Calculated commission amount

    -- Deal economics (POT)
    commission_pot INTEGER DEFAULT 0,  -- 5% of deal value in POT (bonus for provider)
    seeker_bonus_pot INTEGER DEFAULT 100,  -- POT bonus for seeker completing engagement

    -- Status
    status VARCHAR(20) DEFAULT 'confirmed',  -- 'confirmed', 'active', 'completed', 'cancelled'

    -- Lifecycle
    confirmed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT,

    -- Invoicing
    invoice_sent_at TIMESTAMP,
    invoice_due_at TIMESTAMP,
    payment_received_at TIMESTAMP,
    payment_amount DECIMAL(10,2),

    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_engagements_match_id ON engagements(match_id);
CREATE INDEX idx_engagements_seeker_id ON engagements(seeker_id);
CREATE INDEX idx_engagements_provider_id ON engagements(provider_id);
CREATE INDEX idx_engagements_category_id ON engagements(category_id);
CREATE INDEX idx_engagements_status ON engagements(status);

-- RATINGS TABLE (Reviews from both parties)
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id INTEGER NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    from_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Rating details
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    would_recommend BOOLEAN,

    -- Dimensions (optional detailed ratings)
    expertise_rating INTEGER CHECK (expertise_rating >= 1 AND expertise_rating <= 5),
    communication_rating INTEGER CHECK (communication_rating >= 1 AND communication_rating <= 5),
    professionalism_rating INTEGER CHECK (professionalism_rating >= 1 AND professionalism_rating <= 5),
    value_rating INTEGER CHECK (value_rating >= 1 AND value_rating <= 5),

    -- Rewards
    pot_earned INTEGER DEFAULT 10,  -- POT reward for leaving rating

    -- Metadata
    public BOOLEAN DEFAULT TRUE,  -- Can be displayed publicly
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ratings_engagement_id ON ratings(engagement_id);
CREATE INDEX idx_ratings_from_user ON ratings(from_user_id);
CREATE INDEX idx_ratings_to_user ON ratings(to_user_id);
CREATE INDEX idx_ratings_public ON ratings(public);

-- POT_TRANSACTIONS TABLE (Internal currency ledger)
CREATE TABLE IF NOT EXISTS pot_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Transaction details
    amount INTEGER NOT NULL,  -- Positive = earned/received, Negative = spent/burned
    transaction_type VARCHAR(20) NOT NULL,  -- 'earn', 'spend', 'burn', 'redeem', 'transfer'
    category VARCHAR(50) NOT NULL,  -- Specific reason (see categories below)
    description TEXT,

    -- Reference to related record
    reference_type VARCHAR(50),  -- 'engagement', 'rating', 'profile', 'referral', etc.
    reference_id INTEGER,

    -- Balance tracking
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,

    -- Metadata
    metadata JSON,  -- Additional context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pot_transactions_user_id ON pot_transactions(user_id);
CREATE INDEX idx_pot_transactions_type ON pot_transactions(transaction_type);
CREATE INDEX idx_pot_transactions_category ON pot_transactions(category);
CREATE INDEX idx_pot_transactions_created_at ON pot_transactions(created_at);

-- Transaction Categories Reference:
-- EARN: 'profile_creation', 'first_response', 'engagement_bonus', 'rating_bonus', 'referral', 'content', 'daily_login'
-- SPEND: 'premium_match', 'rush_match', 'profile_boost', 'verified_badge', 'featured_listing', 'analytics', 'support'
-- BURN: Automatic when POT is spent on platform features
-- REDEEM: Convert POT to USD (with 20% fee)

-- REFERRALS TABLE (Track referral program)
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referred_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Referral details
    referral_type VARCHAR(20) NOT NULL,  -- 'seeker', 'provider'
    referral_code VARCHAR(50),  -- Unique code used (optional)

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'completed', 'rewarded', 'cancelled'

    -- Rewards
    pot_bonus INTEGER,  -- 250 for seeker, 500 for provider

    -- Lifecycle
    completed_at TIMESTAMP,  -- When referred user completed qualifying action
    rewarded_at TIMESTAMP,   -- When POT was awarded

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX idx_referrals_referred_id ON referrals(referred_id);
CREATE INDEX idx_referrals_status ON referrals(status);

-- CONTENT TABLE (User-generated content for rewards)
CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Content details
    content_type VARCHAR(50) NOT NULL,  -- 'guide', 'video', 'testimonial', 'success_story', 'article'
    title VARCHAR(500) NOT NULL,
    body TEXT,
    url VARCHAR(1000),  -- If external content

    -- Categorization
    category_id INTEGER REFERENCES categories(id),  -- Associated category (optional)
    tags JSON,  -- Array of tag strings

    -- Review and approval
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'published', 'rejected'
    reviewer_notes TEXT,
    approved_by INTEGER REFERENCES users(id),

    -- Rewards
    pot_earned INTEGER DEFAULT 0,

    -- Lifecycle
    approved_at TIMESTAMP,
    published_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_user_id ON content(user_id);
CREATE INDEX idx_content_status ON content(status);
CREATE INDEX idx_content_type ON content(content_type);

-- ============================================================================
-- PART 2: SEED DATA - INITIAL CATEGORIES
-- ============================================================================

-- Category 1: Financial Advisors (already deployed)
INSERT OR IGNORE INTO categories (
    name,
    display_name,
    description,
    icon,
    launched_at,
    active,
    commission_rate,
    matching_criteria
) VALUES (
    'financial_advisors',
    'Financial Advisors',
    'Certified financial advisors specializing in wealth management, tax optimization, retirement planning, and investment strategies.',
    '💰',
    CURRENT_TIMESTAMP,
    TRUE,
    20.00,
    json('{"expertise_match": 30, "values_alignment": 20, "communication_style": 15, "logistics_fit": 10, "pricing_alignment": 10, "track_record": 10, "certification_match": 5}')
);

-- Category 2: Career Coaches (Phase 2)
INSERT OR IGNORE INTO categories (
    name,
    display_name,
    description,
    icon,
    active,
    commission_rate,
    matching_criteria
) VALUES (
    'career_coaches',
    'Career Coaches',
    'Professional career coaches helping with job transitions, promotions, career pivots, and leadership development.',
    '🎯',
    FALSE,
    20.00,
    json('{"expertise_match": 35, "industry_knowledge": 20, "communication_style": 15, "track_record": 15, "logistics_fit": 10, "pricing_alignment": 5}')
);

-- Category 3: Therapists & Counselors (Phase 2)
INSERT OR IGNORE INTO categories (
    name,
    display_name,
    description,
    icon,
    active,
    commission_rate,
    matching_criteria
) VALUES (
    'therapists',
    'Therapists & Counselors',
    'Licensed therapists and counselors specializing in mental health, personal growth, and emotional wellness.',
    '🧠',
    FALSE,
    15.00,
    json('{"expertise_match": 35, "modality_fit": 20, "communication_style": 20, "logistics_fit": 15, "pricing_alignment": 10}')
);

-- Category 4: Fitness Trainers (Phase 2)
INSERT OR IGNORE INTO categories (
    name,
    display_name,
    description,
    icon,
    active,
    commission_rate,
    matching_criteria
) VALUES (
    'fitness_trainers',
    'Fitness Trainers',
    'Certified personal trainers helping with fitness goals, strength training, weight loss, and athletic performance.',
    '💪',
    FALSE,
    20.00,
    json('{"expertise_match": 30, "training_philosophy": 20, "communication_style": 15, "logistics_fit": 15, "pricing_alignment": 10, "track_record": 10}')
);

-- ============================================================================
-- PART 3: VIEWS FOR CONVENIENCE
-- ============================================================================

-- View: Active providers with user details
CREATE VIEW IF NOT EXISTS active_providers_view AS
SELECT
    p.id,
    p.user_id,
    u.name,
    u.email,
    p.business_name,
    p.category_id,
    c.display_name AS category_name,
    p.bio,
    p.specialties,
    p.pricing_min,
    p.pricing_max,
    p.location,
    u.rating_average,
    u.rating_count,
    p.lead_count,
    p.engagement_count,
    p.status,
    p.boosted_until,
    p.created_at
FROM providers p
JOIN users u ON p.user_id = u.id
JOIN categories c ON p.category_id = c.id
WHERE p.status = 'active';

-- View: Active seekers with user details
CREATE VIEW IF NOT EXISTS active_seekers_view AS
SELECT
    s.id,
    s.user_id,
    u.name,
    u.email,
    s.category_id,
    c.display_name AS category_name,
    s.needs_description,
    s.budget_min,
    s.budget_max,
    s.location,
    s.format_preference,
    s.urgency,
    s.status,
    s.created_at
FROM seekers s
JOIN users u ON s.user_id = u.id
JOIN categories c ON s.category_id = c.id
WHERE s.status = 'active';

-- View: POT token economy stats
CREATE VIEW IF NOT EXISTS pot_economy_stats AS
SELECT
    (SELECT COUNT(*) FROM users WHERE pot_balance > 0) AS users_with_pot,
    (SELECT SUM(pot_balance) FROM users) AS total_pot_in_circulation,
    (SELECT SUM(total_pot_earned) FROM users) AS total_pot_earned_all_time,
    (SELECT SUM(total_pot_spent) FROM users) AS total_pot_spent_all_time,
    (SELECT SUM(total_pot_burned) FROM users) AS total_pot_burned_all_time,
    (SELECT COUNT(*) FROM pot_transactions WHERE created_at > datetime('now', '-7 days')) AS transactions_last_7_days,
    (SELECT SUM(amount) FROM pot_transactions WHERE transaction_type = 'earn' AND created_at > datetime('now', '-7 days')) AS pot_earned_last_7_days,
    (SELECT SUM(ABS(amount)) FROM pot_transactions WHERE transaction_type = 'spend' AND created_at > datetime('now', '-7 days')) AS pot_spent_last_7_days;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
