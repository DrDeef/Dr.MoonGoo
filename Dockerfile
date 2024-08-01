# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy only the specified files into the container at /usr/src/app
COPY bot.py commands.py config.py scheduler.py requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 5005

# Define environment variable
ENV FLASK_APP=bot.py

# Run the application
CMD ["python", "bot.py"]
