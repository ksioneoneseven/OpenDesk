# OpenDesk - Helpdesk Ticketing System

A comprehensive web-based Helpdesk ticketing system designed for small IT service providers. This application provides a complete solution for managing support tickets, assets, time tracking, expenses, and a knowledge base.

## Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Tickets Module](#tickets-module)
  - [Assets Module](#assets-module)
  - [Time & Expenses Module](#time--expenses-module)
  - [Knowledge Base Module](#knowledge-base-module)
- [User Roles and Permissions](#user-roles-and-permissions)
- [Customization](#customization)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

The Helpdesk Ticketing System includes the following core features:

### Ticket Management
- Create, view, update, and close support tickets
- Assign tickets to technicians
- Set priorities and due dates
- Track SLA compliance
- Email notifications for ticket updates
- Ticket categorization and filtering

### Asset Management
- Track hardware and software assets
- Manage asset assignments to users
- Track warranty information
- Link assets to related tickets
- Asset history and timeline

### Time & Expenses Tracking
- Log time spent on tickets
- Record expenses related to tickets
- Generate time and expense reports
- Billable vs. non-billable tracking

### Knowledge Base
- Create and organize articles by category
- Search functionality
- Article ratings and comments
- Internal vs. client-facing articles
- Related articles suggestions

## System Requirements

- Python 3.8 or higher
- SQLite (default) or MySQL/PostgreSQL for production
- Modern web browser (Chrome, Firefox, Safari, Edge)
- 1GB RAM minimum (2GB+ recommended)
- 500MB disk space (excluding database growth)

## Installation

### Option 1: Standard Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ksioneoneseven/OpenDesk.git
   cd OpenDesk
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. Create an admin user:
   ```bash
   flask create-admin
   ```

6. Start the development server:
   ```bash
   flask run
   ```

7. Access the application at http://localhost:5000

### Option 2: Docker Installation

1. Make sure Docker and Docker Compose are installed on your system.

2. Clone the repository:
   ```bash
   git clone https://github.com/ksioneoneseven/OpenDesk.git
   cd OpenDesk
   ```

3. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

4. Access the application at http://localhost:5000

## Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
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

1. Install the appropriate database connector:
   ```bash
   # For PostgreSQL
   pip install psycopg2-binary
   
   # For MySQL
   pip install mysqlclient
   ```

2. Update the `DATABASE_URL` in your `.env` file to point to your database.

3. Run migrations to create the database schema:
   ```bash
   flask db upgrade
   ```

## Usage

### Tickets Module

The tickets module is the core of the helpdesk system, allowing you to manage support requests from creation to resolution.

#### Creating a Ticket

1. Navigate to the Tickets section from the main menu
2. Click "New Ticket"
3. Fill in the required information:
   - Subject: A brief description of the issue
   - Description: Detailed information about the problem
   - Requester: The person reporting the issue
   - Priority: Urgency level (Low, Medium, High, Urgent)
   - Type: Category of the issue (Incident, Service Request, etc.)
   - Assign to: The technician responsible for the ticket
4. Click "Create Ticket"

#### Managing Tickets

- **Viewing Tickets**: The main tickets page displays all tickets with filtering options
- **Updating Status**: Change the status as you work on the ticket (New, In Progress, Resolved, Closed)
- **Adding Comments**: Document the troubleshooting steps and communication with the requester
- **Time Tracking**: Log time spent working on the ticket
- **Linking Assets**: Associate relevant hardware or software with the ticket

### Assets Module

The assets module helps you track and manage your organization's IT inventory.

#### Adding an Asset

1. Navigate to the Assets section
2. Click "Add Asset"
3. Enter the asset details:
   - Name: Descriptive name of the asset
   - Type: Computer, Server, Network Device, etc.
   - Serial Number: For hardware identification
   - Purchase Date: When the asset was acquired
   - Warranty Expiry: End date of the warranty period
   - Status: In Use, Available, Maintenance, Retired
   - Notes: Additional information about the asset
4. Click "Save Asset"

#### Asset Management

- **Viewing Assets**: Browse all assets with filtering options
- **Assigning Assets**: Assign assets to users
- **Asset Timeline**: View the history of the asset
- **Related Tickets**: See all support tickets associated with an asset

### Time & Expenses Module

This module allows you to track time spent on tickets and related expenses.

#### Logging Time

1. From a ticket view, click "Log Time"
2. Enter the following details:
   - Start Time: When you began working
   - End Time: When you finished working
   - Duration: Automatically calculated, or enter manually
   - Notes: Description of the work performed
   - Billable: Toggle if the time is billable to the client
3. Click "Save Time Entry"

#### Recording Expenses

1. From a ticket view, click "Add Expense"
2. Enter the expense details:
   - Amount: Cost of the expense
   - Description: What the expense was for
   - Date: When the expense occurred
   - Billable: Toggle if the expense is billable to the client
3. Click "Save Expense"

#### Generating Reports

1. Navigate to the Reports section
2. Select the report type (Time or Expenses)
3. Set the date range and other filters
4. Click "Generate Report"
5. Export the report to CSV or PDF if needed

### Knowledge Base Module

The knowledge base serves as a repository of solutions and documentation.

#### Creating Categories

1. Navigate to the Knowledge Base section
2. Click "Manage Categories"
3. Click "Add Category"
4. Enter the category details:
   - Name: Category title
   - Description: Brief explanation of the category
   - Parent Category: Optional, for creating subcategories
   - Private: Toggle if the category is for internal use only
5. Click "Save Category"

#### Creating Articles

1. Navigate to the Knowledge Base section
2. Click "New Article"
3. Enter the article details:
   - Title: Descriptive title of the article
   - Category: Select the appropriate category
   - Summary: Brief overview of the article
   - Content: Detailed information using the rich text editor
   - Tags: Keywords for improved searchability
   - Internal: Toggle if the article is for staff only
4. Click "Publish Article"

#### Using the Knowledge Base

- **Browsing**: Navigate through categories to find relevant articles
- **Searching**: Use the search bar to find articles by keyword
- **Rating Articles**: Provide feedback on article usefulness
- **Commenting**: Add additional information or ask questions about articles
- **Printing**: Generate printer-friendly versions of articles

## User Roles and Permissions

The system includes the following user roles:

### Administrator
- Full access to all system features
- Manage users and roles
- Configure system settings
- Access to all reports and analytics

### Technician
- Create and manage tickets
- Track time and expenses
- Manage assets
- Create and edit knowledge base articles

### Client
- Create and view their own tickets
- View assigned assets
- Access the client-facing knowledge base
- Cannot view internal articles or other clients' data

## Customization

### Email Templates

Email templates are located in the `app/templates/email` directory. You can customize these templates to match your organization's branding.

### System Settings

Administrators can configure various system settings through the admin interface:

1. Navigate to Admin > Settings
2. Adjust settings such as:
   - Company information
   - SLA definitions
   - Default ticket settings
   - Email notification preferences
   - UI customization options

### Custom Fields

You can add custom fields to tickets, assets, and other entities:

1. Navigate to Admin > Custom Fields
2. Click "Add Custom Field"
3. Configure the field:
   - Name: Field identifier
   - Label: Display name
   - Type: Text, Number, Date, Dropdown, etc.
   - Entity: Ticket, Asset, User, etc.
   - Required: Whether the field is mandatory
   - Visible to: Which user roles can see the field
4. Click "Save Field"

## API Documentation

The system provides a RESTful API for integration with other applications.

### Authentication

API requests require authentication using an API key:

```
Authorization: Bearer YOUR_API_KEY
```

To generate an API key, navigate to Admin > API Keys.

### Endpoints

- `GET /api/tickets`: List all tickets
- `POST /api/tickets`: Create a new ticket
- `GET /api/tickets/{id}`: Get a specific ticket
- `PUT /api/tickets/{id}`: Update a ticket
- `GET /api/assets`: List all assets
- `GET /api/kb/articles`: List knowledge base articles

For complete API documentation, see the `/api/docs` endpoint when running the application.

## Troubleshooting

### Common Issues

#### Application Won't Start

- Check if the virtual environment is activated
- Verify that all dependencies are installed
- Ensure the database connection is configured correctly
- Check the application logs for specific error messages

#### Email Notifications Not Working

- Verify SMTP settings in the `.env` file
- Check if the email server allows the connection
- Ensure the sender email address is valid
- Check the application logs for email-related errors

#### Database Migration Issues

If you encounter database migration errors:

1. Delete the migrations folder
2. Delete the database file (if using SQLite)
3. Run the following commands:
   ```bash
   flask db init
   flask db migrate -m "Fresh migration"
   flask db upgrade
   ```

### Logs

Application logs are stored in the `logs` directory. Check these logs for detailed error information when troubleshooting issues.

## Contributing

We welcome contributions to improve the Helpdesk Ticketing System!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Submit a pull request

Please ensure your code follows our coding standards and includes appropriate tests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

For additional support, please contact support@example.com or visit our website at https://example.com.
