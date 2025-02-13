# Financial Data Assistant

![5321738902254_ pic](https://github.com/user-attachments/assets/44b747f9-0442-4f6a-a940-70e009b491ef)

![5311738902216_ pic](https://github.com/user-attachments/assets/3eb87885-70dc-4f6b-8eaa-98672aa91208)

**Author**: Xiaoting Kuang

**Development Tools**:
- Code Development: [Cursor](https://cursor.sh/) - The AI-first code editor
- AI Assistance: Claude (Anthropic) - For rapid development and problem-solving

A comprehensive financial data platform that aggregates and analyzes data from FDIC (Federal Deposit Insurance Corporation) and NCUA (National Credit Union Administration). The platform includes an automated data pipeline using Apache Airflow and a web interface with SQL querying capabilities.

![5331738902295_ pic](https://github.com/user-attachments/assets/eb939b35-863e-4d58-b97c-09375793a8a6)


## Features

- Automated data collection from FDIC and NCUA sources
- Daily data freshness checks and updates
- Interactive SQL query interface
- Pre-built analytics queries
- AI-powered chat interface for data exploration
- Comprehensive documentation and API reference

## System Requirements

- Python 3.11+
- PostgreSQL 13+
- Redis (for Airflow)
- Virtual environment management tool (venv recommended)

## Directory Structure

```
.
├── airflow/
│   ├── dags/
│   │   ├── refresh_financial_data_dag.py
│   │   ├── fdic_ingestion.py
│   │   └── ncua_ingestion.py
├── docs/
│   ├── architecture.md
│   ├── data_mechanics.md
│   └── technical_overview.md
├── prospects/
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── templates/
│   ├── base.html
│   ├── chat/
│   └── documentation/
└── manage.py
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/financial-data-assistant.git
cd financial-data-assistant
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (create .env file):
```bash
# Django settings
DEBUG=True
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database settings
DATABASE_URL=postgresql://user:password@localhost:5432/financial_db

# Airflow settings
AIRFLOW_HOME=/path/to/your/airflow
AIRFLOW__CORE__SQL_ALCHEMY_CONN=sqlite:////path/to/your/airflow/airflow.db
AIRFLOW__CORE__LOAD_EXAMPLES=False
```

5. Initialize the database:
```bash
python manage.py migrate
python manage.py createsuperuser
```

## Running the Application

### 1. Start Airflow Services

Initialize Airflow database (first time only):
```bash
airflow db init
```

Create Airflow user (first time only):
```bash
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin
```

Start Airflow services:
```bash
# Start the web server (in a separate terminal)
airflow webserver -p 8081

# Start the scheduler (in another separate terminal)
airflow scheduler
```

Airflow UI will be available at: http://localhost:8081

### 2. Start Django Development Server

```bash
python manage.py runserver 8000
```

The web application will be available at: http://localhost:8000

## Available URLs

- Main Application: http://localhost:8000
- Documentation: http://localhost:8000/docs/
- Chat Interface: http://localhost:8000/chat/
- Admin Interface: http://localhost:8000/admin/
- Airflow Interface: http://localhost:8081

## Data Pipeline

The Airflow DAG (`refresh_financial_data`) runs daily at 6 AM and performs the following tasks:
1. Checks FDIC website for new data
2. Checks NCUA website for new data
3. Generates a freshness report
4. Updates database if new data is available

## Development

### Running Tests
```bash
python manage.py test
```

### Code Style
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
flake8 .

# Run type checking
mypy .
```

## API Documentation

The application provides several API endpoints for data access:

- `/api/institutions/`: List of financial institutions
- `/api/stats/`: Quarterly statistics
- `/chat/query/`: Natural language query endpoint
- `/chat/sql/`: SQL query endpoint

## Acknowledgments

- FDIC for providing financial institution data
- NCUA for providing credit union data
- Apache Airflow team for the amazing workflow management platform
- Django team for the robust web framework

## Learning Resources

### Interview Preparation Courses
Looking to level up your interview skills? Check out these comprehensive courses:

- [Grokking the Modern System Design Interview](https://www.educative.io/explore?aff=VMyL) - The ultimate guide developed by Meta & Google engineers. Master distributed system fundamentals and practice with real-world interview questions. (26 hours, Intermediate)

- [Grokking the Coding Interview Patterns](https://www.educative.io/explore?aff=VMyL) - Master 24 essential coding patterns to solve thousands of LeetCode-style questions. Created by FAANG engineers. (85 hours, Intermediate)

- [Grokking the Low Level Design Interview Using OOD Principles](https://www.educative.io/explore?aff=VMyL) - A battle-tested guide to Object Oriented Design Interviews, developed by FAANG engineers. Master OOD fundamentals with practical examples.

### Essential Reading
- [Designing Data-Intensive Applications](https://amzn.to/4hiHZZf) by Martin Kleppmann - The definitive guide to building reliable, scalable, and maintainable systems. A must-read for understanding the principles behind modern data systems.

### Hosting Solutions
For deploying your own instance of this project, consider these reliable hosting options:

- [DigitalOcean](https://www.tkqlhce.com/click-101329284-15836238) - Simple and robust cloud infrastructure
- [DigitalOcean Managed Databases](https://www.anrdoezrs.net/click-101329284-15836245) - Fully managed PostgreSQL databases
