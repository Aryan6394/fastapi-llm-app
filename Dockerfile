# Use a lightweight Python image to keep cold starts fast
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies without storing cache to keep the image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8080 (Cloud Run's default)
EXPOSE 8080

# Command to run the production ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]