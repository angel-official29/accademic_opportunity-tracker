USE campus_opportunity_planner;


INSERT IGNORE INTO departments
    (department_code, department_name)
VALUES
    ('CSE', 'Computer Science and Engineering'),
    ('CSE-IOT-AI', 'CSE with IoT and Artificial Intelligence'),
    ('ECE', 'Electronics and Communication Engineering'),
    ('ME', 'Mechanical Engineering'),
    ('CE', 'Civil Engineering'),
    ('BBA', 'Bachelor of Business Administration');


INSERT IGNORE INTO opportunity_categories
    (category_name, description)
VALUES
    ('Internship', 'Industry or academic internship opportunities'),
    ('Scholarship', 'Financial assistance and merit scholarships'),
    ('Hackathon', 'Technology and problem-solving competitions'),
    ('Research', 'Research projects and assistantship opportunities'),
    ('Competition', 'Academic, technical and innovation competitions'),
    ('Fellowship', 'Structured learning and professional fellowships');


INSERT IGNORE INTO skills
    (skill_name, skill_category)
VALUES
    ('Python', 'Programming'),
    ('SQL', 'Database'),
    ('Java', 'Programming'),
    ('C++', 'Programming'),
    ('Machine Learning', 'Artificial Intelligence'),
    ('Internet of Things', 'IoT'),
    ('Data Analysis', 'Analytics'),
    ('Web Development', 'Development'),
    ('Communication', 'Professional'),
    ('Research Writing', 'Research'),
    ('Cloud Computing', 'Cloud'),
    ('UI/UX Design', 'Design');


INSERT IGNORE INTO document_types
    (document_name, description)
VALUES
    ('Resume', 'Updated resume or curriculum vitae'),
    ('NOC', 'No Objection Certificate from the university'),
    ('Identity Card', 'Valid university identity card'),
    ('Marksheet', 'Latest academic marksheet'),
    ('Cover Letter', 'Application-specific cover letter'),
    ('Statement of Purpose', 'Statement explaining interest and suitability'),
    ('Portfolio', 'Collection of relevant work or projects'),
    ('Recommendation Letter', 'Recommendation from faculty or mentor');