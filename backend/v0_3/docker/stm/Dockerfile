FROM python:3.12-slim

WORKDIR /app

# Copy package files
COPY ../stm-package/ ./stm-package/
COPY ../shared/ ./shared/

# Install STM dependencies  
RUN pip install --no-cache-dir -r stm-package/requirements.txt

# Expose port
EXPOSE 8100

# Run STM package
CMD ["python", "-m", "stm-package.main"]
