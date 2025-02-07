# Financial Data Assistant

**Author**: Xiaoting Kuang

**Development Tools**:
- Code Development: [Cursor](https://cursor.sh/) - The AI-first code editor
- AI Assistance: Claude (Anthropic) - For rapid development and problem-solving

A comprehensive financial data platform that aggregates and analyzes data from FDIC (Federal Deposit Insurance Corporation) and NCUA (National Credit Union Administration). The platform includes an automated data pipeline using Apache Airflow and a web interface with SQL querying capabilities.

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

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FDIC for providing financial institution data
- NCUA for providing credit union data
- Apache Airflow team for the amazing workflow management platform
- Django team for the robust web framework

## Support

For support, please open an issue in the GitHub repository or contact the maintainers. 