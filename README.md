# Coursaty

## Project Overview
Coursaty is an online learning platform that allows users to browse, purchase, and watch video courses. It provides a comprehensive ecosystem for both students and administrators.

## Features
- **Course Browsing**: Explore a wide variety of available courses.
- **Purchasing**: Secure course purchases through Stripe integration.
- **Video Lessons**: Access and watch video content for enrolled courses.
- **Comments**: Engage with instructors and other students via lesson comments.
- **Wishlist**: Save interested courses for later.
- **Blog**: Read articles and updates related to the platform.
- **Dashboard**: A personalized student dashboard to track enrolled courses and progress.
- **Admin Panel**: Comprehensive administrative interface for managing courses, users, and content.
- **Bilingual Support**: Full support for both Arabic and English languages.

## Tech Stack
- **Backend Framework**: Django
- **Database**: PostgreSQL (hosted on Neon)
- **Payments**: Stripe
- **Media Storage**: Cloudinary
- **Styling**: Tailwind CSS
- **Deployment**: Render

## Local Development Setup

To get this project running locally on your machine, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Coursaty
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the project root and add the required variables (see the Environment Variables section below).

5. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Load initial data (optional but recommended):**
   ```bash
   python manage.py loaddata data.json
   ```

7. **Run the development server:**
   ```bash
   python manage.py runserver
   ```
   You can now access the platform at `http://127.0.0.1:8000/`.

## Environment Variables

To run this project, you will need to add the following environment variables to your `.env` file:

- `SECRET_KEY`: Django secret key.
- `DEBUG`: Set to `True` for development, `False` for production.
- `DATABASE_URL`: Connection string for your PostgreSQL database (Neon).
- `STRIPE_PUBLIC_KEY`: Your Stripe publishable key.
- `STRIPE_SECRET_KEY`: Your Stripe secret key.
- `STRIPE_WEBHOOK_SECRET`: Your Stripe webhook signing secret.
- `CLOUDINARY_URL`: Your Cloudinary connection URL for media storage.

## Deployment

The application is configured to be deployed on **Render**. It uses **Neon** for the highly available PostgreSQL database and **Cloudinary** for scalable media and file storage.

## Live Demo

Check out the live application here: [https://coursaty-9qzy.onrender.com](https://coursaty-9qzy.onrender.com)
# Coursaty

Coursaty is an open-source E-Learning and Online Course platform built with Django. It provides a complete solution for course management, user registration, payments, and an integrated blog.

## Features

- **Courses Management**: Organized by categories, with rich content and lessons.
- **User Accounts**: Registration, authentication, profile management, and enrolled courses dashboard.
- **Payments**: Integrated payment gateway for purchasing premium courses.
- **Blog**: Built-in blogging system to share articles, updates, and news.
- **Wishlist**: Users can add courses to their wishlist for later.
- **Multilingual Support**: Ready for localization.

## Project Structure

This Django project consists of several cohesive applications:

- `accounts/`: Handles user authentication, registration, and profiles.
- `blog/`: Contains the blog posts functionality.
- `courses/`: The core e-learning application containing models for Categories, Courses, Lessons, and Wishlist.
- `payments/`: Manages transactions and payment integration for course enrollments.
- `config/`: Main Django configuration and settings.
- `templates/`: HTML templates for the frontend, utilizing a customized layout.

## Prerequisites

- Python 3.8+
- pip (Python package installer)
- virtualenv (optional but recommended)

## Installation & Local Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Coursaty
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

6. **Access the application:**
   Open your browser and navigate to `http://127.0.0.1:8000/`.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License.
