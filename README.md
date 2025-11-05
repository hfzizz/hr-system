# HR Management System

A comprehensive Human Resources Management System built with Django 5.1.3, designed to streamline HR operations including employee management, performance appraisals, contract management, and employee promotions.

## 📋 Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Database](#database)
- [Contributing](#contributing)

## ✨ Features

### Employee Management
- **Employee Records**: Comprehensive employee database with personal information, contact details, and employment history
- **Department Management**: Organize employees by departments
- **Resume Parsing**: Automated resume processing using spaCy NLP for extracting candidate information
- **Profile Management**: User profiles with customizable settings
- **Role-based Access Control**: Secure authentication with email or username login

### Performance Appraisals
- **Appraisal Periods**: Define and manage appraisal cycles
- **Multi-level Review Process**: Primary and secondary appraiser workflow
- **Status Tracking**: Monitor appraisal progress through various stages (pending, under review, completed, etc.)
- **Academic Tracking**: Track qualifications, publications, research work, and conference participation
- **Teaching Evaluation**: Module management and student supervision records
- **Professional Development**: Track memberships, consultancy work, and administrative posts

### Contract Management
- **Contract Types**: Support for multiple contract types (3-year renewal, 1-year extension, local staff contracts)
- **Multi-stage Approval**: Workflow through employee → Dean → SMT approval process
- **Research Integration**: Link with Scopus API for publication verification
- **Document Management**: PDF generation and contract document handling
- **Status Notifications**: Real-time contract status updates
- **Historical Records**: Maintain contract history and audit trails

### Employee Promotion
- Promotion tracking and management module
- Integration with appraisal and contract systems

### Reusable Components
- **Dynamic Data Tables**: Sortable, filterable, and paginated tables with customizable columns
- **Template Tags**: Custom Django template tags for consistent UI components
- **Responsive Design**: Mobile-friendly interface with modern styling

## 🛠️ Technology Stack

### Backend
- **Python 3.x**
- **Django 5.1.3** - Web framework
- **PostgreSQL/SQLite** - Database (configurable)
- **Django REST Framework 3.15.2** - API development

### Frontend
- **HTML5/CSS3**
- **JavaScript**
- **Bootstrap/Tailwind CSS** - Responsive design
- **Django Templates** - Server-side rendering

### Key Libraries & Tools
- **spaCy 3.8.4** - Natural Language Processing for resume parsing
- **Pillow 11.0.0** - Image processing
- **django-filter 24.3** - Advanced filtering
- **django-widget-tweaks 1.5.0** - Form styling
- **django-livereload-server 0.5.1** - Development live reload
- **psycopg2 2.9.10** - PostgreSQL adapter
- **Faker 36.1.1** - Test data generation

### External Integrations
- **Scopus API** - Academic publication verification
- **OpenAI API** - AI-powered features (configurable)

## 📦 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)
- PostgreSQL (optional, SQLite is default)
- Git

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/hfzizz/hr-system.git  # Replace with your repository URL
cd hr-system
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download spaCy Language Model

```bash
python -m spacy download en_core_web_sm
```

### 5. Set Up Database

The project is configured to use SQLite by default. To use PostgreSQL instead:

1. Install PostgreSQL
2. Create a database
3. Update `hr_system/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_database_name',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
```

### 8. Collect Static Files

```bash
python manage.py collectstatic
```

### 9. Run Development Server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your web browser.

## ⚙️ Configuration

### Environment Variables

For production deployment, consider using environment variables for sensitive settings:

```python
# In settings.py
import os

# SECURITY WARNING: Never use the default value in production!
# Generate a new secret key: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'CHANGE-ME-IN-PRODUCTION-USE-ENV-VARIABLE')
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
SCOPUS_API_KEY = os.environ.get('SCOPUS_API_KEY', '')
```

### Important Settings

- **SECRET_KEY**: Change in production (currently in settings.py)
- **DEBUG**: Set to `False` in production
- **ALLOWED_HOSTS**: Configure for production domains
- **TIME_ZONE**: Currently set to 'Asia/Brunei'
- **MEDIA_ROOT**: Media files location for uploads
- **STATIC_ROOT**: Static files collection directory

### File Upload Configuration

```python
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
ALLOWED_UPLOAD_PDF_TYPES = ['application/pdf']
```

## 📖 Usage

### Admin Panel

Access the Django admin panel at `http://127.0.0.1:8000/admin/` using your superuser credentials.

From here you can:
- Manage employees, departments, and users
- Configure appraisal periods
- Review and approve contracts
- Manage system-wide settings

### User Roles

The system supports role-based access control:
- **Admin**: Full system access
- **HR Staff**: Employee and appraisal management
- **Department Heads**: Department-level oversight
- **Employees**: Self-service portal for personal information and appraisals

### Main Features Access

- **Dashboard**: `/` - Main dashboard with overview
- **Employee Management**: `/employees/` - Employee CRUD operations
- **Appraisals**: `/appraisals/` - Performance review system
- **Contracts**: `/contract/` - Contract management workflow
- **Promotions**: `/promotion/` - Employee promotion tracking
- **Profile**: `/profile/` - User profile management
- **Settings**: `/settings/` - User preferences

## 📁 Project Structure

```
hr-system/
├── appraisals/          # Performance appraisal module
│   ├── migrations/
│   ├── static/
│   ├── templates/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── components/          # Reusable UI components
│   ├── static/
│   ├── templatetags/
│   └── views.py
├── contract/            # Contract management module
│   ├── migrations/
│   ├── templates/
│   ├── models.py
│   ├── views.py
│   ├── services.py
│   ├── scopus.py
│   └── urls.py
├── employees/           # Employee management module
│   ├── migrations/
│   ├── static/
│   ├── templates/
│   ├── templatetags/
│   ├── utils/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── resume_parser.py
│   └── urls.py
├── employee_promotion/  # Promotion tracking module
│   ├── migrations/
│   ├── templates/
│   └── urls.py
├── hr_system/           # Main project configuration
│   ├── management/
│   ├── settings.py
│   ├── urls.py
│   ├── backends.py      # Custom authentication backend
│   └── wsgi.py
├── middleware/          # Custom middleware
│   └── auth_middleware.py
├── roles/               # Role management
│   ├── migrations/
│   ├── models.py
│   └── views.py
├── static/              # Static files (CSS, JS, images)
├── templates/           # Global templates
├── media/               # User-uploaded files
├── docs/                # Documentation
├── manage.py            # Django management script
└── requirements.txt     # Python dependencies
```

## 🗄️ Database

### Default Configuration (SQLite)

The system uses SQLite by default for easy setup:
- Database file: `db.sqlite3`
- Suitable for development and small deployments

### Production Database (PostgreSQL)

For production environments, PostgreSQL is recommended:
- Better performance with large datasets
- Advanced features for complex queries
- Better concurrency handling

### Key Models

- **Employee**: Core employee information and relationships
- **Department**: Organizational structure
- **Appraisal**: Performance review records
- **AppraisalPeriod**: Appraisal cycle management
- **Contract**: Contract applications and approvals
- **Publication**: Academic publications tracking
- **Qualification**: Educational credentials

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Run tests (if available)
5. Commit your changes: `git commit -m "Add your feature"`
6. Push to the branch: `git push origin feature/your-feature-name`
7. Create a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and modular

### Testing

```bash
python manage.py test
```

## 📝 License

This project is part of a Final Year Project (FYP).

## 🔒 Security Notes

**Important**: Before deploying to production:

1. **CRITICAL**: Generate and set a new `SECRET_KEY` using environment variables (NEVER commit it to version control)
   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```
2. Set `DEBUG = False`
3. Configure `ALLOWED_HOSTS` properly
4. Remove or secure API keys (OpenAI, Scopus) - use environment variables only
5. Use environment variables for ALL sensitive data (database credentials, API keys, etc.)
6. Enable HTTPS
7. Configure proper database backups
8. Review and update security middleware settings
9. Remove hardcoded credentials from settings.py

## 📧 Support

For issues, questions, or contributions, please use the GitHub issue tracker.

## 🙏 Acknowledgments

- Django Framework
- spaCy NLP Library
- Bootstrap/Tailwind CSS
- All contributors and maintainers

---

**Note**: This is a Final Year Project (FYP) HR Management System designed for educational and practical HR management purposes.
