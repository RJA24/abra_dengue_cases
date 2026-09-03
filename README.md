# Abra PESU Surveillance Information System

A modular epidemiological surveillance information system for monitoring provincial health data, including Dengue, Tuberculosis, and related surveillance activities.

The system is designed for constrained-resource deployment using a $0 infrastructure stack consisting primarily of Streamlit Community Cloud, Google Sheets, GitHub, and GitHub Actions.

## Architecture

The application follows a modular monolith architecture. The Streamlit entry point handles authentication and routing, while program-specific modules and shared utilities handle presentation, data processing, validation, GIS, and auditing.

```text
                    Streamlit
                        |
                  Authentication
                        |
                     Gateway
                        |
          +-------------+-------------+
          |             |             |
       Dengue           TB           Admin
          |             |             |
          +-------------+-------------+
                        |
                Shared Utilities
          +-------------+-------------+
          |             |             |
        Data           GIS          QA/Audit
          |             |             |
          +-------------+-------------+
                        |
                  Google Sheets
```

## Key Engineering Features

### Data Governance

- Pre-upload data validation
- Data Quality Score
- Municipality and geographic validation
- Missing critical-field detection
- Duplicate Patient ID / Case Number detection
- Upload authorization workflow

### Data Reliability

- Automatic pre-overwrite backups
- Emergency restoration of the previous dataset
- Administrative audit trail
- Explicit confirmation before destructive operations

### Security

- Role-based access control
- Administrator approval workflow
- bcrypt password hashing
- Secrets managed through Streamlit Secrets
- Separation of credentials from application source code

### Performance

The application is optimized for Streamlit Community Cloud's constrained runtime environment through:

- Controlled Streamlit caching
- Cache entry limits
- Pandas memory optimization
- Categorical dtypes for suitable low-cardinality columns
- Lazy loading of program-specific datasets
- Lightweight gateway routing

### GIS & Analytics

- Municipality-level geographic visualization
- Barangay-level analysis where applicable
- Epidemiological trend analysis
- Geographic filtering
- Interactive maps
- Data export capabilities

## Testing & CI

The project uses `pytest` for automated testing.

GitHub Actions runs the test suite when changes are pushed to the repository, helping detect regressions in critical data-processing and validation logic before deployment.

## Project Structure

```text
.
├── app.py
├── dengue/
│   └── dashboard.py
├── tb/
│   └── dashboard.py
├── utils/
│   ├── constants.py
│   ├── cleaning.py
│   ├── data.py
│   ├── geo.py
│   ├── validation.py
│   └── audit.py
├── tests/
│   └── test_cleaning.py
├── .github/
│   └── workflows/
│       └── tests.yml
├── requirements.txt
└── README.md
```

## Local Development

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Streamlit Secrets

Create:

```text
.streamlit/secrets.toml
```

and provide the required credentials and connection configuration.

**Do not commit this file to the repository.**

### 4. Run the application

```bash
streamlit run app.py
```

## Deployment

The application is deployed using Streamlit Community Cloud.

The repository is connected to GitHub, while GitHub Actions performs automated testing as part of the development workflow.

## Design Constraints

This project was deliberately designed around a $0 infrastructure constraint.

Rather than relying on paid cloud databases or infrastructure, the system uses:

- Streamlit Community Cloud for application hosting
- Google Sheets for the current data backend
- GitHub for source control
- GitHub Actions for CI

These choices prioritize accessibility and operational feasibility while introducing known limitations in scalability and concurrency.

## Limitations

The current architecture is intended for a relatively small number of authorized users and operational datasets.

Google Sheets and Streamlit Community Cloud impose limitations on database transactions, concurrent users, storage, and runtime resources.

If system usage or data volume grows substantially, the architecture could be migrated toward a dedicated database and API layer.

## Screenshots



## Author

**Ron Jay Cardenas Ayup**

Data Controller III  
Provincial Department of Health Office – Abra

Interested in data systems, GIS, automation, and application development.
