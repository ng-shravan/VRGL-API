# Use official Python runtime as the base image
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Define build-time arguments
ARG vrgl_db_host_url
ENV vrgl_db_host_url=$vrgl_db_host_url

ARG vrgl_app_db_name
ENV vrgl_app_db_name=$vrgl_app_db_name

ARG vrgl_db_usrname
ENV vrgl_db_usrname=$vrgl_db_usrname

ARG vrgl_db_pwd
ENV vrgl_db_pwd=$vrgl_db_pwd

ARG vrgl_security_db_name
ENV vrgl_security_db_name=$vrgl_security_db_name

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Expose the port that FastAPI will run on
EXPOSE 8000

# Command to run the application using uvicorn
CMD ["uvicorn", "main_app:app", "--host", "0.0.0.0", "--port", "8000"] 