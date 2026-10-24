# Students Database CRUD API

### Backend Development Internship Project | EWB Edu Tech Pvt. Ltd.

A modular REST API for managing student records, built with **Python, FastAPI, SQLite, SQLAlchemy, and Pydantic**. The application implements complete CRUD operations, filtering, pagination, data validation, persistent storage, and structured error handling.

The project also includes an optional **local AI-powered student database assistant using Ollama**, allowing users to query student information using natural language without allowing the language model to execute database queries directly.

---

## Table of Contents

* [Project Overview](#project-overview)
* [Project Objectives](#project-objectives)
* [Key Features](#key-features)
* [Technology Stack](#technology-stack)
* [System Architecture](#system-architecture)
* [Project Structure](#project-structure)
* [Database Design](#database-design)
* [API Reference](#api-reference)
* [Validation and Error Handling](#validation-and-error-handling)
* [Installation and Setup](#installation-and-setup)
* [Running the Application](#running-the-application)
* [Testing](#testing)
* [Optional AI Assistant](#optional-ai-assistant)
* [Security Considerations](#security-considerations)
* [Demonstration Workflow](#demonstration-workflow)
* [Limitations](#limitations)
* [Potential Enhancements](#potential-enhancements)
* [License](#license)

---

## Project Overview

Managing student information requires reliable data storage, validation, and well-defined operations for creating, retrieving, updating, and deleting records.

This project addresses that requirement through a RESTful backend application that exposes student-management functionality through HTTP endpoints.

The application uses FastAPI to handle requests, Pydantic to validate input, SQLAlchemy to manage database interactions, and SQLite to persist student records.

The implementation separates API routing, business logic, database operations, and request validation to improve maintainability and testability.

An optional AI assistant extends the application by interpreting supported natural-language questions and retrieving relevant records through the existing database service layer.

**Primary objective:** Build a functional, testable, and maintainable backend application that demonstrates practical Python backend development skills.

## Project Objectives

1. Implement RESTful APIs for complete student record management.
2. Maintain persistent student records using SQLite.
3. Apply request validation and database constraints to protect data integrity.
4. Support filtering and pagination for efficient record retrieval.
5. Provide consistent HTTP status codes and meaningful error responses.
6. Validate functionality using automated tests and API integration checks.
7. Explore local LLM integration while restricting model access to approved database operations.

## Key Features

| Feature               | Description                                                                           |
| --------------------- | ------------------------------------------------------------------------------------- |
| Student CRUD          | Create, retrieve, update, partially update, and delete student records                |
| Persistent storage    | Store records in SQLite so they survive application restarts                          |
| Data validation       | Validate required fields, email addresses, dates, and contact information             |
| Duplicate prevention  | Enforce student ID and email uniqueness                                               |
| Filtering             | Search by name, course, student ID, and date-of-birth ranges                          |
| Pagination            | Retrieve bounded result sets using `skip` and `limit`                                 |
| Error handling        | Return appropriate HTTP status codes and structured JSON errors                       |
| API documentation     | Interactive Swagger UI, ReDoc, and OpenAPI specification                              |
| Automated testing     | Test CRUD behavior, validation, database persistence, and AI failure handling         |
| Optional AI assistant | Query supported student information using natural language and local Ollama inference |

---

## Technology Stack

| Technology     | Purpose                                  |
| -------------- | ---------------------------------------- |
| Python         | Core programming language                |
| FastAPI        | REST API framework                       |
| SQLite         | Persistent relational database           |
| SQLAlchemy     | ORM and database access                  |
| Pydantic       | Request validation and response schemas  |
| Uvicorn        | ASGI application server                  |
| pytest         | Automated testing                        |
| HTTPX          | HTTP client and test-client dependency   |
| Ollama         | Optional local language-model inference  |
| Git and GitHub | Version control and project distribution |

---

## System Architecture

The application follows a layered architecture that separates HTTP handling from business logic and database operations.

```text
                     Client / API Consumer
                              |
                              v
                    FastAPI Application
                              |
                    +---------+---------+
                    |                   |
                    v                   v
              Student Router       AI Router
                    |                   |
                    v                   v
             Student Service       AI Service
                    |                   |
                    v                   v
             SQLAlchemy ORM       Query Planner
                    |                   |
                    v                   v
              SQLite Database    Student Service
                                        |
                                        v
                                  SQLite Database
                                        |
                                        v
                                  Relevant Records
                                        |
                                        v
                                  Ollama (Optional)
                                        |
                                        v
                                  Natural-Language
                                      Response
```

### Architectural responsibilities

**API layer:** Handles HTTP requests, route parameters, response models, and status codes.

**Validation layer:** Uses Pydantic schemas to validate incoming data and prevent invalid requests from reaching the database logic.

**Service layer:** Contains student-management operations and database interaction logic.

**Database layer:** Defines SQLAlchemy models, database constraints, session management, and initialization.

**AI layer:** Converts supported questions into validated filters, retrieves relevant records through the existing service layer, and optionally uses Ollama to summarize those records.

The mandatory CRUD functionality does not depend on the AI components.

---

## Project Structure

```text
students-database-crud/
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── errors.py
│   │
│   ├── database/
│   │   ├── models.py
│   │   └── connection.py
│   │
│   ├── schemas/
│   │   ├── student.py
│   │   └── ai.py
│   │
│   ├── services/
│   │   ├── student_service.py
│   │   └── ai_service.py
│   │
│   ├── routers/
│   │   ├── students.py
│   │   └── ai_assistant.py
│   │
│   └── ai/
│       ├── query_planner.py
│       └── ollama_service.py
│
├── tests/
│   ├── conftest.py
│   ├── test_students.py
│   └── test_ai_assistant.py
│
├── scripts/
│   └── seed_database.py
│
├── data/
│   └── .gitkeep
│
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── LICENSE
```

The directory structure separates application responsibilities rather than placing database logic, validation, and HTTP handling in one large module.

The actual SQLite database is created locally and excluded from version control.

---

## Database Design

### Students table

| Field             | Description                               |
| ----------------- | ----------------------------------------- |
| `id`              | Internal integer primary key              |
| `student_id`      | Unique student identifier used by the API |
| `name`            | Student's name                            |
| `date_of_birth`   | Date of birth                             |
| `email`           | Optional, unique email address            |
| `phone`           | Optional contact number                   |
| `course`          | Course or programme name                  |
| `address`         | Optional address                          |
| `enrollment_date` | Optional enrollment date                  |
| `created_at`      | Creation timestamp in UTC                 |
| `updated_at`      | Last-update timestamp in UTC              |

### Data integrity rules

* Each student must have a unique student identifier.
* Email addresses must be unique when provided.
* At least one contact method—email or phone—is required.
* Dates must be valid, and the date of birth cannot be in the future.
* Enrollment dates cannot precede the date of birth.
* The application validates requests before performing database operations.
* Database constraints provide an additional layer of data integrity.

The database is stored locally in `data/students.db` by default. Its location can be configured through the `DATABASE_URL` environment variable.

---

## API Reference

The application exposes REST endpoints for student management.

### 1. Create a student

**Endpoint:** `POST /students`

Creates a new student record.

Example request:

```json
{
  "student_id": "STU1001",
  "name": "Aarav Sharma",
  "date_of_birth": "2005-06-15",
  "email": "aarav@example.com",
  "phone": "9876543210",
  "course": "Computer Science",
  "address": "Bengaluru",
  "enrollment_date": "2025-08-01"
}
```

Expected success status: `201 Created`

The example uses fictional student information.

### 2. Retrieve all students

**Endpoint:** `GET /students`

Retrieves student records with optional filtering and pagination.

Example:

```http
GET /students?course=Computer%20Science&skip=0&limit=10
```

Supported query parameters:

| Parameter    | Purpose                                               |
| ------------ | ----------------------------------------------------- |
| `name`       | Partial, case-insensitive name search                 |
| `course`     | Exact, case-insensitive course filter                 |
| `student_id` | Exact, case-insensitive identifier filter             |
| `dob_after`  | Students born after the specified date                |
| `dob_before` | Students born before the specified date               |
| `skip`       | Number of records to skip; default `0`                |
| `limit`      | Maximum records returned; default `50`, maximum `100` |

Multiple filters can be combined.

### 3. Retrieve a specific student

**Endpoint:** `GET /students/{student_id}`

Example:

```http
GET /students/STU1001
```

Returns the matching student or HTTP `404 Not Found` if the record does not exist.

The route uses the business identifier `student_id`, not the internal database primary key.

### 4. Update a student

**Endpoint:** `PUT /students/{student_id}`

Replaces the student's record using the supplied update data.

Omitted optional fields become `null`. The request is validated before the changes are saved.

### 5. Partially update a student

**Endpoint:** `PATCH /students/{student_id}`

Updates only the supplied fields.

Example request:

```json
{
  "course": "Data Science"
}
```

Unspecified fields remain unchanged. The merged record is validated before the update is committed.

### 6. Delete a student

**Endpoint:** `DELETE /students/{student_id}`

Deletes the specified record.

Expected success status: `204 No Content`

A successful deletion returns no response body. Attempts to delete nonexistent students return HTTP `404`.

### 7. Application health

| Endpoint      | Purpose                                |
| ------------- | -------------------------------------- |
| `GET /`       | Returns basic application information  |
| `GET /health` | Checks application and database health |

### 8. Optional AI assistant

**Endpoint:** `POST /ai/ask`

Accepts a natural-language question about the student database.

Example request:

```json
{
  "question": "How many students are enrolled in Computer Science?"
}
```

The assistant retrieves matching records through approved backend operations and returns a response grounded in the database.

AI functionality is disabled by default and does not affect the mandatory CRUD APIs.

### HTTP status codes

| Status code                | Meaning                                             |
| -------------------------- | --------------------------------------------------- |
| `200 OK`                   | Request completed successfully                      |
| `201 Created`              | Student record created                              |
| `204 No Content`           | Student successfully deleted                        |
| `400 Bad Request`          | Malformed JSON                                      |
| `404 Not Found`            | Requested student does not exist                    |
| `409 Conflict`             | Duplicate student ID or email                       |
| `422 Unprocessable Entity` | Request validation failed                           |
| `503 Service Unavailable`  | Service or optional AI functionality is unavailable |

The application returns structured JSON error responses for handled failures.

---

## Validation and Error Handling

Input validation is implemented with Pydantic schemas and supported by database constraints.

The application checks for:

* Missing required fields.
* Invalid email addresses.
* Invalid or impossible dates.
* Future dates of birth.
* Missing contact information.
* Invalid student identifiers.
* Duplicate student IDs and email addresses.
* Invalid pagination parameters.
* Invalid update requests.
* Requests for nonexistent student records.

For example, attempting to create another student with an existing identifier returns `409 Conflict` rather than silently overwriting the existing record.

The application also distinguishes malformed JSON from syntactically valid requests that fail business validation.

Database implementation details and internal stack traces are not exposed through normal API error responses.

---

## Installation and Setup

### Prerequisites

* Python 3.10 or later.
* pip.
* Git, if cloning the repository.
* A terminal or IDE, such as VS Code.

Ollama is required only for the optional local AI inference feature.

### 1. Clone the repository

Replace the placeholder with your actual GitHub repository URL.

```bash
git clone https://github.com/<your-username>/students-database-crud.git
cd students-database-crud
```

Alternatively, extract the project ZIP and open the extracted project root.

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
```

**macOS / Linux**

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

**Windows PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

If PowerShell blocks environment activation, you can run the project using `.venv\Scripts\python.exe` directly instead of changing your execution policy.

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Configure environment variables

Copy `.env.example` to `.env` if you want to customize the configuration.

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

The default configuration supports normal CRUD operation without requiring external credentials or an AI model.

---

## Running the Application

Start the FastAPI development server from the project root:

```bash
python -m uvicorn app.main:app --reload
```

The application will be available at:

| Resource              | URL                                |
| --------------------- | ---------------------------------- |
| API root              | http://127.0.0.1:8000/             |
| Health check          | http://127.0.0.1:8000/health       |
| Swagger UI            | http://127.0.0.1:8000/docs         |
| ReDoc                 | http://127.0.0.1:8000/redoc        |
| OpenAPI specification | http://127.0.0.1:8000/openapi.json |

The database tables are created automatically during application initialization.

For development and demonstration, Swagger UI provides an interactive interface for executing requests and inspecting responses.

### Load sample data

To insert fictional demonstration records:

```bash
python scripts/seed_database.py
```

The script can be run repeatedly without inserting duplicate seed records. It does not automatically delete existing data.

---

## Configuration

The following environment variables control the application's database and optional AI configuration.

| Variable                 | Default                       | Purpose                                      |
| ------------------------ | ----------------------------- | -------------------------------------------- |
| `DATABASE_URL`           | Project-local SQLite database | Database connection                          |
| `AI_ENABLED`             | `false`                       | Enables the AI endpoint                      |
| `OLLAMA_BASE_URL`        | `http://localhost:11434`      | Ollama server URL                            |
| `OLLAMA_MODEL`           | `llama3.2:1b`                 | Configured Ollama model                      |
| `OLLAMA_TIMEOUT_SECONDS` | `60`                          | Model request timeout                        |
| `AI_MAX_RECORDS`         | `25`                          | Maximum matching records passed to the model |

Refer to `.env.example` for the actual supported configuration.

---

## Testing

Testing is an important part of the project because successful application startup alone does not establish that the API behaves correctly.

The automated test suite uses pytest and FastAPI's test client. Tests use isolated temporary SQLite databases so that the developer's actual database is not modified.

### Run the test suite

```bash
python -m pytest -v
```

### Verified test results

The project's reported local verification results are:

| Verification                       | Result                                |
| ---------------------------------- | ------------------------------------- |
| Automated tests                    | 129 passed                            |
| Failed tests                       | 0                                     |
| Skipped tests                      | 0                                     |
| Live HTTP checks                   | 59 passed                             |
| Database persistence after restart | Verified                              |
| Duplicate record validation        | Verified                              |
| Filtering and pagination           | Verified                              |
| PUT and PATCH behavior             | Verified                              |
| Delete behavior                    | Verified                              |
| AI failure handling                | Tested with a stand-in Ollama service |

The local Windows test run completed with **129 passed, 0 failed, and 0 skipped**. One Starlette deprecation warning concerning the test client was reported.

The AI tests use a mocked or stand-in model service where appropriate. They do not establish that natural-language responses have been validated against a live Ollama model.

These results describe the reported verification runs; future changes should be tested again.

### Test coverage includes

* Student creation and retrieval.
* Full and partial updates.
* Student deletion.
* Validation and uniqueness constraints.
* Combined filters and pagination.
* Invalid request handling.
* Database persistence.
* AI-disabled behavior.
* Model timeout and connection failures.
* Malicious query handling.
* Prevention of model-generated database queries.

---

## Optional AI Assistant

The optional AI assistant extends the CRUD backend with natural-language access to supported student information.

It uses Ollama to run a language model locally rather than depending on a paid hosted LLM API.

### Setup

Install Ollama from its official website:

https://ollama.com/

Start Ollama and download the configured model:

```bash
ollama pull llama3.2:1b
```

Set the following variable in `.env`:

```env
AI_ENABLED=true
```

Restart the FastAPI application after changing the configuration.

The model name must match an installed Ollama model.

### Example questions

The assistant supports predefined question patterns such as:

* How many students are there?
* How many students are enrolled in Computer Science?
* Find students whose names contain Aarav.
* Find student STU1001.
* List students born after 2005.
* Find students born in 2005.

The assistant is rule-based in its interpretation of questions. It does not support arbitrary natural-language queries.

### How it works

1. The query planner maps supported questions to validated filters.
2. The student service retrieves matching records from SQLite.
3. Counts and empty-result responses are computed directly from database results.
4. For supported listing questions, the model can summarize retrieved records.
5. The response indicates whether the answer was deterministic, model-generated, or produced through a fallback.

### AI safety

* The model does not receive a direct database connection.
* Model-generated SQL is not executed.
* Database retrieval uses predefined filters and the existing ORM-based service layer.
* Only selected student fields are sent to the local model; contact information and addresses are excluded.
* Model responses undergo output validation.
* When the model is unavailable, supported operations use documented fallback behavior.

### Failure handling

When AI is disabled, the AI endpoint returns `503 Service Unavailable`.

When Ollama is unavailable or its configured model cannot be found, deterministic questions can still be answered, and supported listings can fall back to a database-derived response with a warning.

If a question is ambiguous or unsupported, the assistant requests clarification instead of generating an unrestricted database query.

**Verification limitation:** Automated tests and stand-in server checks cover the AI integration's behavior, but live inference using an actual Ollama model has not been verified in the reported development environment.

---

## Security Considerations

Security and data integrity are considered at the application and database layers.

* SQLAlchemy ORM operations are used for database access.
* Input validation is applied to API requests.
* Database constraints help enforce uniqueness and other integrity requirements.
* Errors are handled without exposing internal stack traces through normal API responses.
* The LLM cannot execute unrestricted SQL.
* Local Ollama inference avoids sending student information to an external LLM provider.
* Environment files, database files, caches, and virtual environments are excluded from version control by `.gitignore`.

Use fictional records for demonstrations and avoid committing real student information or credentials to the repository.

The application is a local development and internship project; it should not be represented as a production deployment with authentication, authorization, or production infrastructure unless those capabilities are implemented separately.

---

## Demonstration Workflow

For an internship review or technical demonstration, use the following sequence.

### Step 1: Start the application

```bash
python -m uvicorn app.main:app --reload
```

### Step 2: Open Swagger UI

Navigate to:

http://127.0.0.1:8000/docs

### Step 3: Demonstrate CRUD operations

1. Create a student using `POST /students`.
2. Retrieve the record using `GET /students/{student_id}`.
3. List and filter records using `GET /students`.
4. Modify a record using `PUT` and `PATCH`.
5. Delete the demonstration record using `DELETE`.
6. Show the expected error responses for invalid input and nonexistent records.

### Step 4: Explain the architecture

Describe how API routes, validation schemas, service logic, and the database layer work together.

### Step 5: Demonstrate testing

Run:

```bash
python -m pytest -v
```

Explain the distinction between unit tests, API integration checks, and database persistence tests.

### Step 6: Demonstrate the optional AI extension

If Ollama is installed and the configured model is available, enable AI and demonstrate supported questions.

Otherwise, explain the architecture and the AI testing limitation accurately. The core CRUD demonstration does not require Ollama.

---

## Limitations

The current implementation has the following documented limitations:

* The AI query planner supports predefined question patterns rather than unrestricted natural language.
* The quality of AI-generated summaries depends on the installed model.
* The AI assistant limits the number of matching records passed to the model.
* Live inference with the configured Ollama model remains unverified in the reported development environment.
* Authentication, role-based authorization, and production deployment infrastructure are outside the current implementation's documented scope.

These limitations provide a clear boundary for the current project rather than implying capabilities that have not been implemented.

---

## Potential Enhancements

The following are possible future improvements, not features claimed to exist in the current version:

* Authentication and role-based access control.
* Database migrations using Alembic.
* Docker-based deployment.
* Structured application logging and monitoring.
* Continuous integration with automated test execution.
* A frontend dashboard for student administration.
* More flexible natural-language query interpretation.
* Additional API integration and deployment tests.
* Deployment to a cloud platform with suitable configuration and security controls.

---

## License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Project Summary

The Students Database CRUD API demonstrates practical backend development using Python, FastAPI, SQLAlchemy, SQLite, and Pydantic.

Its main deliverables are a persistent student-management API, validated database operations, filtering and pagination, interactive API documentation, automated tests, and an optional locally hosted AI assistant.

The project emphasizes modular code organization, data integrity, predictable HTTP behavior, and reproducible testing.
