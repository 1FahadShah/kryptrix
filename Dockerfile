# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Add a non-root user for security and set the working directory
RUN useradd -m appuser
USER appuser
WORKDIR /home/appuser/app

# 3. Pre-create the database directory so the app has permission to write to it
RUN mkdir -p database

# 4. Copy and install dependencies first to leverage Docker's caching
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application's source code
COPY --chown=appuser:appuser . .

# 6. Expose the port Hugging Face Spaces uses
EXPOSE 8501

# 7. Define the startup command
CMD ["python", "run.py"]