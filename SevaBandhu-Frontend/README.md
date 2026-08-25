# Seva Bandhu Frontend

This directory contains a static frontend export of the existing Django-template UI.

## Run locally

Open `index.html` directly, or serve this directory with any static-file server.

## Structure

- `index.html` — home page
- `pages/` — customer and technician pages
- `assets/css/` — CSS extracted from the Django templates
- `assets/js/` — JavaScript extracted from the Django templates
- `page-manifest.json` — source-template-to-export map

## Important

This export preserves the visual UI only. Authentication, forms, payments, PDFs, live location, WebSockets, and dynamic dashboard data still require the Django backend. Django template variables and tags are rendered as safe placeholders here. Build an API layer before replacing the backend-rendered templates in production.