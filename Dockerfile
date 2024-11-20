# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy only the specified files into the container at /usr/src/app
COPY administration.py bot.py bot_statistics.py config.py commands.py structurecommands.py  scheduler.py  moongoo.py moongoo_commands.py market_calculation.py mongodatabase.py tasks.py requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 5005

# Install Uvicorn if not already in requirements.txt
RUN pip install uvicorn fastapi

# Define the environment variable for FastAPI app
ENV APP_MODULE=bot:app

# Run the application with Uvicorn
CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "5005", "--reload"]