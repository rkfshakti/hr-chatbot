"""Write sample resumes for testing"""

resumes = {
    '/tmp/resume_alice.txt': """Alice Johnson
Senior Python Developer
Email: alice@example.com

SUMMARY
Senior Python developer with 7 years of experience. Expert in FastAPI, PostgreSQL, Docker, and AWS. Led teams of 5+ engineers.

SKILLS
Python, FastAPI, Django, PostgreSQL, Redis, Docker, Kubernetes, AWS, REST APIs, pytest, SQLAlchemy, CI/CD

EXPERIENCE
Senior Software Engineer - TechCorp (2020-2024): Built microservices handling 50M req/day using FastAPI. PostgreSQL optimization, AWS ECS Docker CI/CD.
Software Engineer - StartupXY (2017-2020): Python REST APIs, 500K daily users.

EDUCATION: B.S. Computer Science, University of Chicago 2017
CERTIFICATIONS: AWS Certified Developer Associate
""",
    '/tmp/resume_bob.txt': """Bob Martinez
Full Stack Software Engineer
Email: bob@example.com

SUMMARY
Full stack engineer with 4 years experience. Python, JavaScript, React. Some FastAPI and PostgreSQL experience. Eager learner.

SKILLS
Python, JavaScript, React, Node.js, FastAPI, PostgreSQL, MySQL, Docker basic, AWS Lambda

EXPERIENCE
Software Engineer - WebAgency (2021-2024): React frontends, Node.js and Python backends, PostgreSQL databases.
Junior Developer - Freelance (2020-2021): PHP and basic Python scripting.

EDUCATION: B.S. Information Technology, State University 2020
""",
    '/tmp/resume_carol.txt': """Carol Chen
Staff Software Engineer
Email: carol.chen@example.com

SUMMARY
12 years building distributed systems at scale. Python, Go, Kubernetes, AWS expert. Led org-wide microservices migration. AWS Certified Solutions Architect Professional and CKA certified.

SKILLS
Python, Go, FastAPI, gRPC, PostgreSQL, MongoDB, Redis, Kafka, Kubernetes, Docker, AWS all services, Terraform, Prometheus, Grafana, CI/CD, SRE

EXPERIENCE
Staff Engineer - MegaCorp (2018-2024): Distributed payment processing system 1B transactions/year. Kubernetes migration for 200+ services saving 2M/year. ML feature pipelines Python and Kafka.
Senior Engineer - CloudCo (2014-2018): Multi-region AWS infrastructure 99.99% uptime. Data warehouse on Redshift.
Software Engineer - FinTechStartup (2012-2014): Python Django PostgreSQL financial data processing.

EDUCATION: M.S. Computer Science, Stanford University 2012
CERTIFICATIONS: AWS Certified Solutions Architect Professional, Certified Kubernetes Administrator CKA
""",
}

for path, content in resumes.items():
    with open(path, 'w') as f:
        f.write(content)
    print(f'Created: {path}')

print("Done!")
