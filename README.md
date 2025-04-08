# OpenDesk - Helpdesk Ticketing System

A comprehensive web-based Helpdesk ticketing system designed for small IT service providers. This application provides a complete solution for managing support tickets, assets, time tracking, expenses, and a knowledge base.

## Table of Contents

-   [Features](#features)
-   [System Requirements](#system-requirements)
-   [Installation](#installation)
-   [Configuration](#configuration)
-   [Usage](#usage)
    -   [Tickets Module](#tickets-module)
    -   [Assets Module](#assets-module)
    -   [Time & Expenses Module](#time--expenses-module)
    -   [Knowledge Base Module](#knowledge-base-module)
    -   [Settings Module](#settings-module)
-   [User Roles and Permissions](#user-roles-and-permissions)
-   [Customization](#customization)
-   [API Documentation](#api-documentation)
-   [Troubleshooting](#troubleshooting)
-   [Contributing](#contributing)
-   [License](#license)
-   [Recent Updates](#recent-updates)

## Features

The Helpdesk Ticketing System includes the following core features:

### Ticket Management

-   Create, view, update, and close support tickets
-   Assign tickets to technicians
-   Set priorities and due dates
-   Track SLA compliance
-   Email notifications for ticket updates
-   Ticket categorization and filtering
-   Internal and public comments with role-based permissions

### Asset Management

-   Track hardware and software assets
-   Manage asset assignments to users
-   Track warranty information
-   Link assets to related tickets
-   Asset history and timeline

### Time & Expenses Tracking

-   Log time spent on tickets
-   Record expenses related to tickets
-   Generate time and expense reports
-   Billable vs. non-billable tracking

### Knowledge Base

-   Create and organize articles by category
-   Search functionality
-   Article ratings and comments
-   Internal vs. client-facing articles
-   Related articles suggestions
-   Image attachment support

### Settings Module

-   Configure general application settings
-   Email configuration
-   SLA management
-   Notification preferences
-   Theme customization

## System Requirements

-   Python 3.8 or higher
-   SQLite (default) or MySQL/PostgreSQL for production
-   Modern web browser (Chrome, Firefox, Safari, Edge)
-   1GB RAM minimum (2GB+ recommended)
-   500MB disk space (excluding database growth)

## Installation

### Option 1: Standard Installation

1.  Clone the repository:
    ```bash
    git clone [https://github.com/ksioneoneseven/OpenDesk.git](https://github.com/ksioneoneseven/OpenDesk.git)
    cd OpenDesk
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Initialize the database:
    ```bash
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```
5.  Create an admin user:
    ```bash
    flask create-admin
    ```
6.  Start the development server:
    ```bash
    flask run --port=5001
    ```
7.  Access the application at `http://localhost:5001`

### Option 2: Docker Installation

1.  Make sure Docker and Docker Compose are installed on your system.
2.  Clone the repository:
    ```bash
    git clone [https://github.com/ksioneoneseven/OpenDesk.git](https://github.com/ksioneoneseven/OpenDesk.git)
    cd OpenDesk
    ```
3.  Build and start the containers:
    ```bash
    docker-compose up -d
    ```
4.  Access the application at `http://localhost:5000`

## Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```dotenv
FLASK_APP=helpdesk.py
FLASK_ENV=development  # Change to 'production' for production deployment
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db  # Default SQLite database

# Email configuration
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_DEFAULT_SENDER=helpdesk@example.com

# Optional: For production with PostgreSQL
# DATABASE_URL=postgresql://username:password@localhost/helpdesk
```

### Database Configuration

By default, the application uses SQLite, which is suitable for development and small deployments. For production environments, it's recommended to use PostgreSQL or MySQL:

1.  Install the appropriate database connector:
    ```bash
    # For PostgreSQL
    pip install psycopg2-binary
    # For MySQL
    pip install mysqlclient
    ```
2.  Update the `DATABASE_URL` in your `.env` file to point to your database.
3.  Run migrations to create the database schema:
    ```bash
    flask db upgrade
    ```

### Settings Module Configuration

The Settings module allows administrators to configure various aspects of the application through the web interface:

-   **General Settings:** Application name, company details, default ticket settings
-   **Email Configuration:** SMTP server settings for sending notifications
-   **SLA Settings:** Define response and resolution time targets by priority
-   **Notification Settings:** Configure which events trigger notifications
-   **Theme Settings:** Customize the application's appearance

To access the Settings module, navigate to **Settings** in the main navigation (admin access required).

## Usage

### Tickets Module

The tickets module is the core of the helpdesk system, allowing you to manage support requests from creation to resolution.

#### Creating a Ticket

1.  Navigate to the **Tickets** section from the main menu.
2.  Click **"New Ticket"**.
3.  Fill in the required information:
    -   **Subject:** A brief description of the issue
    -   **Description:** Detailed information about the problem
    -   **Requester:** The person reporting the issue
    -   **Priority:** Urgency level (Low, Medium, High, Urgent)
    -   **Type:** Category of the issue (Incident, Service Request, etc.)
    -   **Assign to:** The technician responsible for the ticket
4.  Click **"Create Ticket"**.

#### Managing Tickets

-   **Viewing Tickets:** The main tickets page displays all tickets with filtering options.
-   **Updating Status:** Change the status as you work on the ticket (New, In Progress, Resolved, Closed).
-   **Adding Comments:** Document the troubleshooting steps and communication with the requester.
    -   *Internal Comments:* Visible only to staff (requires Administrator or Technician role).
    -   *Public Comments:* Visible to all users including the requester.
-   **Time Tracking:** Log time spent working on the ticket.
-   **Linking Assets:** Associate relevant hardware or software with the ticket.

### Knowledge Base Module

The knowledge base module helps you create and organize a repository of articles and solutions.

#### Creating Categories

1.  Navigate to the **Knowledge Base** section.
2.  Click **"Create Category"**.
3.  Fill in the category details:
    -   **Name:** Category title
    -   **Description:** Brief explanation of the category
    -   **Parent Category:** Optional parent for nested categories
    -   **Private:** Whether the category is internal-only
4.  Click **"Create Category"**.

#### Creating Articles

1.  Navigate to the desired category.
2.  Click **"Create Article"**.
3.  Fill in the article details:
    -   **Title:** Article headline
    -   **Content:** Main article body (supports Markdown or plain text)
    -   **Category:** Which category the article belongs to
    -   **Published:** Whether the article is visible
4.  Click **"Create Article"**.

## Troubleshooting

### Common Issues and Solutions

#### Application Won't Start

-   **Issue:** The Flask server fails to start.
-   **Solution:**
    -   Check that all dependencies are installed: `pip install -r requirements.txt`
    -   Verify the database connection settings in your `.env` file.
    -   Ensure the port is not already in use by another application.

#### Database Errors

-   **Issue:** Database migration errors.
-   **Solution:**
    -   Remove the `migrations` folder and recreate it:
        ```bash
        rm -rf migrations
        flask db init
        flask db migrate -m "Fresh migration"
        flask db upgrade
        ```

#### Comment Submission Errors

-   **Issue:** "Error adding comment" when trying to submit a ticket comment.
-   **Solution:**
    -   Ensure you have the correct permissions for the comment type (internal vs. public).
    -   Check that the form is properly filled out with all required fields.

#### Knowledge Base Category Creation Errors

-   **Issue:** Error when creating a new knowledge base category.
-   **Solution:**
    -   Verify that all required fields are completed.
    -   Ensure parent categories exist if you're creating a subcategory.

#### Settings Not Visible

-   **Issue:** Settings module not visible in the application.
-   **Solution:**
    -   Verify you are logged in with an Administrator account.
    -   Check that the settings routes are properly registered in the application.
    -   Clear browser cache and reload the application.

## Recent Updates

### April 2025 Update

-   **Fixed:** `ResourceClosedError` in ticket comments by removing premature database commit in event listener.
-   **Fixed:** Knowledge Base category creation error related to invalid fields.
-   **Added:** Enhanced logging for troubleshooting comment submission issues.
-   **Improved:** Form validation and error reporting for better user feedback.
-   **Updated:** Documentation and troubleshooting guides.

For a complete list of changes, please refer to the commit history on GitHub.
