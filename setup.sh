#!/bin/bash

# Create and activate virtual environment
echo "Creating virtual environment..."
python -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "Setting up databases..."
createdb alpharank
createdb airflow

# Initialize Django
echo "Setting up Django..."
python manage.py migrate
python manage.py collectstatic --noinput

# Initialize Airflow
echo "Setting up Airflow..."
export AIRFLOW_HOME="$(pwd)/airflow"
airflow db init
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p airflow/dags
mkdir -p airflow/logs
mkdir -p airflow/plugins

# Set up pre-commit hooks
echo "Setting up git hooks..."
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
python manage.py check
python manage.py test
EOF
chmod +x .git/hooks/pre-commit

echo "Setup complete! Follow these steps to start the application:"
echo "1. Start Redis: redis-server"
echo "2. Start Airflow webserver: airflow webserver -p 8080"
echo "3. Start Airflow scheduler: airflow scheduler"
echo "4. Start Django development server: python manage.py runserver" 