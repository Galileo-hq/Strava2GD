# 🚀 Unleash Your Strava Data! 🚀

Ever wanted to own your Strava data, analyze it your way, or build a personal dashboard? This project is your key to unlocking it!

**Strava2Drive** is a powerful, automated script that connects to your Strava account, downloads your workout history, and securely uploads it as clean, organized JSON files directly to your Google Drive. Set it up once and let the magic happen automatically!

## ✨ Core Features

-   **Automated Data Pipeline:** Runs on a schedule using GitHub Actions, so you can "set it and forget it."
-   **Rich Data Export:** Captures a comprehensive set of data points for each workout (see the full list below!).
-   **Secure by Design:** Manages all your sensitive API keys and tokens using encrypted GitHub Secrets. Your credentials are never exposed.
-   **Personal Data Warehouse:** Stores your entire workout history in your own Google Drive, giving you full ownership and control.
-   **Easy to Customize:** Built with clean Python, making it easy to extend or modify for your own data projects.

## 📊 Data Deep Dive: What You Get

Each workout is exported as a detailed JSON object, containing a wealth of information. Here's a look at the key data fields you'll have at your fingertips:

-   **Workout Vitals:** `id`, `name`, `type`, `start_date`
-   **Performance Metrics:** `distance_meters`, `moving_time_seconds`, `elapsed_time_seconds`, `total_elevation_gain_meters`
-   **Speed & Power:** `average_speed_mps`, `max_speed_mps`, `average_watts`
-   **Biometrics:** `average_heartrate`, `max_heartrate`, `average_cadence`
-   **Social Stats:** `kudos_count`, `comment_count`, `photo_count`
-   **GPS & Gear:** `start_latlng`, `end_latlng`, `gear_id`, `device_name`
-   **Detailed Splits:** A full array of metric splits, each with its own distance, time, and speed data.

## ⚙️ Setup & Configuration

Getting started is easy. Follow these steps to get your personal data pipeline running.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/your-repository.git
    cd your-repository
    ```

2.  **Create a Virtual Environment & Install Dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configure GitHub Secrets:**
    This is the most critical step for automation. Go to your repository's settings (`Settings` > `Secrets and variables` > `Actions`) and add the following secrets:

    -   `GOOGLE_CREDENTIALS_JSON`: The full JSON content of your Google Cloud `credentials.json` file.
    -   `GOOGLE_TOKEN_JSON`: The JSON content from your generated Google `token.json` file.
    -   `STRAVA_CLIENT_ID`: Your Strava application's Client ID.
    -   `STRAVA_CLIENT_SECRET`: Your Strava application's Client Secret.
    -   `STRAVA_TOKEN_JSON`: The JSON content from your generated Strava `strava_token.json` file.

## 🚀 Automation Options

You have two powerful options for automating your data export.

### 1. GitHub Actions (Recommended)

The easiest way to automate the export is by using the built-in GitHub Actions workflow. It runs on a schedule in the cloud, so you don't need to keep your own computer running.

**Setup:**
Follow the instructions in the "Configure GitHub Secrets" section above. Once your secrets are set, the workflow is ready to go!

**Usage:**
The workflow is configured to run on a schedule. You can also trigger it manually from the **Actions** tab in your GitHub repository anytime you want a fresh export.

### 2. Local Cron Job (Advanced)

If you prefer to run the exporter on your own machine, you can use a classic cron job. This gives you full control over the execution environment.

**Setup:**

1.  **Local Credentials:** Instead of GitHub Secrets, you'll need to have your credential files stored locally in the project directory:
    -   Create a `.env` file in the root directory with your `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET`.
    -   Ensure your `credentials.json`, `token.json`, and `strava_token.json` files are in the `config/` directory.

2.  **Create a Runner Script:** Create a simple shell script named `run_exporter.sh` in the project's root directory. This script ensures the exporter runs with the correct virtual environment.

    ```bash
    #!/bin/bash
    # Make sure to use the absolute path to your project directory
    cd /path/to/your/Strava2Drive
    source venv/bin/activate
    python src/strava_exporter.py
    ```

    Make the script executable:
    ```bash
    chmod +x run_exporter.sh
    ```

3.  **Edit Your Crontab:** Open your user's crontab file for editing:
    ```bash
    crontab -e
    ```

4.  **Add the Cron Job:** Add a line to the crontab file to schedule the script. The following example runs the exporter every Sunday at 3:00 AM.

    ```crontab
    0 3 * * 0 /path/to/your/Strava2Drive/run_exporter.sh >> /path/to/your/Strava2Drive/cron.log 2>&1
    ```

    This command will run your script and log all output (both standard and error) to a `cron.log` file in your project directory, which is useful for debugging.

---

Now, go build something amazing with your data!
