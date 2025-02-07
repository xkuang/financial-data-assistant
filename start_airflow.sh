#!/bin/bash

# Set environment variables
export AIRFLOW_HOME=$(pwd)

# Create required directories
mkdir -p $AIRFLOW_HOME/logs
mkdir -p $AIRFLOW_HOME/plugins

# Initialize the database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# Start the webserver in the background
airflow webserver -D

# Start the scheduler in the background
airflow scheduler -D

echo "Airflow is running!"
echo "Access the web interface at: http://localhost:8080"
echo "Username: admin"
echo "Password: admin" 