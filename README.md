# Siblore POS System

A Django-based Point of Sale (POS) system for managing sales, products, payments, suppliers, and users.

## Features

- **User Management**: Authentication and authorization system
- **Product Management**: Add, edit, and manage inventory
- **Sales Processing**: Handle transactions and sales records
- **Payment Management**: Track and process payments
- **Supplier Management**: Manage supplier information and relationships
- **SQLite Database**: Lightweight database solution

## Requirements

- Python 3.8+
- Django 6.0.1

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd siblore_pos
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv env
   # On Windows
   env\Scripts\activate
   # On Unix/MacOS
   source env/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install django==6.0.1
   ```

4. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

6. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Project Structure

```
siblore_pos/
├── core/           # Core Django settings and configuration
├── users/          # User management app
├── products/       # Product management app
├── sales/          # Sales processing app
├── payments/       # Payment management app
├── suppliers/      # Supplier management app
├── templates/      # HTML templates
├── static/         # Static files (CSS, JavaScript, images)
├── media/          # Media files (product images)
├── db.sqlite3      # SQLite database
└── manage.py       # Django management script
```

## Usage

1. Access the admin panel at `http://127.0.0.1:8000/admin/`
2. Log in with your superuser credentials
3. Add products, suppliers, and manage users through the admin interface
4. Process sales and payments through the main application

## Configuration

- Database: SQLite (located at `db.sqlite3`)
- Debug mode: Enabled (for development)
- Static files: Served from `/static/`
- Media files: Served from `/media/`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
