# Coursaty

Coursaty is a bilingual (English/Arabic) e-learning platform built with Django.
Students browse video courses, purchase them through Stripe Checkout, watch
lessons, leave threaded comments, and manage a wishlist and a personal
dashboard. It also includes an integrated blog and a fully translated admin
panel.

**Live demo:** <https://coursaty-9qzy.onrender.com>

## Features

- **Course catalog** - categories, search, rating and price filters, pagination
- **Secure payments** - Stripe Checkout with webhook-driven enrollment and
  server-side verification of every payment
- **Video lessons** - Cloudinary-hosted video, section/lesson structure, and
  lesson-level access control (enrollment required)
- **Community** - threaded comments on lessons
- **Wishlist and student dashboard**
- **Blog** - registered users can publish posts; authors can edit and delete
  their own
- **Bilingual UI (EN/AR)** - full RTL layout support, translated models via
  django-modeltranslation
- **Admin panel** - manages courses, sections, lessons, payments, ratings,
  comments and wishlists with translated content fields

## Tech Stack

| Layer | Choice |
| --- | --- |
| Backend | Django 5.2 |
| Database | PostgreSQL (hosted on Neon) |
| Payments | Stripe Checkout + webhooks |
| Media storage | Cloudinary (chunked video uploads) |
| Styling | Tailwind CSS |
| Server | gunicorn + WhiteNoise, deployed on Render |

## Project Structure

```
accounts/    Custom user model, registration, login/logout
blog/        Blog posts (create/edit/delete, author permissions)
courses/     Categories, courses, sections, lessons, enrollments,
             ratings, comments, wishlist
payments/    Stripe checkout sessions, webhook handling, payments
config/      Project settings, URLs, WSGI/ASGI entry points
templates/   Shared templates (per-app subdirectories)
locale/      Arabic translations (django.po / django.mo)
scripts/     Build tooling (Tailwind CSS compile)
static/      CSS source (static/src) and build output (static/css)
```

## Local Setup

Requirements: Python 3.10+ and a PostgreSQL database (local or hosted).

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd Coursaty
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Build the frontend stylesheet:**

   ```bash
   python scripts/build_css.py
   ```

   This downloads the pinned Tailwind CSS CLI (see [Frontend Build](#frontend-build-tailwind-css))
   and compiles `static/css/tailwind.css`. The site is unstyled until this has
   run once.

5. **Create a `.env` file** in the project root with the variables listed in
   the next section.

6. **Apply database migrations:**

   ```bash
   python manage.py migrate
   ```

7. **Create an admin user (optional, for content management):**

   ```bash
   python manage.py createsuperuser
   ```

8. **Run the development server:**

   ```bash
   python manage.py runserver
   ```

   The site is now available at <http://127.0.0.1:8000/>.

## Frontend Build (Tailwind CSS)

Styling is compiled ahead of time - there is no runtime CDN script.

- `static/src/tailwind.css` is the source stylesheet (`@tailwind`
  directives, the base form-control styles and the custom design-system
  classes).
- `tailwind.config.js` holds the theme (design tokens, fonts) and the
  content globs (`templates/**/*.html` and `blog/forms.py`, whose widgets
  set Tailwind classes).
- `scripts/build_css.py` downloads the official Tailwind v3.4.17 standalone
  CLI for your platform into `.tailwind/` (git-ignored), verifies it
  against the SHA-256 checksums published on the release, and compiles the
  stylesheet to `static/css/tailwind.css` (git-ignored build output). It
  uses only the Python standard library - no Node.js is required.

During development, keep a watcher running so changes to templates or the
source CSS rebuild automatically:

```bash
python scripts/build_css.py --watch
```

One Tailwind v3 detail worth knowing: rules inside `@layer` are tree-shaken
when their selector classes do not appear in any content file. The
`page-minimal` class (which scopes the underlined form-control style to the
auth/payment pages) must therefore stay on the `<body>` of
`base_minimal.html`; a test guards this.

## Environment Variables

All variables below are read by `python-decouple` from a `.env` file (or real
environment variables, as on Render).

| Variable | Required | Notes |
| --- | --- | --- |
| `SECRET_KEY` | yes | Django secret key |
| `DEBUG` | yes | `True` for development, `False` in production |
| `ALLOWED_HOSTS` | no | Comma-separated; defaults to `127.0.0.1,localhost` |
| `DATABASE_URL` | one of | PostgreSQL URL (e.g. Neon). Alternative: set the five `DB_*` variables below |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | alternative | Used only when `DATABASE_URL` is not set |
| `STRIPE_SECRET_KEY` | yes | Stripe API secret key |
| `STRIPE_PUBLISHABLE_KEY` | yes | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | yes | Signing secret of your Stripe webhook endpoint |
| `CLOUDINARY_CLOUD_NAME` | yes | Cloudinary credentials for media storage |
| `CLOUDINARY_API_KEY` | yes | |
| `CLOUDINARY_API_SECRET` | yes | |

## Stripe Webhook Configuration

The payment flow relies on a Stripe webhook to enroll students after a
successful checkout:

- **Endpoint URL:** `https://<your-host>/payments/webhook/`
- **Events:** `checkout.session.completed` and `checkout.session.expired`

For local development, forward events with the Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/payments/webhook/
```

## Running the Tests

```bash
python manage.py test
```

The suite covers the payment flow (checkout, webhook signature verification,
enrollment idempotency, success-page verification), accounts (registration,
login redirect validation, POST-only logout), courses (lesson access control,
comments, wishlist) and the blog. Note that Django creates and destroys a
`test_*` database on the configured database server while running.

## Internationalization

The UI and admin are translated into Arabic (see `locale/ar`). To update the
translations after changing strings:

```bash
django-admin makemessages -l ar
# ... translate in locale/ar/LC_MESSAGES/django.po ...
django-admin compilemessages
```

Tip: name your virtual environment `.venv` (with a leading dot) so
`makemessages` does not extract strings from `site-packages`. The compiled
`django.mo` is committed because the build server has no gettext tooling.

## Deployment (Render)

The app is deployed on Render with gunicorn and WhiteNoise:

- **Build command:** `./build.sh` (installs dependencies, compiles the
  Tailwind stylesheet, collects static files, applies migrations). The
  build downloads the pinned Tailwind CLI binary (~40 MB) from the
  GitHub release and verifies its checksum before use.
- **Start command:** from the `Procfile` (`gunicorn config.wsgi:application`)
- Environment variables are configured in the Render dashboard; they are the
  same ones listed above.

## Notes and Known Limitations

- Lesson durations are set in the admin rather than extracted automatically
  (the previous automatic extraction required downloading and re-encoding
  every video on save).
- Blog *content* is single-language; only the UI, courses and admin content
  are translatable.
- There is no password-reset flow yet (no email backend is configured).
