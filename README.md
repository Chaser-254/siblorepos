# Siblore POS System

A comprehensive Django-based Point of Sale (POS) system with integrated e-commerce website functionality for managing sales, products, payments, suppliers, customers, and multi-level user management.

## Key Features

### Point of Sale (POS) System
- **Multi-role User Management**: Site Admin, Shop Admin, and Cashier roles with granular permissions
- **Product Management**: Complete inventory control with categories, stock tracking, and barcode support
- **Sales Processing**: Real-time POS terminal with multiple payment methods (Cash, Card, Mobile Money, Bank Transfer, Credit)
- **Customer Management**: Customer database with credit limits and debt tracking
- **Stock Management**: Real-time stock tracking with reorder levels and movement history
- **Financial Reporting**: Comprehensive sales reports, revenue tracking, and profit analysis
- **Debt Management**: Customer credit system with payment tracking and overdue alerts

### E-commerce Website Integration
- **Public Shop Frontend**: Each shop gets its own public website with customizable themes
- **Online Product Catalog**: Display products with images, descriptions, and pricing
- **Shopping Cart System**: Full e-commerce cart functionality with AJAX operations
- **Order Management**: Complete order processing system with status tracking
- **Checkout System**: Secure checkout with customer information collection
- **Shop Customization**: Business details, logos, and theme selection

### User Management & Authentication
- **Role-Based Access Control**:
  - **Site Admin**: Full system access, user management, registration approval
  - **Shop Admin**: Shop management, product/supplier control, cashier management
  - **Cashier**: POS access, sales processing, limited dashboard access
- **Registration System**: Request-based registration with admin approval workflow
- **Custom Authentication**: Enhanced authentication backend with profile-based access control
- **Business Profiles**: Extended user profiles with business information

### Inventory & Product Management
- **Product Categories**: Hierarchical category system
- **Stock Tracking**: Real-time inventory with automatic stock updates on sales
- **Stock Movements**: Complete audit trail of all stock transactions
- **Reorder Management**: Automatic low-stock alerts with configurable reorder levels
- **Product Images**: Image upload and management for products
- **Pricing Control**: Cost price, selling price, and profit margin calculations
- **Barcode Support**: SKU and barcode tracking for products

### Sales & Financial Management
- **Multiple Payment Methods**: Cash, Card, Mobile Money, Bank Transfer, Credit
- **Invoice Generation**: Automatic invoice numbering and receipt printing
- **Tax & Discount Support**: Tax calculation and discount application
- **Debt Tracking**: Customer credit management with payment schedules
- **Revenue Analytics**: Daily, weekly, and monthly revenue reports
- **Profit Analysis**: Real-time profit calculation on sales
- **Sales History**: Complete sales audit trail with detailed reporting

### E-commerce Features
- **Multi-Shop Support**: Each shop admin gets their own customizable website
- **Product Showcase**: Featured products, categories, and search functionality
- **Shopping Cart**: Session-based cart with add/update/remove operations
- **Order Processing**: Complete order lifecycle from placement to completion
- **Customer Orders**: Order tracking and status updates
- **Website Themes**: Multiple theme options for shop customization
- **Business Branding**: Logo upload and business information display

## Technical Architecture

### Django Apps Structure
- **`core`**: Main Django project configuration and settings
- **`users`**: User authentication, profiles, and role-based access control
- **`products`**: Product management, categories, and inventory tracking
- **`sales`**: POS terminal, sales processing, and financial reporting
- **`payments`**: Payment processing and transaction management
- **`suppliers`**: Supplier relationship management
- **`shop_website`**: E-commerce website functionality and online ordering

### Database Models Overview

#### User Management Models
- **`UserProfile`**: Extended user profiles with roles and business information
- **`RegistrationRequest`**: User registration requests with approval workflow

#### Product Management Models
- **`Category`**: Product categorization system
- **`Product`**: Core product information with pricing and images
- **`Stock`**: Real-time inventory tracking with reorder levels
- **`StockMovement`**: Complete audit trail of stock transactions

#### Sales & Financial Models
- **`Customer`**: Customer database with credit management
- **`Sale`**: Sales transactions with comprehensive payment tracking
- **`SaleItem`**: Individual line items in sales transactions
- **`Debt`**: Customer debt tracking with payment schedules
- **`DebtPayment`**: Debt payment records and history
- **`Revenue`**: Daily revenue aggregation and reporting

#### E-commerce Models
- **`ShopProfile`**: Shop website configuration and branding
- **`ShopProduct`**: Products displayed on e-commerce websites
- **`Cart`/`CartItem`**: Shopping cart system
- **`Order`/`OrderItem`**: Online order management system

## Installation & Setup

### Prerequisites
- Python 3.8+
- Django 6.0.1
- SQLite3 (included with Python)

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd siblore_pos
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv env
   # On Windows
   env\Scripts\activate
   # On Unix/MacOS
   source env/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install django==6.0.1
   pip install Pillow  # For image handling
   ```

4. **Database Setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Collect Static Files**
   ```bash
   python manage.py collectstatic
   ```

7. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

## Application URLs & Access

### Main Application
- **Landing Page**: `http://127.0.0.1:8000/`
- **Admin Panel**: `http://127.0.0.1:8000/admin/`
- **Login**: `http://127.0.0.1:8000/login/`
- **Registration Request**: `http://127.0.0.1:8000/register/`

### User Dashboards
- **Site Admin Dashboard**: `http://127.0.0.1:8000/site-admin/`
- **Shop Admin Dashboard**: `http://127.0.0.1:8000/shop-admin/`
- **POS Terminal**: `http://127.0.0.1:8000/sales/pos/`

### Management Interfaces
- **Products**: `http://127.0.0.1:8000/products/`
- **Sales History**: `http://127.0.0.1:8000/sales/sales/`
- **Customers**: `http://127.0.0.1:8000/sales/customers/`
- **Debts**: `http://127.0.0.1:8000/sales/debts/`
- **Reports**: `http://127.0.0.1:8000/sales/reports/`

### E-commerce Websites
- **Shop Home**: `http://127.0.0.1:8000/shop/<username>/`
- **Shop Products**: `http://127.0.0.1:8000/shop/<username>/products/`
- **Shopping Cart**: `http://127.0.0.1:8000/shop/<username>/cart/`
- **Checkout**: `http://127.0.0.1:8000/shop/<username>/checkout/`

### Shop Admin Website Management
- **Website Setup**: `http://127.0.0.1:8000/shop/admin/setup/`
- **Manage Products**: `http://127.0.0.1:8000/shop/admin/products/`
- **Manage Orders**: `http://127.0.0.1:8000/shop/admin/orders/`

## Configuration

### Database Configuration
- **Default**: SQLite database (`db.sqlite3`)
- **Location**: Project root directory
- **Backup**: Regular backups recommended for production

### Media Files
- **Product Images**: `/media/products/`
- **Shop Logos**: `/media/shop_logos/`
- **Website Products**: `/media/shop_products/`

### Static Files
- **CSS/JS**: `/static/` directory
- **Templates**: `/templates/` directory

## User Roles & Permissions

### Site Administrator
- Full system access
- User management and approval
- View all shops and reports
- System configuration
- Registration request management

### Shop Administrator
- Shop management and configuration
- Product and supplier management
- Cashier management
- Sales reports and analytics
- Debt and revenue tracking
- E-commerce website management
- Order processing

### Cashier
- POS terminal access
- Sales processing
- Customer management
- Limited dashboard access
- View own sales only

## Reporting & Analytics

### Sales Reports
- Daily/Weekly/Monthly sales summaries
- Payment method breakdown
- Top-selling products
- Customer purchase history
- Profit analysis

### Inventory Reports
- Stock levels and movements
- Low stock alerts
- Reorder recommendations
- Stock value analysis

### Financial Reports
- Revenue tracking
- Debt aging reports
- Payment method analysis
- Profit margins

## Security Features

- Role-based access control
- Custom authentication backend
- Profile-based user activation
- CSRF protection
- SQL injection prevention
- XSS protection
- Session security

## Frontend Features

### Responsive Design
- Mobile-friendly interface
- Bootstrap-based UI components
- Modern, clean design
- Intuitive navigation

### Interactive Elements
- AJAX-powered cart operations
- Real-time stock updates
- Dynamic product search
- Interactive dashboard widgets

## E-commerce Features

### Shop Customization
- Multiple theme options
- Business branding
- Logo upload
- Custom business information

### Customer Experience
- Product browsing and search
- Shopping cart functionality
- Secure checkout process
- Order tracking

## Advanced Features

### Multi-Shop Support
- Each shop admin gets independent website
- Separate product catalogs
- Independent order management
- Custom branding per shop

### Integration Capabilities
- Barcode scanning support
- Multiple payment gateways
- Email notifications
- Print receipts and invoices

## Deployment Considerations

### Production Setup
- Use PostgreSQL/MySQL for production
- Configure proper static file serving
- Set up SSL certificates
- Configure email backend
- Implement backup strategies

### Performance Optimization
- Database indexing
- Caching implementation
- Image optimization
- CDN integration

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development Guidelines

- Follow PEP 8 Python style guidelines
- Write comprehensive tests
- Document new features
- Use meaningful commit messages
- Maintain backward compatibility

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Phone: +254111363870
- Email: esibitaremmanuel316@gmail.com
- Create an issue in the repository
- Check the documentation
- Review the admin panel for configuration options

## Version History

- **v1.0.0**: Initial release with core POS functionality
- **v1.1.0**: Added e-commerce website integration
- **v1.2.0**: Enhanced reporting and analytics
- **v1.3.0**: Multi-shop support and customization

---

**Siblore POS System** - Complete business management solution for modern retail operations.
