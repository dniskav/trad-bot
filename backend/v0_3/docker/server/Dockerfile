FROM python:3.12-slim

WORKDIR /app

# Copy package files
COPY ../server-package/ ./server-package/
COPY ../shared/ ./shared/

# Install Server dependencies
RUN pip install --no-cache-dir -r server-package/requirements.txt

# Install TA-Lib dependencies
RUN apt-get update && apt-get install -y build-essential libfreetype6-dev

# Expose port
EXPOSE 8200

# Run Server package
CMD ["python", "-m", "server-package.main"]
