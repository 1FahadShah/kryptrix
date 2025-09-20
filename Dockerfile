# 1. Use an official Python runtime as the base image
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the requirements file first to leverage Docker's caching
COPY requirements.txt .

# 4. Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application's code into the container
COPY . .

# 6. Make the startup script executable
RUN chmod +x ./run.sh

# 7. Expose the port that Streamlit runs on
EXPOSE 8501

# 8. Define the command to run when the container starts
CMD ["./run.sh"]