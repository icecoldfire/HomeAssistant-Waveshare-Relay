# Use an official Python image as the base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Add coverage dependencies
RUN pip install pytest-cov

# Copy the entire project into the container
COPY . .

# Set the default command to run pytest
CMD ["pytest", "--disable-warnings"]