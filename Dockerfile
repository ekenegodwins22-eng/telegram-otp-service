# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the application
# NOTE: The bot logic (bot.py) is designed to run in a separate process or thread.
# For a production deployment like Koyeb, it's best to separate the API and the Bot.
# The current Procfile only runs the API. The bot would need a separate worker service.
# For this prototype, we will assume the bot runs as a separate worker process.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
