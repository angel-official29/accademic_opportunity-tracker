CREATE DATABASE IF NOT EXISTS campus_opportunity_planner
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE campus_opportunity_planner;


CREATE TABLE IF NOT EXISTS departments (
    department_id INT AUTO_INCREMENT PRIMARY KEY,
    department_code VARCHAR(20) NOT NULL UNIQUE,
    department_name VARCHAR(100) NOT NULL UNIQUE
);


CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'admin') NOT NULL DEFAULT 'student',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS student_profiles (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    university_uid VARCHAR(30) NOT NULL UNIQUE,
    department_id INT NOT NULL,
    current_year TINYINT NOT NULL,
    cgpa DECIMAL(4,2),
    graduation_year YEAR,
    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    FOREIGN KEY (department_id)
        REFERENCES departments(department_id),
    CHECK (current_year BETWEEN 1 AND 4),
    CHECK (cgpa IS NULL OR cgpa BETWEEN 0 AND 10)
);CREATE TABLE IF NOT EXISTS skills (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(80) NOT NULL UNIQUE,
    skill_category VARCHAR(60)
);


CREATE TABLE IF NOT EXISTS student_skills (
    student_id INT NOT NULL,
    skill_id INT NOT NULL,
    proficiency_level ENUM(
        'beginner',
        'intermediate',
        'advanced'
    ) NOT NULL DEFAULT 'beginner',
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (student_id, skill_id),
    FOREIGN KEY (student_id)
        REFERENCES student_profiles(student_id)
        ON DELETE CASCADE,
    FOREIGN KEY (skill_id)
        REFERENCES skills(skill_id)
        ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS organizations (
    organization_id INT AUTO_INCREMENT PRIMARY KEY,
    organization_name VARCHAR(150) NOT NULL UNIQUE,
    organization_type ENUM(
        'company',
        'university',
        'government',
        'ngo',
        'club',
        'other'
    ) NOT NULL,
    website_url VARCHAR(255),
    contact_email VARCHAR(120),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS opportunity_categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(60) NOT NULL UNIQUE,
    description VARCHAR(255)
);


CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    category_id INT NOT NULL,
    title VARCHAR(180) NOT NULL,
    description TEXT NOT NULL,
    mode ENUM('onsite', 'remote', 'hybrid') NOT NULL,
    location VARCHAR(150),
    stipend DECIMAL(10,2),
    application_url VARCHAR(500),
    application_deadline DATETIME NOT NULL,
    start_date DATE,
    end_date DATE,
    is_campus_managed BOOLEAN NOT NULL DEFAULT FALSE,
    listing_status ENUM(
        'draft',
        'published',
        'closed',
        'cancelled'
    ) NOT NULL DEFAULT 'draft',
    created_by INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(organization_id),

    FOREIGN KEY (category_id)
        REFERENCES opportunity_categories(category_id),

    FOREIGN KEY (created_by)
        REFERENCES users(user_id),

    CHECK (stipend IS NULL OR stipend >= 0),
    CHECK (
        end_date IS NULL
        OR start_date IS NULL
        OR end_date >= start_date
    )
);
CREATE TABLE IF NOT EXISTS eligibility_requirements (
    opportunity_id INT PRIMARY KEY,
    minimum_cgpa DECIMAL(4,2) NOT NULL DEFAULT 0,
    minimum_year TINYINT NOT NULL DEFAULT 1,
    maximum_year TINYINT NOT NULL DEFAULT 4,
    all_departments_allowed BOOLEAN NOT NULL DEFAULT TRUE,

    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(opportunity_id)
        ON DELETE CASCADE,

    CHECK (minimum_cgpa BETWEEN 0 AND 10),
    CHECK (minimum_year BETWEEN 1 AND 4),
    CHECK (maximum_year BETWEEN 1 AND 4),
    CHECK (minimum_year <= maximum_year)
);


CREATE TABLE IF NOT EXISTS opportunity_departments (
    opportunity_id INT NOT NULL,
    department_id INT NOT NULL,

    PRIMARY KEY (opportunity_id, department_id),

    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(opportunity_id)
        ON DELETE CASCADE,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS opportunity_skills (
    opportunity_id INT NOT NULL,
    skill_id INT NOT NULL,
    requirement_type ENUM(
        'required',
        'preferred'
    ) NOT NULL,

    PRIMARY KEY (opportunity_id, skill_id),

    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(opportunity_id)
        ON DELETE CASCADE,

    FOREIGN KEY (skill_id)
        REFERENCES skills(skill_id)
        ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    opportunity_id INT NOT NULL,
    application_status ENUM(
        'saved',
        'preparing',
        'applied',
        'shortlisted',
        'selected',
        'rejected',
        'withdrawn'
    ) NOT NULL DEFAULT 'saved',
    applied_at DATETIME,
    external_reference VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE (student_id, opportunity_id),

    FOREIGN KEY (student_id)
        REFERENCES student_profiles(student_id)
        ON DELETE CASCADE,

    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(opportunity_id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS application_status_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    old_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    changed_by INT NOT NULL,
    change_note VARCHAR(255),
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (application_id)
        REFERENCES applications(application_id)
        ON DELETE CASCADE,

    FOREIGN KEY (changed_by)
        REFERENCES users(user_id)
);
CREATE TABLE IF NOT EXISTS document_types (
    document_type_id INT AUTO_INCREMENT PRIMARY KEY,
    document_name VARCHAR(80) NOT NULL UNIQUE,
    description VARCHAR(255)
);


CREATE TABLE IF NOT EXISTS opportunity_documents (
    opportunity_id INT NOT NULL,
    document_type_id INT NOT NULL,
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,

    PRIMARY KEY (opportunity_id, document_type_id),

    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(opportunity_id)
        ON DELETE CASCADE,

    FOREIGN KEY (document_type_id)
        REFERENCES document_types(document_type_id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS application_documents (
    application_id INT NOT NULL,
    document_type_id INT NOT NULL,
    document_status ENUM(
        'pending',
        'ready',
        'submitted',
        'approved',
        'needs_update'
    ) NOT NULL DEFAULT 'pending',
    file_name VARCHAR(255),
    notes VARCHAR(255),
    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (application_id, document_type_id),

    FOREIGN KEY (application_id)
        REFERENCES applications(application_id)
        ON DELETE CASCADE,

    FOREIGN KEY (document_type_id)
        REFERENCES document_types(document_type_id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS preparation_tasks (
    task_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    task_title VARCHAR(150) NOT NULL,
    due_date DATETIME,
    task_status ENUM(
        'pending',
        'in_progress',
        'completed'
    ) NOT NULL DEFAULT 'pending',
    completed_at DATETIME,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (application_id, task_title),

    FOREIGN KEY (application_id)
        REFERENCES applications(application_id)
        ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS student_interests (
    student_id INT NOT NULL,
    category_id INT NOT NULL,
    interest_level ENUM(
        'low',
        'medium',
        'high'
    ) NOT NULL DEFAULT 'medium',

    PRIMARY KEY (student_id, category_id),

    FOREIGN KEY (student_id)
        REFERENCES student_profiles(student_id)
        ON DELETE CASCADE,

    FOREIGN KEY (category_id)
        REFERENCES opportunity_categories(category_id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    notification_type ENUM(
        'deadline',
        'application_status',
        'preparation_task',
        'system'
    ) NOT NULL,
    title VARCHAR(150) NOT NULL,
    message VARCHAR(500) NOT NULL,
    opportunity_id INT,
    application_id INT,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(opportunity_id)
        ON DELETE SET NULL,

    FOREIGN KEY (application_id)
        REFERENCES applications(application_id)
        ON DELETE SET NULL
);